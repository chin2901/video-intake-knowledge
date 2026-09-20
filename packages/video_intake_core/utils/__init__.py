"""
Utility functions for video_intake_knowledge.

Safe, reusable helpers for URL validation, path sanitization, hashing,
file operations, config loading, and format parsing.
"""

from __future__ import annotations

import hashlib
import re
import urllib.parse
from ipaddress import IPv4Address, IPv4Network
from pathlib import Path
from typing import Any

import yaml


# ----------------------------------------------------------------------
# URL validation and sanitization
# ----------------------------------------------------------------------

# Hosts considered SSRF-dangerous: private ranges, localhost, metadata endpoints
_SSRF_BLOCKED_IPS = {
    IPv4Address("0.0.0.0"),
    IPv4Address("127.0.0.1"),
    IPv4Address("255.255.255.255"),
}
for net in (
    IPv4Network("10.0.0.0/8"),
    IPv4Network("172.16.0.0/12"),
    IPv4Network("192.168.0.0/16"),
    IPv4Network("169.254.0.0/16"),  # link-local
    IPv4Network("0.0.0.0/8"),
    IPv4Network("100.64.0.0/10"),  # CGNAT
):
    _SSRF_BLOCKED_IPS.update(net.hosts())  # type: ignore[arg-type]


def _is_blocked_ip(host: str) -> bool:
    """Check if a hostname resolves to a blocked IP or is a blocked literal IP."""
    host = host.lower().rstrip(".")
    try:
        addr = IPv4Address(host)
        return addr in _SSRF_BLOCKED_IPS
    except ValueError:
        pass
    return False


def validate_url(url: str) -> str:
    """Validate and normalize a URL.

    Only http and https schemes are allowed. Rejects SSRF-dangerous hosts
    (localhost, private IPs, metadata endpoints).

    Args:
        url: The URL to validate.

    Returns:
        The normalized URL string.

    Raises:
        ValueError: If the URL is invalid or dangerous.
    """
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()

    if scheme not in ("http", "https"):
        raise ValueError(
            f"URL scheme '{scheme}' not allowed. Only http and https are permitted."
        )
    if not parsed.hostname:
        raise ValueError(f"URL has no hostname: {url}")

    host = parsed.hostname
    if _is_blocked_ip(host):
        raise ValueError(f"URL host resolves to a blocked IP address: {host}")

    if parsed.hostname in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        raise ValueError(f"URL host is localhost/loopback: {host}")

    if parsed.hostname.endswith(".local"):
        raise ValueError(f"URL host is a local/mDNS name: {host}")

    # Normalize: remove default ports, lowercase scheme and host
    netloc = parsed.hostname.lower()
    if parsed.port and parsed.port not in (80, 443):
        netloc = f"{netloc}:{parsed.port}"

    normalized = urllib.parse.urlunparse(
        (scheme, netloc, parsed.path, parsed.params, parsed.query, "")
    )
    return normalized


def sanitize_for_prompt(text: str) -> str:
    """Sanitize text to be safe to inject into prompts.

    Escapes HTML entities and neutralizes common injection patterns.
    This is a light sanitization — content from videos is untrusted.

    Args:
        text: Raw text from video transcript/OCR.

    Returns:
        Sanitized text safe for prompt injection.
    """
    if not text:
        return ""

    # Escape HTML entities first
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    text = text.replace("'", "&#39;")

    # Neutralize common instruction-injection patterns
    injection_patterns = [
        (r"ignore\s+(previous|all|above|below)\s+instructions?", "[INSTRUCTION_BLOCKED]"),
        (r"disregard\s+(previous|all|above|below)\s+(rules|instructions)?", "[INSTRUCTION_BLOCKED]"),
        (r"you\s+are\s+now\s+(a|an)\s+\w+", "[ROLE_OVERRIDE_BLOCKED]"),
        (r"system\s*:\s*.*", "[SYSTEM_OVERRIDE_BLOCKED]"),
        (r"<\s*script.*?>.*?<\s*/\s*script\s*>", "[SCRIPT_BLOCKED]", re.IGNORECASE | re.DOTALL),
        (r"```.*?ignore.*```", "[CODE_INJECTION_BLOCKED]", re.IGNORECASE | re.DOTALL),
    ]

    for pattern_info in injection_patterns:
        if len(pattern_info) == 2:
            pattern, replacement = pattern_info
            flags = 0
        else:
            pattern, replacement, flags = pattern_info
        text = re.sub(pattern, replacement, text, flags=flags)

    return text.strip()


def redact_sensitive_data(text: str, patterns: list[str] | None = None) -> str:
    """Redact sensitive data patterns from text.

    By default redacts emails, phone numbers, credit card-like patterns.
    Custom patterns can be provided.

    Args:
        text: Text to redact.
        patterns: Custom regex patterns to redact (list of strings).

    Returns:
        Text with sensitive patterns replaced by [REDACTED].
    """
    default_patterns = [
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL_REDACTED]"),
        (
            r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}[-.\s]?\d{1,9}\b",
            "[PHONE_REDACTED]",
        ),
        (
            r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
            "[CARD_REDACTED]",
        ),
        (
            r"\b[A-Z]{2,}[0-9]{6,}[A-Z0-9]?\b",
            "[ID_REDACTED]",
        ),
    ]

    all_patterns = default_patterns + (patterns or [])

    result = text
    for pattern, replacement in all_patterns:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    return result


# ----------------------------------------------------------------------
# Filename and path sanitization
# ----------------------------------------------------------------------

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def sanitize_filename(name: str, max_length: int = 200) -> str:
    """Sanitize a string to be safe as a filename.

    Removes path separators, control characters, null bytes, and collapses
    whitespace. Keeps alphanumeric characters, hyphens, underscores, and dots.

    Args:
        name: Raw name to sanitize.
        max_length: Maximum length of the result (default 200).

    Returns:
        Safe filename string.
    """
    if not name:
        return "untitled"

    # Remove control characters and null bytes
    name = _CONTROL_CHARS.sub("", name)

    # Remove path separators and dangerous characters
    name = name.replace("\\", "_").replace("/", "_")
    name = name.replace("\x00", "")

    # Replace whitespace runs with single underscore
    name = re.sub(r"\s+", "_", name)

    # Keep only safe characters: alphanumeric, hyphen, underscore, dot
    # Also allow some unicode letters for international titles
    name = re.sub(r"[^a-zA-Z0-9áéíóúüñÁÉÍÓÚÜÑäëïöüÄËÏÖÜÀàÈèÌìÒòÙù\s\-_.]", "", name)

    # Collapse multiple dots/hyphens/underscores
    name = re.sub(r"\.{2,}", ".", name)
    name = re.sub(r"-{2,}", "-", name)
    name = re.sub(r"_{2,}", "_", name)

    # Strip leading/trailing dots, hyphens, underscores
    name = name.strip(".-_")

    # Limit length
    if len(name) > max_length:
        name = name[: max_length - 3] + "..."

    if not name:
        name = "untitled"

    return name


def sanitize_path(base: Path, user_path: str | Path) -> Path:
    """Sanitize a user-provided path within a base directory.

    Prevents path traversal attacks by resolving the path and ensuring
    it stays within the base directory.

    Args:
        base: The base directory that must contain the result.
        user_path: User-provided path or path component.

    Returns:
        Resolved path within base.

    Raises:
        ValueError: If the resulting path escapes the base directory.
    """
    base = base.resolve()
    user_path = Path(user_path)

    # If user_path is absolute or contains traversal, reject
    if user_path.is_absolute():
        raise ValueError(f"Absolute paths not allowed: {user_path}")

    combined = (base / user_path).resolve()

    # Check containment
    try:
        combined.relative_to(base)
    except ValueError:
        raise ValueError(
            f"Path traversal detected: {user_path} escapes base {base}"
        ) from None

    return combined


# ----------------------------------------------------------------------
# File type detection
# ----------------------------------------------------------------------

VIDEO_EXTENSIONS = frozenset(
    {
        ".mp4", ".mov", ".mkv", ".webm", ".avi",
        ".m4v", ".mpeg", ".mpg", ".flv", ".wmv",
    }
)


def is_video_file_ext(path: str | Path) -> bool:
    """Check if a file has a recognized video extension.

    Args:
        path: Path to check.

    Returns:
        True if the file extension is a recognized video format.
    """
    return Path(path).suffix.lower() in VIDEO_EXTENSIONS


# ----------------------------------------------------------------------
# Hashing
# ----------------------------------------------------------------------


def compute_sha256(file_path: str | Path, chunk_size: int = 65536) -> str:
    """Compute SHA-256 hash of a file.

    Reads the file in chunks to handle large files efficiently.

    Args:
        file_path: Path to the file.
        chunk_size: Read buffer size in bytes (default 64KB).

    Returns:
        Hexadecimal SHA-256 digest string.

    Raises:
        FileNotFoundError: If the file does not exist.
        IOError: If the file cannot be read.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


# ----------------------------------------------------------------------
# Text helpers
# ----------------------------------------------------------------------


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug.

    Lowercases, removes non-alphanumeric characters (except hyphens),
    collapses whitespace and hyphens.

    Args:
        text: Text to slugify.

    Returns:
        URL-safe slug string.
    """
    if not text:
        return "untitled"

    text = text.lower().strip()
    # Replace non-alnum (except hyphen) with space
    text = re.sub(r"[^a-z0-9\-]", " ", text)
    # Collapse spaces to single hyphen
    text = re.sub(r"\s+", "-", text)
    # Collapse multiple hyphens
    text = re.sub(r"-+", "-", text)
    # Strip leading/trailing hyphens
    text = text.strip("-")

    return text if text else "untitled"


# ----------------------------------------------------------------------
# Duration parsing
# ----------------------------------------------------------------------


def parse_duration(value: str | int | float) -> float:
    """Parse a duration value into seconds.

    Accepts:
    - Plain number: interpreted as seconds.
    - String "MM:SS" or "M:SS": minutes:seconds format.
    - String "H:MM:SS" or "HH:MM:SS": hours:minutes:seconds format.
    - String "Xs", "Xm", "Xh": explicit unit suffixes.
    - String "HH:MM:SS.mmm": with milliseconds.

    Args:
        value: Duration value to parse.

    Returns:
        Duration in seconds as a float.

    Raises:
        ValueError: If the format cannot be parsed.
    """
    if isinstance(value, (int, float)):
        return float(value)

    value = str(value).strip()

    if not value:
        raise ValueError("Empty duration string")

    # Handle explicit unit suffix
    unit_match = re.match(r"^(\d+(?:\.\d+)?)\s*(s|sec|second|seconds|m|min|minute|minutes|h|hr|hour|hours)$", value, re.IGNORECASE)
    if unit_match:
        num = float(unit_match.group(1))
        unit = unit_match.group(2).lower()
        if unit.startswith("s"):
            return num
        elif unit.startswith("m"):
            return num * 60
        elif unit.startswith("h"):
            return num * 3600

    # Handle HH:MM:SS[.mmm] or MM:SS[.mmm]
    time_match = re.match(
        r"^(\d{1,2}):(\d{2}):(\d{2}(?:\.\d+)?)$", value
    )
    if time_match:
        hours = int(time_match.group(1))
        minutes = int(time_match.group(2))
        seconds = float(time_match.group(3))
        return hours * 3600 + minutes * 60 + seconds

    # Handle MM:SS[.mmm]
    mm_ss_match = re.match(r"^(\d{1,2}):(\d{2}(?:\.\d+)?)$", value)
    if mm_ss_match:
        minutes = int(mm_ss_match.group(1))
        seconds = float(mm_ss_match.group(2))
        return minutes * 60 + seconds

    # Try as float
    try:
        return float(value)
    except ValueError:
        pass

    raise ValueError(f"Cannot parse duration: {value!r}")


# ----------------------------------------------------------------------
# Human-readable sizes
# ----------------------------------------------------------------------


def sizeof_fmt(num_bytes: int | float, precision: int = 2) -> str:
    """Format a byte count as a human-readable string.

    Args:
        num_bytes: Number of bytes.
        precision: Decimal places for KB and above (default 2).

    Returns:
        Human-readable size string (e.g., '1.5 MB').
    """
    if num_bytes == 0:
        return "0 B"

    abs_bytes = abs(num_bytes)
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    unit_index = 0

    while abs_bytes >= 1024 and unit_index < len(units) - 1:
        abs_bytes /= 1024
        unit_index += 1

    sign = "-" if num_bytes < 0 else ""
    if unit_index == 0:
        return f"{sign}{int(abs_bytes)} {units[unit_index]}"
    return f"{sign}{abs_bytes:.{precision}f} {units[unit_index]}"


# ----------------------------------------------------------------------
# YAML and config
# ----------------------------------------------------------------------


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Safely load a YAML file.

    Uses yaml.safe_load to avoid arbitrary code execution.

    Args:
        path: Path to the YAML file.

    Returns:
        Parsed YAML content as a dictionary. Empty dict if file is empty.

    Raises:
        FileNotFoundError: If the file does not exist.
        yaml.YAMLError: If the YAML is invalid.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        content = yaml.safe_load(f)

    if content is None:
        return {}
    if not isinstance(content, dict):
        raise ValueError(f"YAML file does not contain a mapping: {path}")
    return content


def merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries.

    Values from `override` take precedence. Nested dicts are merged
    recursively. Lists in `override` replace lists in `base` entirely
    (no list merging).

    Args:
        base: Base dictionary.
        override: Override dictionary (takes precedence).

    Returns:
        New merged dictionary.
    """
    result = dict(base)
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = merge_dict(result[key], value)
        else:
            result[key] = value
    return result


# ----------------------------------------------------------------------
# Video MIME type detection via magic bytes
# ----------------------------------------------------------------------

VIDEO_MAGIC_BYTES = {
    b"\x00\x00\x00\x1cftypmp4": "mp4",
    b"\x00\x00\x00\x1cftypM4A": "m4a",
    b"\x00\x00\x00\x1cftypmov": "mov",
    b"\x00\x00\x00\x1cftypqt": "mov",
    b"\x1a\x45\xdf\xa3": "webm/mkv",  # WebM/Matroska EBML
    b"\x52\x49\x46\x46": "avi/rm",  # RIFF header (AVI, WAV, etc.)
    b"\x00\x00\x01\xba": "mpeg-ps",  # MPEG-2 Program Stream
    b"\x00\x00\x01\xb3": "mpeg-ps",
    b"\x00\x00\x01\xe0": "mpeg-ps",
    b"\x00\x00\x01\xe1": "mpeg-ps",
}


def detect_video_mime(path: str | Path) -> str:
    """Detect video MIME type from file magic bytes.

    Args:
        path: Path to the file.

    Returns:
        Detected MIME type string, or 'unknown' if not recognized.
    """
    path = Path(path)
    if not path.exists():
        return "unknown"

    try:
        with open(path, "rb") as f:
            header = f.read(16)
    except OSError:
        return "unknown"

    for magic, mime in VIDEO_MAGIC_BYTES.items():
        if header.startswith(magic):
            return mime

    return "unknown"


__all__ = [
    "validate_url",
    "sanitize_for_prompt",
    "redact_sensitive_data",
    "sanitize_filename",
    "sanitize_path",
    "is_video_file_ext",
    "compute_sha256",
    "slugify",
    "parse_duration",
    "sizeof_fmt",
    "load_yaml",
    "merge_dict",
    "detect_video_mime",
    "VIDEO_EXTENSIONS",
]
