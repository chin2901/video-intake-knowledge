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

    Removes path separators, control characters, null bytes. Keeps alphanumeric
    characters, spaces, hyphens, underscores, and dots.

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
    # Keep safe characters: alphanumeric, space, hyphen, underscore, dot
    # Also allow some unicode letters for international titles
    name = re.sub(r"[^a-zA-Z0-9áéíóúüñÁÉÍÓÚÜÑäëïöüÄËÏÖÜÀàÈèÌìÒòÙù\s\-_.]", "", name)
    # Collapse multiple dots/hyphens/underscores/spaces
    name = re.sub(r"\.{2,}", ".", name)
    name = re.sub(r"-{2,}", "-", name)
    name = re.sub(r"_{2,}", "_", name)
    name = re.sub(r"\s{2,}", " ", name)
    # Strip leading/trailing dots, hyphens, underscores, spaces
    name = name.strip(" .-_")
    # Limit length - preserve extension if possible
    if len(name) > max_length:
        # Try to preserve extension
        if "." in name and name.rfind(".") > max_length - 10:
            # Extension is near the end, keep it
            ext_start = name.rfind(".")
            name = name[:max_length - (len(name) - ext_start) - 3] + "..." + name[ext_start:]
        else:
            name = name[:max_length - 3] + "..."
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
        ValueError: If the resulting path escapes the base directory or contains null bytes.
    """
    raw_str = str(user_path)
    if "\x00" in raw_str:
        raise ValueError("Path contains null bytes")

    base = base.resolve()
    user_p = Path(user_path)

    # If user_p is absolute, check if it is within base
    if user_p.is_absolute():
        resolved_abs = user_p.resolve()
        try:
            resolved_abs.relative_to(base)
            return resolved_abs
        except ValueError:
            raise ValueError(f"Absolute path escapes base {base}: {user_path}") from None

    combined = (base / user_p).resolve()

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


def _compute_sha256(file_path: str | Path, chunk_size: int = 65536) -> str:
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
        for chunk in iter(lambda: f.read(chunk_size), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_sha256(file_path: str | Path) -> str:
    """Compute SHA-256 hash of a file (contract API).

    Args:
        file_path: Path to the file.

    Returns:
        Hexadecimal SHA-256 digest string.

    Raises:
        FileNotFoundError: If the file does not exist.
        IOError: If the file cannot be read.
    """
    return _compute_sha256(file_path)


def ensure_dir(path: str | Path) -> Path:
    """Ensure a directory exists, creating it if necessary (contract API).

    Args:
        path: Path to the directory.

    Returns:
        The created/verified directory path.
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path
