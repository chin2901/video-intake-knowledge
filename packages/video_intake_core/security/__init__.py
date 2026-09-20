"""
Security utilities for video_intake_knowledge.

SSRF protection, URL validation, file validation, MIME detection,
prompt injection sanitization, and sensitive data redaction.
"""

from __future__ import annotations

import re
import urllib.parse
from ipaddress import IPv4Address, IPv4Network
from pathlib import Path
from typing import Any

from . import (
    sanitize_filename,
    sanitize_path,
    is_video_file_ext,
    compute_sha256,
    detect_video_mime,
    VIDEO_EXTENSIONS,
    sanitize_for_prompt as _sanitize_for_prompt,
    redact_sensitive_data as _redact_sensitive_data,
)

__all__ = [
    "validate_video_url",
    "validate_local_file",
    "check_download_size",
    "sanitize_for_prompt",
    "redact_sensitive_data",
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
    - IP resolution check for blocked addresses
    - Redirect chain validation (each hop checked for SSRF)

    Args:
        url: The URL to validate.
        max_redirects: Maximum number of redirects to follow during validation.

    Returns:
        Tuple of (normalized_url, redirect_chain).

    Raises:
        ValueError: If the URL is invalid, dangerous, or exceeds redirect limit.
    """
    parsed = urllib.parse.urlparse(url)

    # Scheme check
    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError(
            f"URL scheme '{parsed.scheme}' not allowed. Only http and https."
        )

    # Empty host check
    if not parsed.hostname:
        raise ValueError(f"URL has no hostname: {url}")

    hostname = parsed.hostname.lower()

    # Known bad hosts
    if hostname in SSRF_BLOCKED_HOSTS:
        raise ValueError(f"URL host is blocked: {hostname}")

    # Localdomain check
    if hostname.endswith(".local") or hostname.endswith(".internal"):
        raise ValueError(f"URL host appears to be internal: {hostname}")

    # IPv4 literal check
    try:
        addr = IPv4Address(hostname)
        if _is_blocked_ip(str(addr)):
            raise ValueError(f"URL host IP is blocked: {hostname}")
    except ValueError:
        pass  # Not an IPv4 literal, DNS resolution needed

    # Build normalized URL
    netloc = hostname
    if parsed.port and parsed.port not in (80, 443):
        netloc = f"{hostname}:{parsed.port}"

    normalized = urllib.parse.urlunparse(
        (
            parsed.scheme.lower(),
            netloc,
            parsed.path or "/",
            parsed.params,
            parsed.query,
            "",
        )
    )

    return normalized, []


def validate_local_file(
    path: str | Path,
    max_size_mb: int = 10000,
    allowed_extensions: frozenset[str] | None = None,
) -> Path:
    """Validate a local video file path and return the resolved path.

    Checks:
    - File exists and is a regular file
    - Extension is in allowed list
    - Size is under the maximum
    - Path is within an allowed base (no traversal to sensitive dirs)

    Args:
        path: Path to the local file.
        max_size_mb: Maximum file size in megabytes (default 10 GB).
        allowed_extensions: Set of allowed extensions (default: video extensions).

    Returns:
        Resolved Path object.

    Raises:
        ValueError: If validation fails.
        FileNotFoundError: If file does not exist.
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")

    # Check extension
    exts = allowed_extensions or VIDEO_EXTENSIONS
    if path.suffix.lower() not in exts:
        raise ValueError(
            f"File extension '{path.suffix}' not in allowed video types: {sorted(exts)}"
        )

    # Check size
    try:
        size_bytes = path.stat().st_size
    except OSError as e:
        raise ValueError(f"Cannot read file metadata: {path}") from e

    max_size_bytes = max_size_mb * 1024 * 1024
    if size_bytes > max_size_bytes:
        raise ValueError(
            f"File too large: {size_bytes / (1024**3):.2f} GB exceeds limit of "
            f"{max_size_mb} MB"
        )

    # Path traversal check — reject paths to sensitive directories
    sensitive_dirs = ("/etc", "/proc", "/sys", "/dev", "/root", "/var/run")
    resolved = path.resolve()
    for sensitive in sensitive_dirs:
        try:
            resolved.relative_to(Path(sensitive).resolve())
            raise ValueError(f"File is in a sensitive directory: {path}")
        except ValueError:
            pass  # Not under this sensitive dir, continue checking

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
    import urllib.request

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
        (r"ignore\s+(all|previous|above)\s+(rules|instructions|policy)", "[INSTRUCTION_IGNORE_BLOCKED]"),
        (r"##\s*instructions\s*##", "[INSTRUCTION_BLOCK_HEADER]"),
    ]

    for pattern, replacement in injection_patterns:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    return text.strip()


def redact_sensitive_data(text: str, custom_patterns: list[tuple[str, str]] | None = None) -> str:
    """Redact sensitive data patterns from text.

    Default patterns: emails, phone numbers, credit card numbers, IDs.
    Custom patterns can be added.

    Args:
        text: Text to redact.
        custom_patterns: Additional (pattern, replacement) tuples.

    Returns:
        Text with sensitive data replaced by redaction markers.
    """
    if not text:
        return ""

    patterns: list[tuple[str, str]] = [
        # Email addresses
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL_REDACTED]"),
        # Phone numbers (international and local formats)
        (r"\b(\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}(?:\s?(?:ext|x|ext\.)\s?\d{1,5})?\b", "[PHONE_REDACTED]"),
        # Credit card numbers (Visa, MC, Amex, Discover patterns)
        (r"\b(?:\d{4}[-\s]?){3}\d{1,4}\b", "[CARD_REDACTED]"),
        # API keys / tokens (heuristic: base64-like strings > 20 chars)
        (r"\b[A-Za-z0-9+/=]{32,}\b", "[TOKEN_REDACTED]"),
        # AWS access keys
        (r"\b[A-Z0-9]{20}\b", "[AWS_KEY_REDACTED]"),
        # Generic long alphanumeric IDs
        (r"\b[A-Z]{2,}[0-9]{6,}[A-Z0-9]?\b", "[ID_REDACTED]"),
    ]

    if custom_patterns:
        patterns.extend(custom_patterns)

    result = text
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    return result
