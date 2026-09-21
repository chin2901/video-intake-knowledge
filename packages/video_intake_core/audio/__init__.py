"""
Audio extraction and processing module.

Extracts audio from video files (local or via yt-dlp) using ffmpeg.
Supports WAV, MP3, M4A, OPUS, and FLAC formats.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Internal implementation functions
# ----------------------------------------------------------------------

def _extract_audio_impl(
    source: str,
    output_path: Optional[str] = None,
    output_format: str = "wav",
    audio_stream_index: int = 0,
) -> dict[str, Any]:
    """Extract audio from a video file or URL (internal implementation).

    Downloads/opens the source, extracts the audio track using ffmpeg,
    and saves it in the specified format.

    Args:
        source: Path to local video file or URL (YouTube, Facebook, etc.).
        output_path: Optional output path. If None, a temp file is used.
        output_format: Audio format: wav, mp3, m4a, opus, flac.
        audio_stream_index: Index of the audio stream to extract.

    Returns:
        dict with keys: path, format, codec, sample_rate, channels,
        duration, size_bytes, source, sha256.
    """
    logger.info(f"Extracting audio from: {source}")

    is_url = source.startswith(("http://", "https://"))
    video_path: Path

    if is_url:
        video_path = _download_to_temp(source)
    else:
        video_path = Path(source)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {source}")

    if output_path is None:
        output_path = _get_temp_path(f"vitk_audio_{output_format}")
    output_path = Path(output_path)

    codec = _codec_for_format(output_format)
    cmd = _build_ffmpeg_cmd(
        video_path, output_path, codec, output_format, audio_stream_index
    )

    _run_ffmpeg(cmd, "audio extraction")

    if not output_path.exists():
        raise RuntimeError(f"Output file not created: {output_path}")

    info = _get_audio_info(output_path)
    file_hash = _compute_hash(str(output_path))

    return {
        "path": str(output_path.resolve()),
        "format": output_format,
        "codec": codec,
        "sample_rate": info["sample_rate"],
        "channels": info["channels"],
        "duration": info["duration"],
        "size_bytes": info["size_bytes"],
        "source": source,
        "sha256": file_hash,
    }


def _download_to_temp(url: str) -> Path:
    """Download a video URL to a temporary file using yt-dlp."""
    import yt_dlp

    tmp = Path(tempfile.mktemp(suffix=".mp4"))
    ydl_opts = {
        "format": "bestvideo+bestaudio/best",
        "outtmpl": str(tmp),
        "merge_output_format": "mkv",
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    if not tmp.exists():
        raise RuntimeError(f"Failed to download: {url}")
    return tmp


def _codec_for_format(fmt: str) -> str:
    return {
        "wav": "pcm_s16le",
        "mp3": "libmp3lame",
        "m4a": "aac",
        "opus": "libopus",
        "flac": "flac",
    }.get(fmt, "pcm_s16le")


def _build_ffmpeg_cmd(
    video_path: Path,
    output_path: Path,
    codec: str,
    fmt: str,
    audio_stream_index: int,
) -> list[str]:
    audio_map = f"0:a:{audio_stream_index}" if audio_stream_index > 0 else "0:a"
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-map", audio_map,
        "-acodec", codec,
        "-ar", "44100",
        "-ac", "2",
        "-f", fmt,
        str(output_path),
    ]

    if fmt == "mp3":
        cmd.extend(["-b:a", "192k"])
    elif fmt == "m4a":
        cmd.extend(["-b:a", "128k"])
    elif fmt == "opus":
        cmd.extend(["-b:a", "96k"])

    return cmd


def _run_ffmpeg(cmd: list[str], operation: str) -> None:
    """Run ffmpeg with proper path resolution."""
    ffmpeg_path = shutil.which("ffmpeg") or "/usr/bin/ffmpeg"
    if ffmpeg_path:
        cmd[0] = ffmpeg_path

    logger.debug(f"Running: {' '.join(cmd)}")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=600,
    )

    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg {operation} failed: {result.stderr[:500]}")


def _get_audio_info(path: Path) -> dict[str, Any]:
    """Get audio stream info using ffprobe."""
    cmd: list[str] = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "a:0",
        "-show_entries",
        "stream=codec_name,sample_rate,channels,duration,bit_rate",
        "-of", "json",
        str(path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode == 0:
        import json as _json

        try:
            data = _json.loads(result.stdout)
            streams = data.get("streams", [{}])
            if streams:
                s = streams[0]
                return {
                    "codec": str(s.get("codec_name", "unknown")),
                    "sample_rate": int(s.get("sample_rate", 44100)),
                    "channels": int(s.get("channels", 2)),
                    "duration": float(s.get("duration", 0.0)),
                    "bitrate": int(s.get("bit_rate", 0)),
                    "size_bytes": path.stat().st_size,
                }
        except (_json.JSONDecodeError, ValueError, KeyError):
            pass

    return {
        "codec": "unknown",
        "sample_rate": 44100,
        "channels": 2,
        "duration": 0.0,
        "bitrate": 0,
        "size_bytes": path.stat().st_size,
    }


def _compute_hash(file_path: str) -> str:
    """Compute SHA-256 hash of a file."""
    import hashlib

    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _get_temp_path(prefix: str = "vitk_") -> str:
    """Return a temporary file path."""
    return str(Path(tempfile.mktemp(suffix=".wav", prefix=prefix)))


# ----------------------------------------------------------------------
# Contract API wrapper functions
# ----------------------------------------------------------------------


def extract_audio(video_path: str | Path, output_dir: str | Path) -> dict[str, Any]:
    """Extract audio from a video file (contract API).

    Args:
        video_path: Path to local video file.
        output_dir: Directory for output audio file.

    Returns:
        Dict with extraction results.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{Path(video_path).stem}.wav"
    return _extract_audio_impl(
        source=str(video_path),
        output_path=str(output_path),
        output_format="wav",
    )


def extract_audio_from_url(url: str, output_dir: str | Path) -> dict[str, Any]:
    """Extract audio from a video URL (contract API).

    Args:
        url: Video URL to extract audio from.
        output_dir: Directory for output audio file.

    Returns:
        Dict with extraction results.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    # Use a hash of URL for filename to avoid issues
    import hashlib
    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    output_path = output_dir / f"audio_{url_hash}.wav"
    return _extract_audio_impl(
        source=url,
        output_path=str(output_path),
        output_format="wav",
    )


def get_audio_info(audio_path: str | Path) -> dict[str, Any]:
    """Get audio stream info (contract API).

    Args:
        audio_path: Path to audio file.

    Returns:
        Dict with audio info.
    """
    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    return _get_audio_info(path)


# ----------------------------------------------------------------------
# Normalization (kept as internal)
# ----------------------------------------------------------------------


def normalize_audio(
    input_path: str,
    output_path: Optional[str] = None,
    target_lufs: float = -14.0,
    output_format: str = "wav",
) -> dict[str, Any]:
    """Normalize audio loudness using ffmpeg loudnorm filter.

    Args:
        input_path: Path to input audio file.
        output_path: Optional output path.
        target_lufs: Target loudness in LUFS (default -14 LUFS).
        output_format: Output format.

    Returns:
        dict with normalization info.
    """
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {input_path}")

    out = output_path if output_path else _get_temp_path(f"vitk_norm_{output_format}")
    out_path = Path(out)

    codec = "pcm_s16le" if output_format == "wav" else "libmp3lame"
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(path),
        "-af", f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11",
        "-acodec", codec,
        "-ar", "44100",
        "-ac", "2",
        str(out_path),
    ]

    _run_ffmpeg(cmd, "audio normalization")

    return {
        "input_path": str(path),
        "output_path": str(out_path),
        "target_lufs": target_lufs,
        "output_format": output_format,
        "size_bytes": out_path.stat().st_size if out_path.exists() else 0,
    }


# ----------------------------------------------------------------------
# Splitting (kept as internal)
# ----------------------------------------------------------------------


def split_audio(
    audio_path: str,
    segment_duration: int = 300,
    output_dir: Optional[str] = None,
    prefix: str = "segment",
) -> list[dict[str, Any]]:
    """Split a long audio file into segments.

    Args:
        audio_path: Path to input audio file.
        segment_duration: Duration of each segment in seconds.
        output_dir: Directory for output segments.
        prefix: Prefix for segment filenames.

    Returns:
        list of dicts with path, start_time, end_time, index, duration.
    """
    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    out_dir = Path(output_dir) if output_dir else Path(tempfile.mkdtemp(prefix="vitk_segments_"))
    out_dir.mkdir(parents=True, exist_ok=True)

    info = _get_audio_info(path)
    duration = info["duration"]

    if duration <= segment_duration:
        ext = path.suffix or ".wav"
        dest = out_dir / f"{prefix}_00{ext}"
        shutil.copy2(path, dest)
        return [
            {
                "path": str(dest),
                "start_time": 0,
                "end_time": duration,
                "index": 0,
                "duration": duration,
            }
        ]

    num_segments = int(duration / segment_duration) + 1
    segments: list[dict[str, Any]] = []
    ext = path.suffix or ".wav"

    for i in range(num_segments):
        start = i * segment_duration
        end = min(start + segment_duration, duration)
        if start >= duration:
            break

        segment_path = out_dir / f"{prefix}_{i:03d}{ext}"

        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(path),
            "-ss", str(start),
            "-t", str(end - start),
            "-acodec", "copy",
            "-map", "0:a",
            str(segment_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0 and segment_path.exists():
            segments.append(
                {
                    "path": str(segment_path),
                    "start_time": start,
                    "end_time": end,
                    "index": i,
                    "duration": end - start,
                }
            )
        else:
            logger.warning(f"Failed to extract segment {i}")

    return segments


# ----------------------------------------------------------------------
# Direct audio download (kept as internal)
# ----------------------------------------------------------------------


def download_audio_only(
    url: str,
    output_path: Optional[str] = None,
    audio_quality: str = "best",
) -> dict[str, Any]:
    """Download audio only from a URL (using yt-dlp).

    Args:
        url: URL of the video.
        output_path: Optional output path.
        audio_quality: Audio quality preference.

    Returns:
        dict with path, source, format, size_bytes, duration, title, uploader.
    """
    import yt_dlp

    out = output_path if output_path else _get_temp_path("vitk_audio_m4a")
    out_path = Path(out)

    ydl_opts: dict[str, Any] = {
        "format": "bestaudio/best",
        "outtmpl": str(out_path),
        "quiet": True,
        "no_warnings": True,
        "extractaudio": True,
        "audioformat": "m4a",
        "audioquality": audio_quality,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    if not out_path.exists():
        raise RuntimeError(f"Audio download failed for {url}")

    return {
        "path": str(out_path.resolve()),
        "source": url,
        "format": "m4a",
        "size_bytes": out_path.stat().st_size,
        "duration": info.get("duration", 0),
        "title": info.get("title", ""),
        "uploader": info.get("uploader", ""),
    }


# ----------------------------------------------------------------------
# Additional Contract API classes (for test compatibility)
# ----------------------------------------------------------------------


from dataclasses import dataclass, field
from typing import Any


@dataclass
class AudioResult:
    """Audio extraction result (contract API)."""
    path: str = ""
    format: str = ""
    codec: str = ""
    sample_rate: int = 0
    channels: int = 0
    duration: float = 0.0
    size_bytes: int = 0
    source: str = ""
    sha256: str = ""
    error: str | None = None


# ----------------------------------------------------------------------
# Contract API wrapper functions
# ----------------------------------------------------------------------


def extract_audio_from_file(
    video_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Extract audio from a local video file (contract API).

    Alias for extract_audio.

    Args:
        video_path: Path to local video file.
        output_dir: Directory for output audio file.

    Returns:
        Dict with extraction results.
    """
    return extract_audio(video_path, output_dir)