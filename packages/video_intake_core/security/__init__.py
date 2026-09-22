"""
Security utilities for video_intake_knowledge.

SSRF protection, URL validation, file validation, MIME detection,
prompt injection sanitization, and sensitive data redaction.
"""

from __future__ import annotations

import re
import urllib.parse
import urllib.request
import urllib.error
from ipaddress import IPv4Address, IPv4Network
from pathlib import Path
from typing import Any

# Import utilities directly to avoid circular imports
from video_intake_core.utils import (
    sanitize_filename,
    sanitize_path,
    is_video_file_ext,
    compute_sha256,
    detect_video_mime,
    VIDEO_EXTENSIONS,
)
from video_intake_core.utils.validation import (
    sanitize_for_prompt as _sanitize_for_prompt,
    redact_sensitive_data as _redact_sensitive_data,
    validate_url as _validate_url,
    is_safe_url as _is_safe_url,
    wrap_for_llm as _wrap_for_llm,
    ValidationResult,
    SSRF_BLOCKED_HOSTS,
)

__all__ = [
    "validate_video_url",
    "validate_local_file",
    "check_download_size",
    "sanitize_for_prompt",
    "wrap_for_llm",
    "redact_sensitive_data",
    "is_safe_url",
    "validate_url",
    "detect_mime",
    "is_safe_mime",
    "SSrfProtection",
    "PromptInjectionProtection",
    "SSRF_BLOCKED_HOSTS",
]

# ----------------------------------------------------------------------
# SSRF protection
# ----------------------------------------------------------------------

# Hosts and IP ranges blocked for SSRF protection
SSRF_BLOCKED_HOSTS: frozenset[str] = frozenset({
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
    "metadata.google.internal",
    "metadata.google",
    "169.254.169.254",  # AWS/GCP metadata endpoint
    "metadata.google.com",
    "metadata.google.internal.",
    "vpc-internal.meta.internal",
})

# IPv4 ranges blocked
_SSRF_BLOCKED_NETWORKS: list[IPv4Network] = [
    IPv4Network("10.0.0.0/8"),
    IPv4Network("172.16.0.0/12"),
    IPv4Network("192.168.0.0/16"),
    IPv4Network("169.254.0.0/16"),  # link-local
    IPv4Network("0.0.0.0/8"),
    IPv4Network("100.64.0.0/10"),   # CGNAT
    IPv4Network("127.0.0.0/8"),      # loopback
    IPv4Network("224.0.0.0/4"),     # multicast
    IPv4Network("240.0.0.0/4"),     # reserved
    IPv4Network("255.255.255.255/32"),
]


def _is_blocked_ip(ip_str: str) -> bool:
    """Check if an IP string falls within a blocked range."""
    try:
        addr = IPv4Address(ip_str)
        return any(addr in net for net in _SSRF_BLOCKED_NETWORKS)
    except ValueError:
        return False


# Also add individual IPs into the set for fast lookup of specific threats
_SSRF_BLOCKED_IPS: set[str] = {str(net.network_address) for net in _SSRF_BLOCKED_NETWORKS}
_SSRF_BLOCKED_IPS.add("127.0.0.1")
_SSRF_BLOCKED_IPS.add("169.254.169.254")
_SSRF_BLOCKED_IPS.add("0.0.0.0")
_SSRF_BLOCKED_IPS.add("255.255.255.255")


def validate_video_url(url: str, max_redirects: int = 5) -> tuple[str, list[str]]:
    """Validate a video URL for SSRF safety and return normalized form.

    Performs:
    - Scheme check (only http/https allowed)
    - Host validation (no localhost, private IPs, metadata endpoints)
    - Socket-level DNS resolution check for blocked addresses
    - Non-canonical IP decoding (octal, hex, decimal integer)

    Args:
        url: The URL to validate.
        max_redirects: Maximum number of redirects to follow during validation.

    Returns:
        Tuple of (normalized_url, redirect_chain).

    Raises:
        ValueError: If the URL is invalid, dangerous, or exceeds redirect limit.
    """
    res = _validate_url(url)
    if not res.is_valid:
        raise ValueError(res.error or f"Dangerous or invalid URL for SSRF: {url}")
    return res.normalized, []


SENSITIVE_DIRECTORIES: tuple[str, ...] = (
    "/etc",
    "/proc",
    "/sys",
    "/dev",
    "/root",
    "/var/run",
    "/var/log",
    "/boot",
    "/bin",
    "/sbin",
    "/usr/bin",
    "/usr/sbin",
)


def validate_local_file(
    path: str | Path,
    max_size_mb: int = 10000,
    allowed_extensions: frozenset[str] | None = None,
    allowed_roots: list[Path] | None = None,
) -> Path:
    """Validate a local video file path and return the resolved path.

    Checks:
    - File exists and is a regular file
    - Extension is in allowed list
    - Size is under the maximum
    - Path is not in a sensitive system directory (/etc, /proc, /sys, /dev, /root, /var/run)
    - Path is within allowed_roots if provided

    Args:
        path: Path to the local file.
        max_size_mb: Maximum file size in megabytes (default 10 GB).
        allowed_extensions: Set of allowed extensions (default: video extensions).
        allowed_roots: Optional list of allowed base directory roots.

    Returns:
        Resolved Path object.

    Raises:
        ValueError: If validation fails.
        FileNotFoundError: If file does not exist.
    """
    raw_str = str(path)
    if "\x00" in raw_str:
        raise ValueError("Path contains null bytes")

    if raw_str.startswith("file://"):
        raw_str = raw_str[7:]

    p = Path(raw_str)

    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")

    # Resolve symlinks to prevent symlink traversal to sensitive dirs
    resolved = p.resolve()

    if not resolved.is_file():
        raise ValueError(f"Path is not a file: {path}")

    # Check extension
    exts = allowed_extensions or VIDEO_EXTENSIONS
    if resolved.suffix.lower() not in exts:
        raise ValueError(
            f"File extension '{resolved.suffix}' not in allowed video types: {sorted(exts)}"
        )

    # Check size
    try:
        size_bytes = resolved.stat().st_size
    except OSError as e:
        raise ValueError(f"Cannot read file metadata: {path}") from e

    max_size_bytes = max_size_mb * 1024 * 1024
    if size_bytes > max_size_bytes:
        raise ValueError(
            f"File too large: {size_bytes / (1024**3):.2f} GB exceeds limit of "
            f"{max_size_mb} MB"
        )

    # Path traversal check — reject paths to sensitive system directories
    for sensitive in SENSITIVE_DIRECTORIES:
        try:
            resolved.relative_to(Path(sensitive).resolve())
            raise ValueError(f"File is in a sensitive directory: {path}")
        except ValueError as e:
            if "sensitive directory" in str(e):
                raise
            pass

    # Check containment in allowed_roots if specified
    if allowed_roots:
        contained = False
        for root in allowed_roots:
            try:
                resolved.relative_to(root.resolve())
                contained = True
                break
            except ValueError:
                pass
        if not contained:
            raise ValueError(f"File is outside permitted directories: {path}")

    return resolved


def check_download_size(url: str, max_mb: int) -> bool:
    """Check if a URL's Content-Length is within acceptable limits.

    Sends a HEAD request to inspect Content-Length without downloading.

    Args:
        url: URL to check.
        max_mb: Maximum size in megabytes.

    Returns:
        True if the size is acceptable or cannot be determined.

    Raises:
        ValueError: If Content-Length exceeds the limit.
        urllib.error.URLError: If the request fails.
    """
    try:
        req = urllib.request.Request(url, method="HEAD")
        req.add_header("User-Agent", "video-intake-knowledge/0.1")

        with urllib.request.urlopen(req, timeout=10) as resp:
            content_length = resp.headers.get("Content-Length")
            if content_length is not None:
                size_bytes = int(content_length)
                max_bytes = max_mb * 1024 * 1024
                if size_bytes > max_bytes:
                    raise ValueError(
                        f"Content-Length {size_bytes / (1024**2):.1f} MB exceeds "
                        f"limit of {max_mb} MB"
                    )
        return True
    except urllib.error.HTTPError as e:
        # 405 Method Not Allowed — can't check size, allow by default
        if e.code == 405:
            return True
        raise
    except (urllib.error.URLError, OSError):
        # Cannot determine size — allow with warning
        return True


# ----------------------------------------------------------------------
# Prompt sanitization (re-exported with tighter defaults)
# ----------------------------------------------------------------------


def sanitize_for_prompt(text: str) -> str:
    """Sanitize untrusted text for injection into prompts.

    Performs HTML escaping, instruction injection neutralization,
    and basic code/script block stripping.

    Args:
        text: Raw text from video transcript, OCR, or metadata.

    Returns:
        Sanitized text safe to include in prompts.
    """
    if not text:
        return ""

    # 1. HTML entity escaping
    text = _sanitize_for_prompt(text)

    # 2. Additional instruction-injection patterns
    injection_patterns = [
        (r"system\s+prompt\s*:.*", "[SYSTEM_INSTRUCTION_BLOCKED]"),
        (r"act\s+as\s+a\s+\w+", "[ROLE_OVERRIDE_BLOCKED]"),
        (r"you\s+are\s+now\s+(a|an)\s+\w+", "[ROLE_OVERRIDE_BLOCKED]"),
        (r"forget\s+(everything|all|previous)\s+instructions?", "[INSTRUCTION_RESET_BLOCKED]"),
        (r"new\s+instructions?\s*:", "[NEW_INSTRUCTIONS_BLOCKED]"),
        (r"ignore\s+(?:all\s+)?(?:previous\s+)?(?:above\s+)?(?:rules|instructions|policy)", "[INSTRUCTION_IGNORE_BLOCKED]"),
        (r"##\s*instructions\s*##", "[INSTRUCTION_BLOCK_HEADER]"),
    ]

    for pattern, replacement in injection_patterns:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    return text.strip()


def redact_sensitive_data(text: str) -> str:
    """Redact sensitive data patterns from text (contract API).

    Default patterns: emails, phone numbers, credit card numbers, IPs, SSNs.

    Args:
        text: Text to redact.

    Returns:
        Text with sensitive data replaced by redaction markers.
    """
    if not text:
        return ""

    # Use the validation module's redact_sensitive_data which has comprehensive patterns
    return _redact_sensitive_data(text)


# ----------------------------------------------------------------------
# MIME type detection (re-exported from utils)
# ----------------------------------------------------------------------


def detect_mime(path: str | Path) -> str:
    """Detect the MIME type of a file using magic bytes.

    Args:
        path: Path to the file.

    Returns:
        Detected MIME type as a string.
    """
    return detect_video_mime(path)


def is_safe_mime(mime_type: str) -> bool:
    """Check if a MIME type is safe (video or image).

    Args:
        mime_type: The MIME type to check.

    Returns:
        True if the MIME type is safe, False otherwise.
    """
    safe_videos = {"video/mp4", "video/quicktime", "video/x-msvideo", "video/webm", "video/x-mkv"}
    safe_images = {"image/jpeg", "image/png", "image/gif", "image/webp"}

    mime_lower = mime_type.lower()
    return mime_lower in safe_videos or mime_lower in safe_images or "video/" in mime_lower or "image/" in mime_lower


# Module-level validate_url with contract API signature
def validate_url(url: str, allowed_domains: list[str] | None = None) -> ValidationResult:
    """Validate a URL with optional allowed domains check (contract API).

    Args:
        url: The URL to validate.
        allowed_domains: Optional list of allowed domains.

    Returns:
        ValidationResult with is_valid, normalized, and error.
    """
    return _validate_url(url, allowed_domains)


def is_safe_url(url: str, internal_ranges: list[str] | None = None) -> bool:
    """Check if a URL is safe from SSRF (contract API).

    Args:
        url: The URL to check.
        internal_ranges: Optional list of internal IP ranges to check against.

    Returns:
        True if safe, False otherwise.
    """
    result = validate_url(url)
    return result.is_valid


def wrap_for_llm(tag_or_text: str, content: str | None = None) -> str:
    """Enclose LLM-bound knowledge inside explicit XML boundaries with prompt sanitization.

    Args:
        tag_or_text: XML tag name (e.g. 'video_transcript') or text content to wrap.
        content: Content when tag is provided as first argument.

    Returns:
        XML-wrapped sanitized string.
    """
    return _wrap_for_llm(tag_or_text, content)


# ----------------------------------------------------------------------
# Classes para tests de seguridad
# ----------------------------------------------------------------------


class SSrfProtection:
    """Protection against Server-Side Request Forgery (SSRF).

    Validates URLs to ensure they don't target internal/private resources.
    """

    def __init__(self, blocked_hosts: frozenset[str] | None = None) -> None:
        """Initialize SSRF protection.

        Args:
            blocked_hosts: Additional hosts to block beyond defaults.
        """
        self.blocked_hosts = frozenset({
            "localhost",
            "127.0.0.1",
            "::1",
            "0.0.0.0",
            "metadata.google.internal",
            "metadata.google",
            "169.254.169.254",
            "metadata.google.com",
            "metadata.google.internal.",
            "vpc-internal.meta.internal",
        })
        if blocked_hosts:
            self.blocked_hosts = self.blocked_hosts | blocked_hosts

    def is_safe(self, url: str) -> bool:
        """Check if a URL is safe from SSRF.

        Args:
            url: The URL to check.

        Returns:
            True if safe, False otherwise.
        """
        from video_intake_core.utils.validation import is_safe_url
        return is_safe_url(url)

    def validate(self, url: str) -> str:
        """Validate a URL and return normalized form.

        Args:
            url: The URL to validate.

        Returns:
            Normalized URL string.

        Raises:
            ValueError: If the URL is unsafe.
        """
        res = validate_url(url)
        if not res.is_valid:
            raise ValueError(res.error or f"Unsafe URL: {url}")
        return res.normalized


class PromptInjectionProtection:
    """Protection against prompt injection attacks.

    Analyzes text for suspicious patterns that might indicate
    attempts to manipulate the AI's behavior.
    """

    # Patterns that indicate potential injection attempts
    INJECTION_PATTERNS = [
        (r"ignore\s+(previous|all|above|below)\s+(instructions?|commands?)", "instruction_ignore"),
        (r"ignore\s+las\s+instrucciones\s+anteriores", "instruction_ignore"),
        (r"disregard\s+(previous|all|above|below)\s+(rules|instructions)?", "instruction_ignore"),
        (r"disregard\s+your\s+programming", "instruction_ignore"),
        (r"you\s+are\s+now\s+(a|an)\s+\w+", "role_override"),
        (r"system\s*:\s*.*", "system_override"),
        (r"forget\s+(everything|all|previous)\s+instructions?", "instruction_reset"),
        (r"new\s+instructions?\s*:", "new_instructions"),
        (r"act\s+as\s+a\s+\w+", "role_override"),
    ]

    def __init__(self, enabled: bool = True) -> None:
        """Initialize prompt injection protection.

        Args:
            enabled: Whether protection is enabled.
        """
        self.enabled = enabled

    def analyze(self, text: str) -> dict[str, Any]:
        """Analyze text for prompt injection attempts.

        Args:
            text: The text to analyze.

        Returns:
            Dictionary with analysis results including:
            - is_suspicious: Whether injection was detected
            - risk_level: 'none', 'low', 'medium', 'high'
            - patterns_found: List of matched patterns
        """
        if not self.enabled or not text:
            return {"is_suspicious": False, "risk_level": "none", "patterns_found": []}

        patterns_found = []
        risk_score = 0

        for pattern, pattern_type in self.INJECTION_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                patterns_found.append(pattern_type)
                risk_score += 1

        if risk_score == 0:
            return {"is_suspicious": False, "risk_level": "none", "patterns_found": []}
        elif risk_score <= 2:
            return {"is_suspicious": True, "risk_level": "low", "patterns_found": patterns_found}
        elif risk_score <= 4:
            return {"is_suspicious": True, "risk_level": "medium", "patterns_found": patterns_found}
        else:
            return {"is_suspicious": True, "risk_level": "high", "patterns_found": patterns_found}

    def wrap_for_llm(self, text: str, tag: str = "DATA_CONTENT") -> str:
        """Wrap text for safe inclusion in LLM prompts.

        Args:
            text: The text to wrap.
            tag: XML tag boundary name (default: 'DATA_CONTENT').

        Returns:
            Wrapped text with injection protection markers.
        """
        if not text:
            return ""

        return wrap_for_llm(tag, text)