"""
Text processing utilities.

Provides slugification, duration parsing, and human-readable size formatting.
"""

from __future__ import annotations

import re
from typing import Any


def slugify(text: str) -> str:
    """
    Convert text to a URL-safe slug.

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


def parse_duration(value: str | int | float) -> float:
    """
    Parse a duration value into seconds.

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
    unit_match = re.match(
        r"^(\d+(?:\.\d+)?)\s*(s|sec|second|seconds|m|min|minute|minutes|h|hr|hour|hours)$",
        value,
        re.IGNORECASE,
    )
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


def sizeof_fmt(num_bytes: int | float, precision: int = 2) -> str:
    """
    Format a byte count as a human-readable string.

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
