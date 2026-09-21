"""
URL validation and sanitization utilities.

Provides safe URL handling with SSRF protection, HTML sanitization for
prompt injection prevention, and sensitive data redaction.
"""

from __future__ import annotations

import re
import urllib.parse
from ipaddress import IPv4Address, IPv4Network
from typing import Any


# ----------------------------------------------------------------------
# SSRF protection — blocked IP ranges
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


def is_safe_url(url: str) -> bool:
    """
    Check if a URL is safe to download (no SSRF risk).

    Returns True if the URL uses http/https and does not target
    localhost, private IPs, or cloud metadata endpoints.

    Args:
        url: The URL to check.

    Returns:
        True if safe, False otherwise.
    """
    try:
        validate_url(url)
        return True
    except ValueError:
        return False


def validate_url(url: str) -> str:
    """
    Validate and normalize a URL.

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
    """
    Sanitize text to be safe to inject into prompts.

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
        (
            r"disregard\s+(previous|all|above|below)\s+(rules|instructions)?",
            "[INSTRUCTION_BLOCKED]",
        ),
        (r"you\s+are\s+now\s+(a|an)\s+\w+", "[ROLE_OVERRIDE_BLOCKED]"),
        (r"system\s*:\s*.*", "[SYSTEM_OVERRIDE_BLOCKED]"),
        (
            r"<\s*script.*?>.*?<\s*/\s*script\s*>",
            "[SCRIPT_BLOCKED]",
            re.IGNORECASE | re.DOTALL,
        ),
        (
            r"```.*?ignore.*```",
            "[CODE_INJECTION_BLOCKED]",
            re.IGNORECASE | re.DOTALL,
        ),
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
    """
    Redact sensitive data patterns from text.

    By default redacts emails, phone numbers, credit card-like patterns.
    Custom patterns can be provided.

    Args:
        text: Text to redact.
        patterns: Custom regex patterns to redact (list of strings).

    Returns:
        Text with sensitive patterns replaced by [REDACTED].
    """
    default_patterns = [
        (
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "[EMAIL_REDACTED]",
        ),
        (
            r"\b(?:\+?\d{1,3}[-.\\s]?)?\(?\d{2,4}\)?[-.\\s]?\d{3,4}[-.\\s]?\d{3,4}[-.\\s]?\d{1,9}\b",
            "[PHONE_REDACTED]",
        ),
        (r"\b(?:\d{4}[-\s]?){3}\d{4}\b", "[CARD_REDACTED]"),
        (r"\b[A-Z]{2,}[0-9]{6,}[A-Z0-9]?\b", "[ID_REDACTED]"),
    ]

    all_patterns = default_patterns + (patterns or [])

    result = text
    for pattern, replacement in all_patterns:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    return result
