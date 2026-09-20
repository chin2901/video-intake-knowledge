"""
Video inspection module.

Uses ffprobe to inspect local video files and yt-dlp to inspect remote
URLs without downloading.

Provides metadata: duration, resolution, fps, codecs, bitrate, streams,
chapters, format, etc.
"""

from __future__ import annotations

import json as _json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Optional

import yt_dlp

logger = logging.getLogger(__name__)


def inspect_video_file(path: str | Path) -> dict[str, Any]:
    """Inspect a local video file using ffprobe.

    Args:
        path: Path to the video file.

    Returns:
        dict with full video metadata:
            - path: Absolute path to file.
            - filename: File name.
            - directory: Directory.
            - size_bytes: File size.
            - mtime: Modification time.
            - format: Container format (mp4, mkv, etc.).
            - duration: Duration in seconds.
            - bitrate: Overall bitrate.
            - video_count: Number of video streams.
            - audio_count: Number of audio streams.
            - subtitle_count: Number of subtitle streams.
            - chapters: List of chapters if present.
            - streams: List of all streams.
            - video: Primary video stream info (resolution, fps, codec, bitrate).
            - audio: Primary audio stream info (codec, sample_rate, channels, bitrate).
            - has_audio: Whether the file has audio.
            - has_video: Whether the file has video.
            - frame_count: Estimated frame count.
            - creation_time: Creation time from metadata if available.
    """
    path = Path(path)
    if not path.exists():
        return {
            "path": str(path),
            "error": f"File not found: {path}",
            "exists": False,
        }

    size = path.stat().st_size
    mtime = path.stat().st_mtime
    ext = path.suffix.lower().lstrip(".")

    # Run ffprobe
    cmd: list[str] = [
        "ffprobe",
        "-v", "error",
        "-show_format",
        "-show_streams",
        "-show_chapters",
        "-of", "json",
        str(path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        return {
            "path": str(path),
            "error": f"ffprobe failed: {result.stderr[:500]}",
            "exists": True,
            "size_bytes": size,
        }

    try:
        data = _json.loads(result.stdout)
    except _json.JSONDecodeError as e:
        return {
            "path": str(path),
            "error": f"Invalid ffprobe output: {e}",
            "exists": True,
            "size_bytes": size,
        }

    fmt = data.get("format", {})
    streams = data.get("streams", [])
    chapters = data.get("chapters", [])

    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
    subtitle_streams = [s for s in streams if s.get("codec_type") == "subtitle"]

    primary_video = video_streams[0] if video_streams else {}
    primary_audio = audio_streams[0] if audio_streams else {}

    # Calculate fps from video stream
    fps = _extract_fps(primary_video)

    # Estimate frame count
    duration = float(fmt.get("duration", 0))
    frame_count = int(duration * fps) if fps > 0 and duration > 0 else 0

    result_dict: dict[str, Any] = {
        "path": str(path.resolve()),
        "filename": path.name,
        "directory": str(path.parent),
        "size_bytes": size,
        "mtime": mtime,
        "extension": ext,
        "format": fmt.get("format_name", ext),
        "duration": float(fmt.get("duration", 0)),
        "bitrate": int(fmt.get("bit_rate", 0)),
        "video_count": len(video_streams),
        "audio_count": len(audio_streams),
        "subtitle_count": len(subtitle_streams),
        "chapters": [
            {
                "index": ch.get("index", 0),
                "time_base": ch.get("time_base", ""),
                "start": float(ch.get("start", 0)),
                "end": float(ch.get("end", 0)),
                "title": ch.get("tags", {}).get("title", ""),
            }
            for ch in chapters
        ],
        "streams": streams,
        "video": {
            "codec": primary_video.get("codec_name", ""),
            "codec_long": primary_video.get("codec_long_name", ""),
            "width": primary_video.get("width", 0),
            "height": primary_video.get("height", 0),
            "resolution": f"{primary_video.get('width', 0)}x{primary_video.get('height', 0)}",
            "fps": round(fps, 3),
            "frame_rate": primary_video.get("r_frame_rate", ""),
            "avg_fps": primary_video.get("avg_frame_rate", ""),
            "bitrate": int(primary_video.get("bit_rate", 0)),
            "pixel_format": primary_video.get("pix_fmt", ""),
            "profile": primary_video.get("profile", ""),
            "level": primary_video.get("level", ""),
            "nb_frames": int(primary_video.get("nb_frames", 0)),
            "has_b_frames": primary_video.get("has_b_frames", 0),
        },
        "audio": {
            "codec": primary_audio.get("codec_name", ""),
            "codec_long": primary_audio.get("codec_long_name", ""),
            "sample_rate": int(primary_audio.get("sample_rate", 0)),
            "channels": int(primary_audio.get("channels", 0)),
            "channel_layout": primary_audio.get("channel_layout", ""),
            "bitrate": int(primary_audio.get("bit_rate", 0)),
            "bit_rate_mode": primary_audio.get("bit_rate_mode", ""),
            "library": primary_audio.get("codec_tag_string", ""),
        },
        "has_video": len(video_streams) > 0,
        "has_audio": len(audio_streams) > 0,
        "frame_count": frame_count,
        "creation_time": _extract_creation_time(fmt),
    }

    return result_dict


def inspect_download_url(url: str) -> dict[str, Any]:
    """Inspect a remote video URL using yt-dlp without downloading.

    Args:
        url: URL of the video (YouTube, Facebook, Instagram, TikTok).

    Returns:
        dict with metadata:
            - url: Original URL.
            - title: Video title.
            - description: Video description.
            - uploader: Channel/uploader name.
            - upload_date: Upload date (YYYYMMDD).
            - publish_date: Publish date.
            - duration: Duration in seconds.
            - duration_string: Human-readable duration.
            - thumbnail: Thumbnail URL.
            - thumbnail_default: Default thumbnail URL.
            - webpage_url: Canonical URL.
            - extractor: Name of the extractor used.
            - extractor_key: Extractor key.
            - formats: List of available formats.
            - format_count: Number of formats.
            - video_quality: Best available video quality (height in px).
            - audio_available: Whether audio-only formats exist.
            - view_count: View count if available.
            - like_count: Like count if available.
            - dislike_count: Dislike count if available.
            - average_rating: Average rating.
            - categories: Categories/tags.
            - tags: List of tags.
            - language: Detected language.
            - subtitles: Available subtitles.
            - automatic_captions: Available auto-generated captions.
            - captions: Available manual captions.
            - is_live: Whether the video is live.
            - req_headers: Required headers if any.
    """
    logger.info(f"Inspecting URL: {url}")

    ydl_opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "skip_download": True,
        "quiet": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        return {
            "url": url,
            "error": f"Failed to inspect URL: {str(e)[:500]}",
            "url_type": "unknown",
        }

    # Build formats list
    formats: list[dict[str, Any]] = []
    for fmt in info.get("formats", []):
        formats.append({
            "format_id": fmt.get("format_id", ""),
            "ext": fmt.get("ext", ""),
            "protocol": fmt.get("protocol", ""),
            "width": fmt.get("width", 0),
            "height": fmt.get("height", 0),
            "resolution": fmt.get("resolution", ""),
            "fps": fmt.get("fps", 0),
            "vcodec": fmt.get("vcodec", ""),
            "acodec": fmt.get("acodec", ""),
            "filesize": fmt.get("filesize", 0),
            "filesize_approx": fmt.get("filesize_approx", 0),
            "tbr": fmt.get("tbr", 0),
            "vbr": fmt.get("vbr", 0),
            "abr": fmt.get("abr", 0),
            "audio_channels": fmt.get("audio_channels", 0),
            "fps_float": fmt.get("fps_float", 0),
            "format": fmt.get("format", ""),
            "format_note": fmt.get("format_note", ""),
            "preference": fmt.get("preference", 0),
        })

    # Subtitle/caption info
    subtitles = {}
    automatic_captions = {}
    captions = {}

    if "subtitles" in info:
        for lang, sub_list in info["subtitles"].items():
            subtitles[lang] = [s.get("url", "") for s in sub_list]
    if "automatic_captions" in info:
        for lang, cap_list in info["automatic_captions"].items():
            automatic_captions[lang] = [c.get("url", "") for c in cap_list]
    if "captions" in info:
        for lang, cap_list in info["captions"].items():
            captions[lang] = [c.get("url", "") for c in cap_list]

    # Detect best video quality
    best_video_height = 0
    for fmt in info.get("formats", []):
        h = fmt.get("height", 0)
        if h > best_video_height:
            best_video_height = h

    audio_available = any(
        f.get("acodec", "") and f.get("vcodec", "none") == "none"
        for f in formats
    )

    # Extract upload date
    upload_date = info.get("upload_date", "")
    publish_date = info.get("publish_date", "")

    return {
        "url": url,
        "title": info.get("title", ""),
        "description": info.get("description", ""),
        "uploader": info.get("uploader", ""),
        "uploader_id": info.get("uploader_id", ""),
        "upload_date": upload_date,
        "publish_date": publish_date,
        "duration": info.get("duration", 0),
        "duration_string": info.get("duration_string", ""),
        "thumbnail": info.get("thumbnail", ""),
        "thumbnail_default": info.get("thumbnail_default", ""),
        "webpage_url": info.get("webpage_url", ""),
        "extractor": info.get("extractor", ""),
        "extractor_key": info.get("extractor_key", ""),
        "formats": formats,
        "format_count": len(formats),
        "video_quality": best_video_height,
        "audio_available": audio_available,
        "view_count": info.get("view_count", 0),
        "like_count": info.get("like_count", 0),
        "dislike_count": info.get("dislike_count", 0),
        "average_rating": info.get("average_rating", 0.0),
        "categories": info.get("categories", []),
        "tags": info.get("tags", []),
        "language": info.get("language", ""),
        "subtitles": subtitles,
        "automatic_captions": automatic_captions,
        "captions": captions,
        "is_live": bool(info.get("is_live", False)),
        "is_draft": bool(info.get("is_draft", False)),
        "availability": info.get("availability", ""),
    }


def _extract_fps(video_stream: dict[str, Any]) -> float:
    """Extract FPS from a video stream dict."""
    # Try avg_frame_rate first
    avg_fps = video_stream.get("avg_frame_rate", "")
    if avg_fps and "/" in avg_fps:
        try:
            num, den = avg_fps.split("/")
            if int(den) > 0:
                return int(num) / int(den)
        except (ValueError, ZeroDivisionError):
            pass

    # Try r_frame_rate
    r_frame = video_stream.get("r_frame_rate", "")
    if r_frame and "/" in r_frame:
        try:
            num, den = r_frame.split("/")
            if int(den) > 0:
                return int(num) / int(den)
        except (ValueError, ZeroDivisionError):
            pass

    # Try fps field
    fps_val = video_stream.get("fps", 0)
    if isinstance(fps_val, (int, float)) and fps_val > 0:
        return float(fps_val)

    return 30.0  # Default fallback


def _extract_creation_time(fmt: dict[str, Any]) -> Optional[str]:
    """Extract creation time from format metadata."""
    tags = fmt.get("tags", {})
    for key in ("creation_time", "creationdate", "datetime", "date"):
        val = tags.get(key)
        if val:
            return str(val)
    return None


# ---------------------------------------------------------------------------
# Batch inspection
# ---------------------------------------------------------------------------

def inspect_multiple(paths: list[str]) -> list[dict[str, Any]]:
    """Inspect multiple video files/URLs.

    Args:
        paths: List of file paths or URLs.

    Returns:
        List of inspection results in the same order.
    """
    results: list[dict[str, Any]] = []
    for path in paths:
        try:
            if path.startswith(("http://", "https://")):
                results.append(inspect_download_url(path))
            else:
                results.append(inspect_video_file(path))
        except Exception as e:
            results.append({
                "path": path,
                "url": path if path.startswith(("http://", "https://")) else None,
                "error": str(e),
                "exists": Path(path).exists() if not path.startswith(("http://", "https://")) else None,
            })
    return results
