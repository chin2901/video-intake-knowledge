"""
Unit tests for Video Inspection module (F1, F2).

Verifies:
1. Lazy import of yt_dlp (<300ms SLA).
2. VideoInfo contract restoration with all required rich media attributes.
3. Native ffprobe inspection and file:// URI handling.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest
from video_intake_core.inspection import (
    VideoInfo,
    inspect_local_video,
    inspect_video,
)


@pytest.fixture
def sample_video_path() -> Path:
    p = Path(__file__).parent.parent / "fixtures" / "video" / "sample.mp4"
    assert p.exists(), f"Sample fixture missing at {p}"
    return p.resolve()


def test_lazy_yt_dlp_import():
    """Verify that importing inspection module does not eagerly import yt_dlp."""
    # Remove yt_dlp and inspection from sys.modules if present
    for mod in list(sys.modules.keys()):
        if mod == "yt_dlp" or mod.startswith("yt_dlp.") or "inspection" in mod:
            sys.modules.pop(mod, None)

    import video_intake_core.inspection  # noqa: F401

    assert "yt_dlp" not in sys.modules, "yt_dlp must be lazily imported, not loaded at module top level"


def test_local_video_inspection_sla(sample_video_path: Path):
    """Verify that local video inspection completes well within the 300ms SLA."""
    t0 = time.perf_counter()
    info = inspect_video(sample_video_path)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert info.error is None
    assert elapsed_ms < 300.0, f"Inspection took {elapsed_ms:.1f}ms, exceeding 300ms SLA"


def test_video_info_rich_metadata_contract(sample_video_path: Path):
    """Verify that VideoInfo retains and exposes all required rich stream attributes (F2)."""
    info = inspect_video(sample_video_path)

    assert isinstance(info, VideoInfo)
    assert info.title == "sample.mp4"
    assert info.duration == pytest.approx(5.0, abs=0.1)
    assert info.width == 320
    assert info.height == 240
    assert info.fps == 30.0
    assert info.video_codec == "h264"
    assert info.audio_codec == "aac"
    assert info.audio_channels == 1
    assert len(info.streams) >= 2
    assert "mp4" in info.format_name.lower() or "mov" in info.format_name.lower()
    assert info.file_size_bytes > 0
    assert info.platform == "local"

    # Verify to_dict serialization
    d = info.to_dict()
    assert d["title"] == "sample.mp4"
    assert d["width"] == 320
    assert d["height"] == 240
    assert d["video_codec"] == "h264"
    assert d["audio_codec"] == "aac"
    assert d["file_size_bytes"] > 0


def test_inspect_file_uri(sample_video_path: Path):
    """Verify inspection handles file:// URIs correctly."""
    file_uri = f"file://{sample_video_path}"
    info = inspect_video(file_uri)

    assert info.error is None
    assert info.width == 320
    assert info.height == 240
    assert info.fps == 30.0
    assert info.video_codec == "h264"
    assert info.audio_codec == "aac"


def test_inspect_local_video_contract(sample_video_path: Path):
    """Verify inspect_local_video delegates cleanly and preserves all metadata."""
    info = inspect_local_video(str(sample_video_path))

    assert isinstance(info, VideoInfo)
    assert info.title == "sample.mp4"
    assert info.width == 320
    assert info.height == 240
    assert info.fps == 30.0
    assert len(info.streams) >= 2


def test_inspect_nonexistent_file():
    """Verify graceful handling when target media does not exist."""
    info = inspect_video("/tmp/nonexistent_video_path_xyz_123.mp4")
    assert info.error is not None
    assert "not found" in info.error.lower()
