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
)

# Re-export from fs submodule
from .fs import (
    VIDEO_EXTENSIONS,
    compute_sha256,
    is_video_file_ext,
    sanitize_filename,
    sanitize_path,
)

# Re-export from text submodule
from .text import parse_duration, slugify, sizeof_fmt


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
            header = f.read(16)
    except OSError:
        return "unknown"

    for magic, mime in VIDEO_MAGIC_BYTES.items():
        if header.startswith(magic):
            return mime

    return "unknown"


__all__ = [
    # From validation
    "validate_url",
    "is_safe_url",
    "sanitize_for_prompt",
    "redact_sensitive_data",
    "_is_blocked_ip",
    # From fs
    "sanitize_filename",
    "sanitize_path",
    "is_video_file_ext",
    "compute_sha256",
    "VIDEO_EXTENSIONS",
    # From text
    "slugify",
    "parse_duration",
    "sizeof_fmt",
    # YAML and MIME
    "load_yaml",
    "merge_dict",
    "detect_video_mime",
]
