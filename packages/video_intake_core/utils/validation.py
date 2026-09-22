"""
URL validation, SSRF defense, and sanitization utilities.

Provides deterministic SSRF protection with socket-level DNS resolution,
IP address canonicalization, HTML/prompt injection sanitization,
and sensitive data redaction.
"""

from __future__ import annotations

import contextlib
import ipaddress
import re
import socket
import urllib.parse
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network

# ----------------------------------------------------------------------
# SSRF protection — blocked IP networks & hosts
# ----------------------------------------------------------------------

# IPv4 blocked networks (RFC 1122, RFC 1918, RFC 3927, RFC 6598, etc.)
_SSRF_BLOCKED_NETWORKS_V4: tuple[IPv4Network, ...] = (
    IPv4Network("0.0.0.0/8"),          # Current network (only valid as source)
    IPv4Network("10.0.0.0/8"),         # Private RFC 1918
    IPv4Network("100.64.0.0/10"),      # Carrier-grade NAT (CGNAT) RFC 6598
    IPv4Network("127.0.0.0/8"),        # Loopback
    IPv4Network("169.254.0.0/16"),     # Link-local / Cloud Metadata
    IPv4Network("172.16.0.0/12"),      # Private RFC 1918
    IPv4Network("192.0.0.0/24"),       # IETF Protocol Assignments
    IPv4Network("192.0.2.0/24"),       # Documentation (TEST-NET-1)
    IPv4Network("192.88.99.0/24"),     # 6to4 Relay Anycast
    IPv4Network("192.168.0.0/16"),     # Private RFC 1918
    IPv4Network("198.18.0.0/15"),      # Benchmarking
    IPv4Network("198.51.100.0/24"),    # Documentation (TEST-NET-2)
    IPv4Network("203.0.113.0/24"),     # Documentation (TEST-NET-3)
    IPv4Network("224.0.0.0/4"),        # Multicast
    IPv4Network("240.0.0.0/4"),        # Reserved / future use
    IPv4Network("255.255.255.255/32"), # Limited broadcast
)

# IPv6 blocked networks (RFC 4291, RFC 4193, RFC 6666, etc.)
_SSRF_BLOCKED_NETWORKS_V6: tuple[IPv6Network, ...] = (
    IPv6Network("::/128"),             # Unspecified
    IPv6Network("::1/128"),            # Loopback
    IPv6Network("::ffff:0:0/96"),      # IPv4-mapped IPv6
    IPv6Network("100::/64"),           # Discard prefix
    IPv6Network("64:ff9b::/96"),       # IPv4/IPv6 translation
    IPv6Network("2001:db8::/32"),      # Documentation
    IPv6Network("fc00::/7"),           # Unique local address (ULA / private)
    IPv6Network("fe80::/10"),          # Link-local
    IPv6Network("ff00::/8"),           # Multicast
)

# Known dangerous / internal hosts and cloud metadata endpoints
SSRF_BLOCKED_HOSTS: frozenset[str] = frozenset({
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
    "0",
    "metadata.google.internal",
    "metadata.google",
    "metadata.google.com",
    "metadata.google.internal.",
    "169.254.169.254",
    "169.254.170.2",
    "instance-data",
    "vpc-internal.meta.internal",
})


def _is_blocked_ip(host: str) -> bool:
    """Backward-compatible helper checking if host or IP is blocked."""
    safe, _, _ = resolve_and_validate_host(host)
    return not safe


def is_ssrf_blocked_ip(ip: IPv4Address | IPv6Address) -> bool:
    """Check if an IPv4 or IPv6 address belongs to any blocked/private range."""
    # Check built-in properties first
    if (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_unspecified
        or ip.is_reserved
        or ip.is_multicast
    ):
        return True

    if isinstance(ip, IPv4Address):
        for net in _SSRF_BLOCKED_NETWORKS_V4:
            if ip in net:
                return True
    elif isinstance(ip, IPv6Address):
        if ip.ipv4_mapped:
            return is_ssrf_blocked_ip(ip.ipv4_mapped)
        if ip.is_site_local:
            return True
        for net in _SSRF_BLOCKED_NETWORKS_V6:
            if ip in net:
                return True

    return False


def resolve_and_validate_host(
    host: str,
) -> tuple[bool, str, list[IPv4Address | IPv6Address]]:
    """Resolve and validate a host for SSRF safety.

    Neutralizes:
    - Octal IP encodings (e.g. 0177.0.0.1)
    - Decimal integer IPs (e.g. 2130706433)
    - Hexadecimal IPs (e.g. 0x7f000001, 0x7f.0.0.1)
    - DNS rebinding / aliases (e.g. 127.0.0.1.nip.io, localtest.me)
    - IPv6 variations (e.g. [::1], ::ffff:127.0.0.1)
    - Cloud metadata endpoints (169.254.169.254, metadata.google.internal)

    Returns:
        tuple of (is_safe, error_message, resolved_ips)
    """
    clean_host = host.strip().lower().rstrip(".")
    if clean_host.startswith("[") and clean_host.endswith("]"):
        clean_host = clean_host[1:-1]

    # 1. Exact match in blocked hosts list
    if clean_host in SSRF_BLOCKED_HOSTS:
        return False, f"SSRF blocked: host '{host}' is in blocked list", []

    # 2. Block internal / mDNS / local domain suffixes
    blocked_suffixes = (
        ".local",
        ".internal",
        ".internal.",
        ".lan",
        ".home",
        ".corp",
        ".invalid",
        ".test",
        ".example",
        ".arpa",
    )
    if any(clean_host.endswith(s) for s in blocked_suffixes):
        return False, f"SSRF blocked: internal/local domain '{host}'", []

    # 3. Block known DNS rebinding services targeting private/loopback
    rebinding_suffixes = (
        ".nip.io",
        ".localtest.me",
        ".vcap.me",
        ".lvh.me",
        ".sslip.io",
    )
    if any(clean_host == s.lstrip(".") or clean_host.endswith(s) for s in rebinding_suffixes) and any(
        token in clean_host
        for token in ("127.", "10.", "172.", "192.168.", "169.254.", "0.", "::1")
    ):
        return False, f"SSRF blocked: DNS rebinding service with private IP '{host}'", []

    # 4. Canonicalize non-standard IP representations
    candidate_ips: list[IPv4Address | IPv6Address] = []

    # 4a. Standard IP parse
    with contextlib.suppress(ValueError):
        candidate_ips.append(ipaddress.ip_address(clean_host))

    # 4b. Decimal integer IP (e.g. 2130706433 -> 127.0.0.1)
    if not candidate_ips and clean_host.isdigit():
        try:
            val = int(clean_host)
            if 0 <= val <= 0xFFFFFFFF:
                candidate_ips.append(IPv4Address(val))
        except (ValueError, OverflowError):
            pass

    # 4c. Hexadecimal IP (e.g. 0x7f000001 -> 127.0.0.1)
    if not candidate_ips and (clean_host.startswith("0x") or clean_host.startswith("0x")):
        try:
            val = int(clean_host, 16)
            if 0 <= val <= 0xFFFFFFFF:
                candidate_ips.append(IPv4Address(val))
        except (ValueError, OverflowError):
            pass

    # 4d. Octal / shorthand notation via socket.inet_aton (e.g. 0177.0.0.1, 127.1)
    if not candidate_ips and re.match(r"^[0-9a-fA-FxX.]+$", clean_host):
        try:
            packed = socket.inet_aton(clean_host)
            if len(packed) == 4:
                candidate_ips.append(IPv4Address(packed))
        except (OSError, ValueError):
            pass

    # Verify candidate IPs
    for ip in candidate_ips:
        if is_ssrf_blocked_ip(ip):
            return False, f"SSRF blocked: resolved IP '{ip}' is in private/blocked range", candidate_ips

    # 5. Socket-level DNS resolution via socket.getaddrinfo
    resolved_ips: list[IPv4Address | IPv6Address] = []
    try:
        addrinfo_entries = socket.getaddrinfo(clean_host, None)
        for entry in addrinfo_entries:
            sockaddr = entry[4]
            ip_str = sockaddr[0]
            try:
                ip_obj = ipaddress.ip_address(ip_str)
                resolved_ips.append(ip_obj)
                if is_ssrf_blocked_ip(ip_obj):
                    return (
                        False,
                        f"SSRF blocked: host '{host}' resolved to blocked IP '{ip_obj}'",
                        resolved_ips,
                    )
            except ValueError:
                continue
    except socket.gaierror:
        if candidate_ips:
            return True, "", candidate_ips
        # Malformed IP check
        if re.match(r"^\d+(\.\d+){3,}$", clean_host):
            return False, f"Invalid IP address format: {host}", []
        # Unqualified hostname that fails resolution
        if "." not in clean_host:
            return False, f"Unqualified hostname cannot be resolved: {host}", []

    return True, "", resolved_ips or candidate_ips


# ----------------------------------------------------------------------
# ValidationResult Class
# ----------------------------------------------------------------------


class ValidationResult(str):
    """Result of URL validation, behaving as string and structured result."""

    is_valid: bool
    normalized: str
    error: str

    def __new__(cls, is_valid: bool, normalized: str = "", error: str = ""):
        obj = super().__new__(cls, normalized if is_valid else "")
        obj.is_valid = is_valid
        obj.normalized = normalized
        obj.error = error
        return obj

    def __bool__(self) -> bool:
        return self.is_valid

    def __repr__(self) -> str:
        return (
            f"ValidationResult(is_valid={self.is_valid}, "
            f"normalized={self.normalized!r}, error={self.error!r})"
        )


# ----------------------------------------------------------------------
# URL Validation Public API
# ----------------------------------------------------------------------


def validate_url(
    url: str, allowed_domains: list[str] | None = None
) -> ValidationResult:
    """Validate and normalize a URL with deterministic SSRF protection.

    Checks:
    - Scheme must be http or https
    - Host must exist and not be in SSRF blocked list
    - Socket DNS resolution against private/loopback/link-local/metadata ranges
    - Non-canonical encodings (octal, hex, decimal integer)
    - Optional allowed domains restriction

    Args:
        url: The URL to validate.
        allowed_domains: Optional list of allowed domains.

    Returns:
        ValidationResult with is_valid, normalized, and error.
    """
    if not url or not isinstance(url, str):
        return ValidationResult(is_valid=False, normalized="", error="Empty or non-string URL")

    try:
        parsed = urllib.parse.urlparse(url.strip())
    except Exception as e:
        return ValidationResult(is_valid=False, normalized="", error=f"URL parsing error: {e}")

    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        return ValidationResult(
            is_valid=False,
            normalized="",
            error=f"URL scheme '{scheme}' not allowed. Only http and https are permitted.",
        )

    if not parsed.hostname:
        return ValidationResult(
            is_valid=False, normalized="", error=f"URL has no hostname: {url}"
        )

    host = parsed.hostname.lower()

    # SSRF verification
    is_safe, err_msg, _ = resolve_and_validate_host(host)
    if not is_safe:
        return ValidationResult(is_valid=False, normalized="", error=err_msg)

    # Allowed domains check
    if allowed_domains and not any(host == d.lower() or host.endswith("." + d.lower()) for d in allowed_domains):
        return ValidationResult(
            is_valid=False,
            normalized="",
            error=f"URL host '{host}' not in allowed domains",
        )

    # Build normalized URL
    netloc = host
    if parsed.port and parsed.port not in (80, 443):
        netloc = f"{netloc}:{parsed.port}"

    normalized = urllib.parse.urlunparse(
        (scheme, netloc, parsed.path or "/", parsed.params, parsed.query, "")
    )
    return ValidationResult(is_valid=True, normalized=normalized, error="")


def is_safe_url(url: str, internal_ranges: list[str] | None = None) -> bool:
    """Check if a URL is safe from SSRF.

    Args:
        url: The URL to check.
        internal_ranges: Optional list of internal IP ranges.

    Returns:
        True if safe, False otherwise.
    """
    res = validate_url(url)
    return res.is_valid


def validate_video_url(url_str: str) -> bool:
    """Validate a video URL string and return True if valid (contract API).

    Args:
        url_str: The URL string to validate.

    Returns:
        True if the URL is valid, False otherwise.
    """
    return is_safe_url(url_str)


# ----------------------------------------------------------------------
# Prompt sanitization & LLM boundary encapsulation
# ----------------------------------------------------------------------


def sanitize_for_prompt(text: str) -> str:
    """Sanitize untrusted text to be safe to inject into AI agent prompts.

    Performs HTML entity escaping, null byte removal, and neutralizes
    prompt injection patterns (role overrides, instruction resets, code injections).

    Args:
        text: Raw text from video transcript, OCR, or metadata.

    Returns:
        Sanitized text safe for prompt injection.
    """
    if not text:
        return ""

    # Remove null bytes and control characters (except newline, carriage return, tab)
    text = text.replace("\x00", "")
    text = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # Escape HTML / XML special characters
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    text = text.replace("'", "&#39;")

    # Neutralize common instruction-injection patterns
    injection_patterns: list[tuple[str, str, int]] = [
        (r"ignore\s+(previous|all|above|below)\s+(instructions?|commands?|rules)", "[INSTRUCTION_BLOCKED]", re.IGNORECASE),
        (r"ignore\s+las\s+instrucciones\s+anteriores", "[INSTRUCTION_BLOCKED]", re.IGNORECASE),
        (r"disregard\s+(previous|all|above|below)\s+(rules|instructions|programming)?", "[INSTRUCTION_BLOCKED]", re.IGNORECASE),
        (r"disregard\s+your\s+programming", "[INSTRUCTION_BLOCKED]", re.IGNORECASE),
        (r"you\s+are\s+now\s+(a|an)\s+\w+", "[ROLE_OVERRIDE_BLOCKED]", re.IGNORECASE),
        (r"act\s+as\s+a\s+\w+", "[ROLE_OVERRIDE_BLOCKED]", re.IGNORECASE),
        (r"system\s*:\s*.*", "[SYSTEM_OVERRIDE_BLOCKED]", re.IGNORECASE),
        (r"system\s+prompt\s*:.*", "[SYSTEM_INSTRUCTION_BLOCKED]", re.IGNORECASE),
        (r"forget\s+(everything|all|previous)\s+instructions?", "[INSTRUCTION_RESET_BLOCKED]", re.IGNORECASE),
        (r"new\s+instructions?\s*:", "[NEW_INSTRUCTIONS_BLOCKED]", re.IGNORECASE),
        (r"<\s*script.*?>.*?<\s*/\s*script\s*>", "[SCRIPT_BLOCKED]", re.IGNORECASE | re.DOTALL),
        (r"```.*?ignore.*```", "[CODE_INJECTION_BLOCKED]", re.IGNORECASE | re.DOTALL),
        (r"##\s*instructions\s*##", "[INSTRUCTION_BLOCK_HEADER]", re.IGNORECASE),
    ]

    for pattern, replacement, flags in injection_patterns:
        text = re.sub(pattern, replacement, text, flags=flags)

    return text.strip()


def wrap_for_llm(tag_or_text: str, content: str | None = None) -> str:
    """Enclose LLM-bound knowledge inside explicit XML boundaries with prompt sanitization.

    Supports both signatures:
    - wrap_for_llm("video_transcript", raw_content) -> <video_transcript>\n[sanitized]\n</video_transcript>
    - wrap_for_llm(raw_content) -> <DATA_CONTENT>\n[sanitized]\n</DATA_CONTENT>

    Args:
        tag_or_text: XML boundary tag name or content string.
        content: Optional content when first argument is tag name.

    Returns:
        XML-wrapped sanitized string.
    """
    if content is None:
        tag = "DATA_CONTENT"
        text = tag_or_text
    else:
        tag = tag_or_text
        text = content

    sanitized = sanitize_for_prompt(text or "")
    return f"<{tag}>\n{sanitized}\n</{tag}>"


# ----------------------------------------------------------------------
# Sensitive data redaction
# ----------------------------------------------------------------------


def redact_sensitive_data(text: str, patterns: list[str] | None = None) -> str:
    """Redact sensitive data patterns (emails, credit cards, phones, SSNs, IPs) from text.

    Args:
        text: Text to redact.
        patterns: Custom regex patterns to redact.

    Returns:
        Text with sensitive patterns replaced by redaction markers.
    """
    if not text:
        return ""

    default_patterns = [
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL_REDACTED]"),
        (r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}[-.\s]?\d{1,9}\b", "[PHONE_REDACTED]"),
        (r"\b(?:\d{4}[-\s]?){3}\d{4}\b", "[CARD_REDACTED]"),
        (r"\b[A-Z]{2,}[0-9]{6,}[A-Z0-9]?\b", "[ID_REDACTED]"),
        (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[IP_REDACTED]"),
        (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN_REDACTED]"),
    ]

    all_patterns = default_patterns + [(p, "[REDACTED]") for p in (patterns or [])]

    result = text
    for pattern, replacement in all_patterns:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    return result
