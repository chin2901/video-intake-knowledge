"""
Acquisition module — detects video sources and resolves URLs.

Supports:
- YouTube (youtube.com, youtu.be, shorts)
- Facebook (facebook.com/watch, facebook.com/video, facebook.com/reel, facebook.com/share)
- Instagram (instagram.com/reel, instagram.com/p, instagram.com/tv, instagram.com/reels)
- TikTok (tiktok.com, va.tiktok.com, vm.tiktok.com)
- Local video files (mp4, mov, mkv, webm, avi, m4v, mpeg, mpg, flv, wmv)

Provides URL detection, source type identification, and URL resolution.
"""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from pathlib import Path
from typing import Optional

from ..schemas import Source, SourceType, ResolvedURL
from ..utils.validation import is_safe_url
from ..utils.fs import sanitize_filename

logger = logging.getLogger(__name__)

# URL pattern matchers
YOUTUBE_PATTERNS = [
    re.compile(r"^https?://(www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})", re.IGNORECASE),
    re.compile(r"^https?://youtu\.be/([a-zA-Z0-9_-]{11})", re.IGNORECASE),
    re.compile(r"^https?://(www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})", re.IGNORECASE),
    re.compile(r"^https?://(www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})", re.IGNORECASE),
    re.compile(r"^https?://(www\.)?youtube\.com/live/([a-zA-Z0-9_-]{11})", re.IGNORECASE),
    re.compile(r"^https?://m\.youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})", re.IGNORECASE),
]

FACEBOOK_PATTERNS = [
    re.compile(r"^https?://(www\.)?facebook\.com/watch\?v=(\d+)", re.IGNORECASE),
    re.compile(r"^https?://(www\.)?facebook\.com/video\.php\?v=(\d+)", re.IGNORECASE),
    re.compile(r"^https?://(www\.)?facebook\.com/reel/(\d+)", re.IGNORECASE),
    re.compile(r"^https?://(www\.)?facebook\.com/share/r/([a-zA-Z0-9_-]+)", re.IGNORECASE),
    re.compile(r"^https?://(www\.)?facebook\.com/([a-zA-Z0-9_.]+)/videos/(\d+)", re.IGNORECASE),
    re.compile(r"^https?://(www\.)?facebook\.com/([a-zA-Z0-9_.]+)/watch/(\d+)", re.IGNORECASE),
    re.compile(r"^https?://(www\.)?facebook\.com/?video/v/(\d+)", re.IGNORECASE),
]

INSTAGRAM_PATTERNS = [
    re.compile(r"^https?://(www\.)?instagram\.com/reel/([a-zA-Z0-9_-]+)", re.IGNORECASE),
    re.compile(r"^https?://(www\.)?instagram\.com/p/([a-zA-Z0-9_-]+)", re.IGNORECASE),
    re.compile(r"^https?://(www\.)?instagram\.com/tv/([a-zA-Z0-9_-]+)", re.IGNORECASE),
    re.compile(r"^https?://(www\.)?instagram\.com/reels/([a-zA-Z0-9_-]+)", re.IGNORECASE),
    re.compile(r"^https?://(www\.)?instagram\.com/([a-zA-Z0-9_.]+)/reel/([a-zA-Z0-9_-]+)", re.IGNORECASE),
]

TIKTOK_PATTERNS = [
    re.compile(r"^https?://(www\.)?tiktok\.com/@([^/]+)/video/(\d+)", re.IGNORECASE),
    re.compile(r"^https?://(www\.)?tiktok\.com/t/([a-zA-Z0-9_-]+)", re.IGNORECASE),
    re.compile(r"^https?://(vm|va|vt)\.tiktok\.com/([^/?]+)", re.IGNORECASE),
    re.compile(r"^https?://(www\.)?tiktok\.com/([^/]+)/video/(\d+)", re.IGNORECASE),
]


def detect_source_type(url: str) -> Optional[SourceType]:
    """Detect the type of video source from a URL.

    Args:
        url: The URL to detect the source type for.

    Returns:
        SourceType if detected, None otherwise.
    """
    for pattern in YOUTUBE_PATTERNS:
        if pattern.match(url):
            return SourceType.YOUTUBE
    for pattern in FACEBOOK_PATTERNS:
        if pattern.match(url):
            return SourceType.FACEBOOK
    for pattern in INSTAGRAM_PATTERNS:
        if pattern.match(url):
            return SourceType.INSTAGRAM
    for pattern in TIKTOK_PATTERNS:
        if pattern.match(url):
            return SourceType.TIKTOK
    return None


def detect_source(url_or_path: str) -> Optional[Source]:
    """Detect a video source from a URL or file path.

    Args:
        url_or_path: URL or local file path to detect.

    Returns:
        Source object if detected, None otherwise.
    """
    path = Path(url_or_path)
    if path.exists() and path.is_file():
        ext = path.suffix.lower().lstrip(".")
        if ext in ("mp4", "mov", "mkv", "webm", "avi", "m4v", "mpeg", "mpg", "flv", "wmv"):
            return Source(
                source_type=SourceType.LOCAL_FILE,
                url=str(path.resolve()),
                title=path.stem,
                platform="local",
                raw_url=url_or_path,
            )
        return None

    source_type = detect_source_type(url_or_path)
    if source_type is None:
        return None

    return Source(
        source_type=source_type,
        url=url_or_path,
        platform=source_type.value,
        raw_url=url_or_path,
    )


def resolve_url(url: str, follow_redirects: bool = True) -> ResolvedURL:
    """Resolve a video URL to its canonical form.

    For YouTube, Facebook, Instagram, and TikTok URLs, this attempts to
    resolve redirects and extract the canonical video identifier.

    Args:
        url: The URL to resolve.
        follow_redirects: Whether to follow HTTP redirects.

    Returns:
        ResolvedURL with the canonical URL and metadata.
    """
    source_type = detect_source_type(url)
    if source_type is None:
        raise ValueError(f"Unsupported source type for URL: {url}")

    resolved_url = url
    canonical_id = None

    if source_type == SourceType.YOUTUBE:
        for pattern in YOUTUBE_PATTERNS:
            match = pattern.match(url)
            if match:
                groups = match.groups()
                for g in groups:
                    if len(g) == 11 and g.replace("_", "").replace("-", "").isalnum():
                        canonical_id = g
                        break
                if canonical_id:
                    resolved_url = f"https://www.youtube.com/watch?v={canonical_id}"
                    break

    elif source_type == SourceType.FACEBOOK:
        for pattern in FACEBOOK_PATTERNS:
            match = pattern.match(url)
            if match:
                groups = match.groups()
                for g in groups:
                    if g.isdigit() and len(g) >= 6:
                        canonical_id = g
                        resolved_url = f"https://www.facebook.com/video.php?v={canonical_id}"
                        break
                if canonical_id:
                    break

    elif source_type == SourceType.INSTAGRAM:
        for pattern in INSTAGRAM_PATTERNS:
            match = pattern.match(url)
            if match:
                groups = match.groups()
                for g in groups:
                    if len(g) >= 8 and re.match(r"^[a-zA-Z0-9_-]+$", g):
                        canonical_id = g
                        resolved_url = f"https://www.instagram.com/p/{canonical_id}/"
                        break
                if canonical_id:
                    break

    elif source_type == SourceType.TIKTOK:
        for pattern in TIKTOK_PATTERNS:
            match = pattern.match(url)
            if match:
                groups = match.groups()
                for g in groups:
                    if g.isdigit():
                        canonical_id = g
                        resolved_url = f"https://www.tiktok.com/@username/video/{canonical_id}"
                        break
                if canonical_id:
                    break

    if canonical_id is None:
        canonical_id = hashlib.sha256(url.encode()).hexdigest()[:16]

    return ResolvedURL(
        original_url=url,
        resolved_url=resolved_url,
        canonical_id=canonical_id,
        source_type=source_type,
        redirect_chain=[url] if follow_redirects else [],
    )


def extract_video_id(url: str) -> Optional[str]:
    """Extract the canonical video ID from a URL.

    Args:
        url: The URL to extract the video ID from.

    Returns:
        The video ID if extractable, None otherwise.
    """
    try:
        resolved = resolve_url(url)
        return resolved.canonical_id
    except ValueError:
        return None


def is_video_url(text: str) -> bool:
    """Check if a string contains a processable video URL.

    Args:
        text: Text to check for video URLs.

    Returns:
        True if a video URL is detected, False otherwise.
    """
    url_pattern = re.compile(
        r"https?://"
        r"(?:www\.)?"
        r"(?:"
        r"youtube\.com/(?:watch\?v=|shorts/|embed/|live/)|"
        r"youtu\.be/|"
        r"facebook\.com/(?:watch\.php\?v=|video\.php\?v=|reel/|share/r/|/videos/|/watch/)|"
        r"instagram\.com/(?:reel/|p/|tv/|reels/)|"
        r"tiktok\.com/(?:@[^/]+/video/|t/)|"
        r"(?:vm|va|vt)\.tiktok\.com/"
        r")"
        r"[a-zA-Z0-9_\-\/?=&#]+",
        re.IGNORECASE,
    )
    return bool(url_pattern.search(text))


def extract_all_video_urls(text: str) -> list[str]:
    """Extract all video URLs from a text.

    Args:
        text: Text to extract URLs from.

    Returns:
        List of unique video URLs found.
    """
    url_pattern = re.compile(
        r"https?://"
        r"(?:www\.)?"
        r"(?:"
        r"youtube\.com/(?:watch\?v=|shorts/|embed/|live/)|"
        r"youtu\.be/|"
        r"facebook\.com/(?:watch\.php\?v=|video\.php\?v=|reel/|share/r/|/videos/|/watch/)|"
        r"instagram\.com/(?:reel/|p/|tv/|reels/)|"
        r"tiktok\.com/(?:@[^/]+/video/|t/)|"
        r"(?:vm|va|vt)\.tiktok\.com/"
        r")"
        r"[a-zA-Z0-9_\-\/?=&#]+",
        re.IGNORECASE,
    )
    matches = url_pattern.findall(text)
    urls = []
    for match in matches:
        url = match if isinstance(match, str) else match.group(0) if hasattr(match, "group") else str(match)
        if url and url not in urls:
            urls.append(url)
    return urls


def generate_safe_filename(source: Source, extension: str = "mp4") -> str:
    """Generate a safe, readable filename for a video source.

    Args:
        source: The source to generate a filename for.
        extension: The file extension (default: mp4).

    Returns:
        A safe filename combining source info and hash.
    """
    base = sanitize_filename(source.title or source.platform or "video")
    source_hash = hashlib.sha256(source.url.encode()).hexdigest()[:8]
    date_str = "unknown"
    if source.metadata and source.metadata.get("published_date"):
        date_str = source.metadata["published_date"][:10].replace("-", "")
    return f"{date_str}_{base}_{source_hash}.{extension}"


def create_source_id(source: Source) -> str:
    """Create a unique job/source ID for a video source.

    Args:
        source: The source to create an ID for.

    Returns:
        A unique identifier string.
    """
    source_hash = hashlib.sha256(source.url.encode()).hexdigest()[:12]
    return f"vitk_{source_hash}_{uuid.uuid4().hex[:8]}"


__all__ = [
    "detect_source_type",
    "detect_source",
    "resolve_url",
    "extract_video_id",
    "is_video_url",
    "extract_all_video_urls",
    "generate_safe_filename",
    "create_source_id",
    "YOUTUBE_PATTERNS",
    "FACEBOOK_PATTERNS",
    "INSTAGRAM_PATTERNS",
    "TIKTOK_PATTERNS",
]

# Alias for backwards compatibility and CLI usage
detect_video_sources = detect_source
detect_video_source_type = detect_source_type
