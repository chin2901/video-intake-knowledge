"""
Unit tests for Video Acquisition and Normalization module (F3).

Verifies:
1. YouTube URL detection with arbitrary parameter ordering (?feature=shared&v=, ?t=10&v=).
2. Facebook mobile and shortlinks (fb.watch, m.facebook.com).
3. TikTok URL detection and canonical ID extraction.
4. Support for file:// URIs in detect_source.
5. Redirect resolution for shortened links.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from video_intake_core.acquisition import (
    SourceType,
    detect_source,
    detect_source_type,
    extract_all_video_urls,
    resolve_url,
)


@pytest.fixture
def sample_video_path() -> Path:
    p = Path(__file__).parent.parent / "fixtures" / "video" / "sample.mp4"
    assert p.exists()
    return p.resolve()


@pytest.mark.parametrize(
    "url,expected_id",
    [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/watch?feature=shared&v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtube.com/watch?time_continue=10&v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://m.youtube.com/watch?v=dQw4w9WgXcQ&t=15s", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/live/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ],
)
def test_youtube_url_detection_and_parameter_order(url: str, expected_id: str):
    """Verify that YouTube URLs with arbitrary query parameters are correctly detected and canonicalized."""
    source_type = detect_source_type(url)
    assert source_type == SourceType.YOUTUBE

    resolved = resolve_url(url, follow_redirects=False)
    assert resolved.canonical_id == expected_id
    assert resolved.resolved_url == f"https://www.youtube.com/watch?v={expected_id}"


@pytest.mark.parametrize(
    "url,expected_type",
    [
        ("https://fb.watch/abc1234/", SourceType.FACEBOOK),
        ("https://m.facebook.com/watch?v=12345678", SourceType.FACEBOOK),
        ("https://www.facebook.com/watch/?v=12345678", SourceType.FACEBOOK),
        ("https://m.facebook.com/video.php?v=12345678", SourceType.FACEBOOK),
        ("https://www.facebook.com/reel/12345678", SourceType.FACEBOOK),
        ("https://www.facebook.com/share/v/AbCdEfGhIj/", SourceType.FACEBOOK),
    ],
)
def test_facebook_shortlinks_and_mobile_urls(url: str, expected_type: SourceType):
    """Verify that Facebook shortlinks (fb.watch) and mobile URLs (m.facebook.com) are detected."""
    source_type = detect_source_type(url)
    assert source_type == expected_type

    resolved = resolve_url(url, follow_redirects=False)
    assert resolved.source_type == SourceType.FACEBOOK
    assert resolved.canonical_id is not None


def test_file_uri_support(sample_video_path: Path):
    """Verify that file:// URIs are cleanly detected as local files."""
    file_uri = f"file://{sample_video_path}"

    source_type = detect_source_type(file_uri)
    assert source_type == SourceType.LOCAL_FILE

    source = detect_source(file_uri)
    assert source is not None
    assert source.source_type == SourceType.LOCAL_FILE
    assert Path(source.url).resolve() == sample_video_path.resolve()
    assert source.title == sample_video_path.stem


def test_redirect_resolution_following():
    """Verify HTTP redirect resolution properly follows shortened links."""
    short_url = "https://vm.tiktok.com/ZMabcdef/"
    final_target = "https://www.tiktok.com/@creator/video/9876543210987654321"

    mock_resp = MagicMock()
    mock_resp.geturl.return_value = final_target
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = None

    with patch("urllib.request.urlopen", return_value=mock_resp):
        resolved = resolve_url(short_url, follow_redirects=True)
        assert resolved.source_type == SourceType.TIKTOK
        assert resolved.canonical_id == "9876543210987654321"
        assert len(resolved.redirect_chain) >= 2
        assert resolved.redirect_chain[-1] == final_target


def test_redirect_resolution_network_error_fallback():
    """Verify redirect resolution falls back gracefully when network fails."""
    short_url = "https://vm.tiktok.com/ZMabcdef/"

    with patch("urllib.request.urlopen", side_effect=OSError("Network unreachable")):
        resolved = resolve_url(short_url, follow_redirects=True)
        assert resolved.source_type == SourceType.TIKTOK
        assert resolved.canonical_id is not None
        assert resolved.resolved_url is not None


def test_extract_all_video_urls_mixed_text():
    """Verify batch extraction of video URLs from free-form text with parameters and shortlinks."""
    text = """
    Check out this video: https://www.youtube.com/watch?feature=shared&v=dQw4w9WgXcQ
    Also this one: https://fb.watch/shortlink123/
    And TikTok: https://vm.tiktok.com/ZM123456/
    """
    urls = extract_all_video_urls(text)
    assert len(urls) == 3
    assert any("youtube.com" in u for u in urls)
    assert any("fb.watch" in u for u in urls)
    assert any("tiktok.com" in u for u in urls)
