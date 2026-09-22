"""
Shared fixtures and utilities for the 4-tier opaque-box E2E test suite.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"


@pytest.fixture
def project_root() -> Path:
    """Return the absolute path to project root."""
    return PROJECT_ROOT


@pytest.fixture
def sample_video() -> Path:
    """Return path to synthetic sample video."""
    video = FIXTURES_DIR / "video" / "sample.mp4"
    assert video.exists(), f"Sample video not found at {video}"
    return video


@pytest.fixture
def sample_audio() -> Path:
    """Return path to synthetic sample audio."""
    audio = FIXTURES_DIR / "audio" / "sample.wav"
    assert audio.exists(), f"Sample audio not found at {audio}"
    return audio


@pytest.fixture
def sample_subtitles() -> Path:
    """Return path to sample subtitles file."""
    sub = FIXTURES_DIR / "subtitles" / "sample.srt"
    assert sub.exists(), f"Sample subtitles not found at {sub}"
    return sub


@pytest.fixture
def isolated_env(tmp_path: Path) -> dict[str, str]:
    """Provide isolated environment variables pointing HOME and XDG dirs to tmp_path."""
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    env["XDG_CONFIG_HOME"] = str(home / ".config")
    env["XDG_DATA_HOME"] = str(home / ".local" / "share")
    env["XDG_CACHE_HOME"] = str(home / ".cache")
    import site
    env["PYTHONPATH"] = str(PROJECT_ROOT / "packages") + ":" + site.getusersitepackages() + ":" + env.get("PYTHONPATH", "")
    return env


@pytest.fixture
def run_cli(isolated_env: dict[str, str], tmp_path: Path) -> Callable[..., subprocess.CompletedProcess[str]]:
    """Factory fixture to run the video-intake CLI in an isolated subprocess."""

    def _run(*args: str, input_text: str | None = None, cwd: Path | None = None, timeout: float = 30.0) -> subprocess.CompletedProcess[str]:
        work_dir = cwd or tmp_path
        cmd = [sys.executable, "-m", "video_intake_core.cli", *args]
        return subprocess.run(
            cmd,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(work_dir),
            env=isolated_env,
        )

    return _run


@pytest.fixture
def parse_json() -> Callable[[str], Any]:
    """Pytest fixture providing JSON parsing helper for CLI stdout."""
    return parse_cli_json


def parse_cli_json(stdout: str) -> Any:
    try:
        return json.loads(stdout.strip())
    except json.JSONDecodeError:
        pass

    start_dict = stdout.find("{")
    end_dict = stdout.rfind("}")
    start_list = stdout.find("[")
    end_list = stdout.rfind("]")

    if end_dict > end_list and start_dict != -1 and end_dict > start_dict:
        try:
            return json.loads(stdout[start_dict:end_dict+1])
        except json.JSONDecodeError:
            pass
    elif end_list > end_dict and start_list != -1 and end_list > start_list:
        try:
            return json.loads(stdout[start_list:end_list+1])
        except json.JSONDecodeError:
            pass

    return {}
