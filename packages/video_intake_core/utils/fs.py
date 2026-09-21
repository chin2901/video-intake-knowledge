"""
File system and path utilities.

Provides safe filename/path sanitization, file type detection,
SHA-256 hashing, and video extension handling.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path


# ----------------------------------------------------------------------
# Filename and path sanitization
# ----------------------------------------------------------------------

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")

VIDEO_EXTENSIONS = frozenset(
    {
        ".mp4", ".mov", ".mkv", ".webm", ".avi",
        ".m4v", ".mpeg", ".mpg", ".flv", ".wmv",
    }
)


def sanitize_filename(name: str, max_length: int = 200) -> str:
    """
    Sanitize a string to be safe as a filename.

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
    """
    Sanitize a user-provided path within a base directory.

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


def is_video_file_ext(path: str | Path) -> bool:
    """
    Check if a file has a recognized video extension.

    Args:
        path: Path to check.

    Returns:
        True if the file extension is a recognized video format.
    """
    return Path(path).suffix.lower() in VIDEO_EXTENSIONS


def compute_sha256(file_path: str | Path, chunk_size: int = 65536) -> str:
    """
    Compute SHA-256 hash of a file.

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
