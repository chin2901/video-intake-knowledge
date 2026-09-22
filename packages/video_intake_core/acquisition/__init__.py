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
import urllib.parse
import urllib.request
from urllib.parse import parse_qs, urlparse
import uuid
from pathlib import Path
from typing import Optional

from ..schemas import Source, SourceType, ResolvedURL
from ..utils.validation import is_safe_url
from ..utils.fs import sanitize_filename

logger = logging.getLogger(__name__)

# URL pattern matchers
YOUTUBE_PATTERNS = [
    re.compile(r"^https?://(www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)", re.IGNORECASE),
    re.compile(r"^https?://youtu\.be/([a-zA-Z0-9_-]+)", re.IGNORECASE),
    re.compile(r"^https?://(www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]+)", re.IGNORECASE),
    re.compile(r"^https?://(www\.)?youtube\.com/embed/([a-zA-Z0-9_-]+)", re.IGNORECASE),
    re.compile(r"^https?://(www\.)?youtube\.com/live/([a-zA-Z0-9_-]+)", re.IGNORECASE),
    re.compile(r"^https?://m\.youtube\.com/watch\?v=([a-zA-Z0-9_-]+)", re.IGNORECASE),
    re.compile(r"^https?://(www\.|m\.)?youtube\.com/watch\?.*[?&]v=([a-zA-Z0-9_-]+)", re.IGNORECASE),
]

FACEBOOK_PATTERNS = [
    re.compile(r"^https?://(www\.|m\.)?facebook\.com/watch/?\?.*v=(\d+)", re.IGNORECASE),
    re.compile(r"^https?://(www\.|m\.)?facebook\.com/video\.php\?.*v=(\d+)", re.IGNORECASE),
    re.compile(r"^https?://(www\.|m\.)?facebook\.com/reel/(\d+)", re.IGNORECASE),
    re.compile(r"^https?://(www\.|m\.)?facebook\.com/share/r/([a-zA-Z0-9_-]+)", re.IGNORECASE),
    re.compile(r"^https?://(www\.|m\.)?facebook\.com/share/v/([a-zA-Z0-9_-]+)", re.IGNORECASE),
    re.compile(r"^https?://(www\.|m\.)?facebook\.com/([a-zA-Z0-9_.]+)/videos/(\d+)", re.IGNORECASE),
    re.compile(r"^https?://(www\.|m\.)?facebook\.com/([a-zA-Z0-9_.]+)/watch/(\d+)", re.IGNORECASE),
    re.compile(r"^https?://(www\.|m\.)?facebook\.com/?video/v/(\d+)", re.IGNORECASE),
    re.compile(r"^https?://fb\.watch/([a-zA-Z0-9_-]+)", re.IGNORECASE),
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
    if not url:
        return None

    if url.startswith("file://"):
        return SourceType.LOCAL_FILE

    try:
        parsed = urlparse(url)
    except Exception:
        parsed = None

    if parsed and parsed.scheme in ("http", "https"):
        host = parsed.netloc.lower().split(":")[0]
        if host.startswith("www."):
            host = host[4:]
        if host.startswith("m."):
            host = host[2:]

        # YouTube check
        if host in ("youtube.com", "youtu.be"):
            if host == "youtu.be":
                return SourceType.YOUTUBE
            qs = parse_qs(parsed.query)
            if "v" in qs and qs["v"]:
                return SourceType.YOUTUBE
            if any(parsed.path.startswith(prefix) for prefix in ("/shorts/", "/embed/", "/live/", "/v/")):
                return SourceType.YOUTUBE
            if parsed.path.rstrip("/") in ("/watch", "/watch_videos"):
                return SourceType.YOUTUBE

        # Facebook check
        if host in ("facebook.com", "fb.watch", "fb.com"):
            return SourceType.FACEBOOK

        # Instagram check
        if host in ("instagram.com", "instagr.am"):
            return SourceType.INSTAGRAM

        # TikTok check
        if host in ("tiktok.com", "vm.tiktok.com", "va.tiktok.com", "vt.tiktok.com"):
            return SourceType.TIKTOK

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
    if not url_or_path:
        return None

    raw_path = url_or_path
    if raw_path.startswith("file://"):
        raw_path = raw_path[7:]

    path = Path(raw_path)
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

    if source_type == SourceType.LOCAL_FILE:
        return Source(
            source_type=SourceType.LOCAL_FILE,
            url=raw_path,
            title=Path(raw_path).stem,
            platform="local",
            raw_url=url_or_path,
        )

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

    redirect_chain = [url]
    curr_url = url

    if follow_redirects and curr_url.startswith(("http://", "https://")):
        try:
            parsed_host = urlparse(curr_url).netloc.lower()
            is_shortened = any(sh in parsed_host for sh in (
                "vm.tiktok.com", "va.tiktok.com", "vt.tiktok.com",
                "fb.watch", "youtu.be", "bit.ly", "tinyurl.com", "t.co"
            ))
            if is_shortened:
                from ..security import validate_video_url
                try:
                    validate_video_url(curr_url)
                except ValueError as ve:
                    logger.warning("SSRF blocked during redirect resolution: %s", ve)
                    return ResolvedURL(url=curr_url, canonical_id=None, source_type=source_type, normalized_url=curr_url, redirect_chain=redirect_chain)
                
                req = urllib.request.Request(
                    curr_url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                    method="HEAD",
                )
                with urllib.request.urlopen(req, timeout=4.0) as resp:
                    final_url = resp.geturl()
                    if final_url and final_url != curr_url:
                        redirect_chain.append(final_url)
                        curr_url = final_url
                        resolved_type = detect_source_type(curr_url)
                        if resolved_type:
                            source_type = resolved_type
        except Exception as e:
            logger.debug("Failed redirect resolution for %s: %s", curr_url, e)

    resolved_url = curr_url
    canonical_id = None
    parsed_target = urlparse(curr_url)
    qs = parse_qs(parsed_target.query)

    if source_type == SourceType.YOUTUBE:
        if "v" in qs and qs["v"] and qs["v"][0]:
            canonical_id = qs["v"][0]
        elif parsed_target.netloc.lower().endswith("youtu.be"):
            path_parts = [p for p in parsed_target.path.split("/") if p]
            if path_parts:
                canonical_id = path_parts[0]
        elif any(parsed_target.path.startswith(p) for p in ("/shorts/", "/embed/", "/live/", "/v/")):
            path_parts = [p for p in parsed_target.path.split("/") if p]
            if len(path_parts) >= 2:
                canonical_id = path_parts[1]

        if not canonical_id:
            for pattern in YOUTUBE_PATTERNS:
                match = pattern.match(curr_url)
                if match:
                    for g in match.groups():
                        if g and g.replace("_", "").replace("-", "").isalnum():
                            canonical_id = g
                            break
                    if canonical_id:
                        break

        if canonical_id:
            resolved_url = f"https://www.youtube.com/watch?v={canonical_id}"

    elif source_type == SourceType.FACEBOOK:
        if "v" in qs and qs["v"] and qs["v"][0]:
            canonical_id = qs["v"][0]
            resolved_url = f"https://www.facebook.com/video.php?v={canonical_id}"
        elif "fb.watch" in parsed_target.netloc.lower():
            path_parts = [p for p in parsed_target.path.split("/") if p]
            if path_parts:
                canonical_id = path_parts[0]
                resolved_url = f"https://www.facebook.com/watch/?v={canonical_id}"

        if not canonical_id:
            for pattern in FACEBOOK_PATTERNS:
                match = pattern.match(curr_url)
                if match:
                    for g in match.groups():
                        if g and g.isdigit() and len(g) >= 6:
                            canonical_id = g
                            resolved_url = f"https://www.facebook.com/video.php?v={canonical_id}"
                            break
                        if g and len(g) >= 6 and re.match(r"^[a-zA-Z0-9_-]+$", g):
                            canonical_id = g
                            resolved_url = f"https://www.facebook.com/share/v/{canonical_id}/"
                            break
                    if canonical_id:
                        break

    elif source_type == SourceType.INSTAGRAM:
        path_parts = [p for p in parsed_target.path.split("/") if p]
        for idx_p, part in enumerate(path_parts):
            if part in ("p", "reel", "tv", "reels") and idx_p + 1 < len(path_parts):
                candidate = path_parts[idx_p + 1]
                if len(candidate) >= 5 and re.match(r"^[a-zA-Z0-9_-]+$", candidate):
                    canonical_id = candidate
                    resolved_url = f"https://www.instagram.com/p/{canonical_id}/"
                    break

        if not canonical_id:
            for pattern in INSTAGRAM_PATTERNS:
                match = pattern.match(curr_url)
                if match:
                    for g in match.groups():
                        if g and len(g) >= 8 and re.match(r"^[a-zA-Z0-9_-]+$", g):
                            canonical_id = g
                            resolved_url = f"https://www.instagram.com/p/{canonical_id}/"
                            break
                    if canonical_id:
                        break

    elif source_type == SourceType.TIKTOK:
        video_match = re.search(r"/video/(\d+)", parsed_target.path)
        if video_match:
            canonical_id = video_match.group(1)
            resolved_url = f"https://www.tiktok.com/@video/video/{canonical_id}"

        if not canonical_id:
            for pattern in TIKTOK_PATTERNS:
                match = pattern.match(curr_url)
                if match:
                    for g in match.groups():
                        if g and g.isdigit():
                            canonical_id = g
                            resolved_url = f"https://www.tiktok.com/@username/video/{canonical_id}"
                            break
                    if canonical_id:
                        break

    if canonical_id is None:
        canonical_id = hashlib.sha256(curr_url.encode()).hexdigest()[:16]

    return ResolvedURL(
        original_url=url,
        resolved_url=resolved_url,
        canonical_id=canonical_id,
        source_type=source_type,
        redirect_chain=redirect_chain if follow_redirects else [],
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
        r"(?:www\.|m\.)?"
        r"(?:"
        r"youtube\.com/(?:watch\?|shorts/|embed/|live/)|"
        r"youtu\.be/|"
        r"facebook\.com/(?:watch/?\?|video\.php\?|reel/|share/r/|share/v/|/videos/|/watch/)|"
        r"fb\.watch/|"
        r"instagram\.com/(?:reel/|p/|tv/|reels/)|"
        r"tiktok\.com/(?:@[^/]+/video/|t/)|"
        r"(?:vm|va|vt)\.tiktok\.com/"
        r")"
        r"[a-zA-Z0-9_\-\/?=&#.%+]+",
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
        r"(?:www\.|m\.)?"
        r"(?:"
        r"youtube\.com/(?:watch\?|shorts/|embed/|live/)|"
        r"youtu\.be/|"
        r"facebook\.com/(?:watch/?\?|video\.php\?|reel/|share/r/|share/v/|/videos/|/watch/)|"
        r"fb\.watch/|"
        r"instagram\.com/(?:reel/|p/|tv/|reels/)|"
        r"tiktok\.com/(?:@[^/]+/video/|t/)|"
        r"(?:vm|va|vt)\.tiktok\.com/"
        r")"
        r"[a-zA-Z0-9_\-\/?=&#.%+]+",
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
    "detect_video_sources",
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
detect_video_source_type = detect_source_type


class VideoSource:
    """Lightweight source object for detect_video_sources results."""

    def __init__(
        self,
        source_type: str,
        url: str,
        resolved_path: str | None = None,
        video_id: str | None = None,
        title: str | None = None,
    ):
        self.source_type = source_type
        self.url = url
        self.resolved_path = resolved_path
        self.id = video_id
        self.title = title


def detect_video_sources(text: str) -> list[VideoSource]:
    """Detect all video sources in a text string.

    Extracts URLs and local file paths, identifies their types,
    and returns a list of VideoSource objects.

    Args:
        text: Text to search for video sources.

    Returns:
        List of VideoSource objects with source_type, url, resolved_path, id, title.
    """
    sources: list[VideoSource] = []

    # Extract all video URLs from text
    urls = extract_all_video_urls(text)
    for url in urls:
        source = detect_source(url)
        if source:
            # Extract video ID from URL
            video_id = extract_video_id(url)
            sources.append(
                VideoSource(
                    source_type=source.source_type.value,
                    url=source.url,
                    video_id=video_id,
                    title=source.title,
                )
            )

    # Also check for local file paths in text
    video_exts = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".mpeg", ".mpg", ".flv", ".wmv"}
    stripped = text.strip().strip("'\"")
    direct_path = Path(stripped)
    if direct_path.exists() and direct_path.is_file() and direct_path.suffix.lower() in video_exts:
        sources.append(
            VideoSource(
                source_type="local",
                url=f"file://{direct_path.resolve()}",
                resolved_path=str(direct_path.resolve()),
                video_id=None,
                title=direct_path.stem,
            )
        )
    else:
        # Look for path patterns (both absolute and relative)
        import re

        path_pattern = re.compile(
            r"(?:^|\s)((?:/[^\s]+|[.\w\-_/]+)\.(?:mp4|mov|mkv|webm|avi|m4v|mpeg|mpg|flv|wmv))",
            re.IGNORECASE,
        )
        for match in path_pattern.finditer(text):
            file_path = match.group(1).strip()
            path = Path(file_path)
            if path.exists() and path.is_file() and path.suffix.lower() in video_exts:
                resolved_str = str(path.resolve())
                if not any(s.resolved_path == resolved_str for s in sources):
                    sources.append(
                        VideoSource(
                            source_type="local",
                            url=f"file://{resolved_str}",
                            resolved_path=resolved_str,
                            video_id=None,
                            title=path.stem,
                        )
                    )

    return sources
