"""
Visual analysis module.

Detects scene changes, extracts keyframes, analyzes video frames
for visual content understanding.

Supports:
- PySceneDetect for scene detection
- ffmpeg-based scene detection (fallback)
- Keyframe extraction at scene boundaries or evenly spaced
- Frame analysis for visual elements
"""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Internal implementation functions
# ----------------------------------------------------------------------

def _detect_scenes_impl(
    video_path: str | Path,
    method: str = "auto",
    threshold: float = 30.0,
    min_scene_len: float = 2.0,
) -> list[dict[str, Any]]:
    """Detect scene changes in a video (internal implementation).

    Args:
        video_path: Path to video file.
        method: 'scenedetect' (PySceneDetect), 'ffmpeg' (ffmpeg select filter), 'auto'.
        threshold: Threshold for scene detection (0-100, higher = more sensitive).
        min_scene_len: Minimum scene length in seconds.

    Returns:
        List of scene dicts with:
            - start_time: Start timestamp in HH:MM:SS.mmm
            - end_time: End timestamp
            - start_seconds: Start in seconds float
            - end_seconds: End in seconds float
            - duration: Duration in seconds
            - frame_path: Optional path to saved frame at scene start
            - confidence: Detection confidence (when available)
            - method: Detection method used
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    scenes: list[dict[str, Any]] = []

    if method == "auto":
        # Try scenedetect first, fall back to ffmpeg
        try:
            scenes = _detect_with_scenedetect(video_path, threshold, min_scene_len)
            if scenes:
                return scenes
        except Exception as e:
            logger.debug(f"PySceneDetect failed: {e}")
            method = "ffmpeg"

    if method == "ffmpeg" or method == "auto":
        scenes = _detect_with_ffmpeg(video_path, threshold, min_scene_len)

    return scenes


def _detect_with_scenedetect(
    video_path: Path,
    threshold: float,
    min_scene_len: float,
) -> list[dict[str, Any]]:
    """Use PySceneDetect CLI for scene detection."""
    scenes: list[dict[str, Any]] = []

    try:
        import scenedetect  # type: ignore
    except ImportError:
        logger.debug("PySceneDetect not installed, falling back to ffmpeg")
        return scenes

    # Use scenedetect CLI via subprocess
    cmd = [
        "scenedetect",
        "-i", str(video_path),
        "detect-scenes",
        f"threshold={threshold}",
        f"min-scene-len={min_scene_len}",
        "-o", str(tempfile.mkdtemp(prefix="vitk_scenes_")),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        logger.debug(f"scenedetect failed: {result.stderr}")
        return scenes

    # Parse CSV output
    content = result.stdout + result.stderr
    lines = content.split("\n")
    for line in lines:
        if "scene," in line and "," in line:
            parts = line.split(",")
            if len(parts) >= 3:
                try:
                    start_seconds = float(parts[1])
                    scenes.append({
                        "start_time": _seconds_to_time(start_seconds),
                        "start_seconds": start_seconds,
                        "end_seconds": start_seconds + 0.1,  # Minimal scene
                        "duration": 0.1,
                        "confidence": None,
                        "method": "scenedetect",
                    })
                except (ValueError, IndexError):
                    continue

    return scenes


def _detect_with_ffmpeg(
    video_path: Path,
    threshold: float,
    min_scene_len: float,
) -> list[dict[str, Any]]:
    """Use ffmpeg select filter for scene detection.

    Uses the 'select' filter with 'gt(scene, threshold)' to detect
    scene changes.
    """
    scenes: list[dict[str, Any]] = []
    tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
    tmp_path = Path(tmp.name)
    tmp.close()

    try:
        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-vf",
            f"select='gt(scene\\\\,{threshold})',metadata=print:file={tmp_path},showinfo",
            "-vsync", "vfr",
            "-f", "null",
            "-",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        if result.returncode not in (0, 255):  # 255 = null muxer success
            logger.debug(f"ffmpeg scene detection failed: {result.stderr[:500]}")
            return scenes

        # Parse the metadata output
        content = tmp_path.read_text(errors="replace")
        frame_num = 0

        for line in content.split("\n"):
            if "pts_time:" in line:
                try:
                    parts = line.split("pts_time:")
                    if len(parts) >= 2:
                        pts = float(parts[1].split(",")[0].strip())
                        if pts > 0:
                            scenes.append({
                                "start_time": _seconds_to_time(pts),
                                "start_seconds": pts,
                                "end_seconds": pts,
                                "duration": 0,
                                "frame": frame_num,
                                "confidence": None,
                                "method": "ffmpeg",
                            })
                            frame_num += 1
                except (ValueError, IndexError):
                    continue

    finally:
        tmp_path.unlink(missing_ok=True)

    return scenes


def _extract_keyframes_impl(
    video_path: str | Path,
    scene_changes: Optional[list[dict[str, Any]]] = None,
    max_frames: int = 20,
    output_dir: Optional[str | Path] = None,
    image_format: str = "png",
    scene_frame_offset: float = 0.1,
) -> list[dict[str, Any]]:
    """Extract keyframes from a video (internal implementation).

    Extracts frames at scene changes, evenly spaced intervals,
    or both.

    Args:
        video_path: Path to video file.
        scene_changes: Optional list of scene change dicts from detect_scenes().
        max_frames: Maximum number of frames to extract.
        output_dir: Directory for output frames. Auto-created if needed.
        image_format: Image format: png, jpg, jpeg, bmp.
        scene_frame_offset: Offset from scene start in seconds.

    Returns:
        List of frame dicts with:
            - timestamp: Time of frame in seconds.
            - timestamp_str: Time as HH:MM:SS.mmm.
            - frame_path: Path to saved image.
            - width: Frame width.
            - height: Frame height.
            - index: Frame index.
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="vitk_frames_")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    frames: list[dict[str, Any]] = []
    frame_idx = 0

    # Get video duration
    duration = _get_video_duration(video_path)
    if duration is None:
        duration = 60.0  # Fallback

    # Calculate frame positions
    if scene_changes:
        # Extract at scene changes plus evenly spaced
        scene_times = sorted(set(
            sc.get("start_seconds", 0) + scene_frame_offset
            for sc in scene_changes
            if sc.get("start_seconds", 0) + scene_frame_offset < duration
        ))

        # Add evenly spaced frames
        if len(scene_times) < max_frames:
            num_even = max_frames - len(scene_times)
            for i in range(1, num_even + 1):
                t = (duration * i) / (num_even + 1)
                scene_times.append(t)

        frame_times = sorted(scene_times)[:max_frames]
    else:
        # Just evenly spaced
        num_frames = min(max_frames, 20)
        frame_times = [(duration * i) / (num_frames + 1) for i in range(1, num_frames + 1)]

    # Extract each frame
    for t in frame_times:
        if t >= duration:
            continue

        frame_path = output_dir / f"frame_{frame_idx:04d}.{image_format}"
        _extract_single_frame(video_path, frame_path, t, image_format)

        if frame_path.exists():
            size = _get_image_size(frame_path)
            frames.append({
                "timestamp": t,
                "timestamp_str": _seconds_to_time(t),
                "frame_path": str(frame_path),
                "width": size.get("width", 0),
                "height": size.get("height", 0),
                "index": frame_idx,
            })
            frame_idx += 1

    return frames


def _extract_single_frame(
    video_path: Path,
    output_path: Path,
    timestamp: float,
    image_format: str,
) -> bool:
    """Extract a single frame at given timestamp."""
    cmd = [
        "ffmpeg",
        "-y",
        "-ss", str(timestamp),
        "-i", str(video_path),
        "-vframes", "1",
        "-f", image_format,
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

    return result.returncode == 0 and output_path.exists()


def _get_video_duration(video_path: Path) -> Optional[float]:
    """Get video duration using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        str(video_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode == 0:
        try:
            return float(result.stdout.strip())
        except ValueError:
            return None
    return None


def _get_image_size(path: Path) -> dict[str, int]:
    """Get image dimensions."""
    import struct

    try:
        data = path.read_bytes()[:32]
        if data[:2] == b"\xff\xd8":  # JPEG
            # Parse JPEG dimensions
            if len(data) >= 18:
                w = int.from_bytes(data[16:18], "big")
                h = int.from_bytes(data[18:20], "big")
                return {"width": w, "height": h}
        elif data[:8] == b"\x89PNG\r\n\x1a\n":  # PNG
            if len(data) >= 24:
                w = int.from_bytes(data[16:20], "big")
                h = int.from_bytes(data[20:24], "big")
                return {"width": w, "height": h}
        elif data[:4] == b"RIFF":  # WebP
            if len(data) >= 28:
                w = int.from_bytes(data[20:22], "little")
                h = int.from_bytes(data[22:24], "little")
                return {"width": w, "height": h}
        elif data[:2] in (b"BM",):  # BMP
            if len(data) >= 24:
                w = int.from_bytes(data[18:22], "little")
                h = int.from_bytes(data[22:26], "little")
                return {"width": w, "height": h}
    except Exception:
        pass

    # Fallback to ffprobe
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    if result.returncode == 0:
        parts = result.stdout.strip().split(",")
        try:
            return {
                "width": int(parts[0]),
                "height": int(parts[1]) if len(parts) > 1 else 0,
            }
        except (ValueError, IndexError):
            pass

    return {"width": 0, "height": 0}


def _seconds_to_time(seconds: float) -> str:
    """Convert seconds float to HH:MM:SS.mmm string."""
    total_frames = int(seconds * 1000)
    ms = total_frames % 1000
    total_secs = total_frames // 1000
    hours = total_secs // 3600
    minutes = (total_secs % 3600) // 60
    secs = total_secs % 60

    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"


def _time_to_seconds(time_str: str) -> float:
    """Convert HH:MM:SS.mmm to seconds."""
    parts = time_str.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    return 0.0


# ----------------------------------------------------------------------
# Contract API wrapper functions
# ----------------------------------------------------------------------


def detect_scenes(video_path: str | Path) -> list[dict[str, Any]]:
    """Detect scene changes in a video (contract API).

    Args:
        video_path: Path to video file.

    Returns:
        List of scene dicts.
    """
    return _detect_scenes_impl(video_path, method="auto", threshold=30.0, min_scene_len=2.0)


def extract_keyframes(
    video_path: str | Path,
    scenes: list[dict[str, Any]],
    output_dir: str | Path,
) -> list[dict[str, Any]]:
    """Extract keyframes from a video (contract API).

    Args:
        video_path: Path to video file.
        scenes: List of scene dicts from detect_scenes().
        output_dir: Directory for output frames.

    Returns:
        List of frame dicts.
    """
    return _extract_keyframes_impl(
        video_path,
        scene_changes=scenes,
        max_frames=20,
        output_dir=output_dir,
    )


def analyze_keyframe(frame_path: str | Path) -> dict[str, Any]:
    """Analyze a keyframe for visual elements (contract API).

    Args:
        frame_path: Path to frame image.

    Returns:
        Dict with analysis results.
    """
    # Placeholder for future implementation
    return {
        "frame_path": str(frame_path),
        "elements": [],
        "description": "",
        "confidence": 0.0,
    }