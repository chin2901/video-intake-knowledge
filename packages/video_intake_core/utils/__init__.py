"""
Utility functions for video_intake_knowledge.

Safe, reusable helpers for URL validation, path sanitization, hashing,
file operations, config loading, and format parsing.

This module re-exports from submodules for backward compatibility.
"""

from __future__ import annotations

import hashlib
import re
import urllib.parse
from ipaddress import IPv4Address, IPv4Network
from pathlib import Path
from typing import Any

import yaml

# Re-export from validation submodule
from .validation import (
    _is_blocked_ip,
    is_safe_url,
    sanitize_for_prompt,
    redact_sensitive_data,
    validate_url,
    validate_video_url,
    ValidationResult,
)

# Re-export from fs submodule
from .fs import (
    VIDEO_EXTENSIONS,
    compute_sha256,
    ensure_dir,
    is_video_file_ext,
    sanitize_filename,
    sanitize_path,
)

# Re-export from text submodule
from .text import (
    parse_duration,
    slugify,
    sizeof_fmt,
    generate_id,
    sanitize_string,
    now_utc,
    detect_language_code,
)


# ----------------------------------------------------------------------
# YAML and config (kept here directly since it's small)
# ----------------------------------------------------------------------


def load_yaml(path: str | Path) -> dict[str, Any]:
    """
    Safely load a YAML file.

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
    """
    Deep merge two dictionaries.

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
# Video MIME type detection via magic bytes (kept here directly)
# ----------------------------------------------------------------------

VIDEO_MAGIC_BYTES = {
    # MP4/M4V/MOV - ftyp box at offset 4
    b"ftypmp4": "video/mp4",
    b"ftypM4A": "audio/mp4",
    b"ftypmov": "video/quicktime",
    b"ftypqt": "video/quicktime",
    b"ftypisom": "video/mp4",
    b"ftypavc1": "video/mp4",
    # WebM/Matroska - EBML header
    b"\x1a\x45\xdf\xa3": "video/webm",
    # AVI - RIFF header
    b"RIFF": "video/x-msvideo",
    # MPEG-PS
    b"\x00\x00\x01\xba": "video/mpeg",
    b"\x00\x00\x01\xb3": "video/mpeg",
    # FLV
    b"FLV": "video/x-flv",
    # WMV/ASF
    b"\x30\x26\xb2\x75\x8e\x66\xcf\x11": "video/x-ms-wmv",
    # MKV (Matroska) - same EBML as WebM but we check extension
}


def detect_video_mime(path: str | Path) -> str:
    """
    Detect video MIME type from file magic bytes.

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
            header = f.read(32)
    except OSError:
        return "unknown"

    if len(header) < 4:
        return "unknown"

    # Check for MP4/MOV/M4V (ftyp at offset 4)
    if header[4:8] in (b"ftyp", b"moov", b"mdat", b"free", b"skip", b"wide"):
        ftyp_brand = header[8:16]
        for magic, mime in VIDEO_MAGIC_BYTES.items():
            if header[8:].startswith(magic):
                return mime
        # Default MP4 detection
        if header[4:8] == b"ftyp":
            return "video/mp4"

    # Check other magic bytes at start of file
    for magic, mime in VIDEO_MAGIC_BYTES.items():
        if header.startswith(magic):
            # Special handling for RIFF (could be AVI or WAV)
            if magic == b"RIFF":
                # Check if it's AVI by looking for "AVI " at offset 8
                if len(header) >= 12 and header[8:12] == b"AVI ":
                    return "video/x-msvideo"
                # Could be WAV
                if len(header) >= 12 and header[8:12] == b"WAVE":
                    return "audio/wav"
                return "video/x-msvideo"  # Default to AVI
            # Special handling for EBML (WebM vs MKV)
            if magic == b"\x1a\x45\xdf\xa3":
                # Check extension to differentiate WebM vs MKV
                if path.suffix.lower() == ".webm":
                    return "video/webm"
                elif path.suffix.lower() == ".mkv":
                    return "video/x-matroska"
                return "video/webm"  # Default
            return mime

    # Check for PNG
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"

    # Check for JPEG
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"

    # Check for GIF
    if header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
        return "image/gif"

    # Check for WebP
    if header.startswith(b"RIFF") and len(header) >= 12 and header[8:12] == b"WEBP":
        return "image/webp"

    # Fallback: check by file extension for common formats
    ext = path.suffix.lower()
    ext_map = {
        ".avi": "video/x-msvideo",
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
        ".mkv": "video/x-matroska",
        ".webm": "video/webm",
        ".flv": "video/x-flv",
        ".wmv": "video/x-ms-wmv",
        ".mpeg": "video/mpeg",
        ".mpg": "video/mpeg",
        ".m4v": "video/mp4",
        ".3gp": "video/3gpp",
        ".3g2": "video/3gpp2",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".tiff": "image/tiff",
        ".tif": "image/tiff",
        ".svg": "image/svg+xml",
    }
    if ext in ext_map:
        return ext_map[ext]

    return "unknown"


# ----------------------------------------------------------------------
# Aliases
# ----------------------------------------------------------------------

# Alias for backward compatibility
safe_filename = sanitize_filename
load_yaml_config = load_yaml


__all__ = [
    # From validation
    "validate_url",
    "is_safe_url",
    "sanitize_for_prompt",
    "redact_sensitive_data",
    "_is_blocked_ip",
    "ValidationResult",
    # From fs
    "sanitize_filename",
    "sanitize_path",
    "is_video_file_ext",
    "compute_sha256",
    "VIDEO_EXTENSIONS",
    "ensure_dir",
    # From text
    "slugify",
    "parse_duration",
    "sizeof_fmt",
    "generate_id",
    "sanitize_string",
    "now_utc",
    "detect_language_code",
    # YAML and MIME
    "load_yaml",
    "load_yaml_config",
    "merge_dict",
    "detect_video_mime",
    # Aliases
    "safe_filename",
]
