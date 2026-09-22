"""
Unit tests for Concurrent Batch Processing Engine (F5, F6).

Verifies:
1. ThreadPoolExecutor concurrent execution.
2. SQLite JobManager persistence in isolated db path.
3. Progress emission and error handling.
4. YAML and JSON manifest parsing.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import pytest
import yaml
from video_intake_core.batch import BatchResult, cmd_batch, run_batch


@pytest.fixture
def sample_video_path() -> Path:
    p = Path(__file__).parent.parent / "fixtures" / "video" / "sample.mp4"
    assert p.exists()
    return p.resolve()


def test_batch_runner_concurrent_execution(sample_video_path: Path, tmp_path: Path):
    """Verify ThreadPoolExecutor concurrently processes entries and tracks SQLite jobs."""
    manifest_file = tmp_path / "manifest.yaml"
    manifest_data = {
        "videos": [
            {"url": f"file://{sample_video_path}", "select": "1,2", "title": "sample_1"},
            {"url": f"file://{sample_video_path}", "select": "2", "title": "sample_2"},
            {"url": f"file://{sample_video_path}", "select": "1", "title": "sample_3"},
        ]
    }
    with open(manifest_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(manifest_data, f)

    db_path = tmp_path / "test_jobs.db"
    events = []

    def on_progress(event: dict):
        events.append(event)

    result = run_batch(
        manifest_path=manifest_file,
        max_workers=3,
        output_dir=tmp_path / "artifacts",
        db_path=db_path,
        progress_callback=on_progress,
    )

    assert isinstance(result, BatchResult)
    assert result.total == 3
    assert result.successful == 3
    assert result.failed == 0
    assert len(result.jobs) == 3
    assert len(events) >= 6  # running and completed for each

    # Verify SQLite persistence
    assert db_path.exists()
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM jobs WHERE status = 'completed'")
    completed_count = cursor.fetchone()[0]
    conn.close()
    assert completed_count == 3


def test_batch_runner_json_manifest(sample_video_path: Path, tmp_path: Path):
    """Verify batch processing works with JSON manifests."""
    manifest_file = tmp_path / "manifest.json"
    manifest_data = [
        {"url": f"file://{sample_video_path}", "select": "2", "title": "json_entry_1"},
        {"url": f"file://{sample_video_path}", "select": "2", "title": "json_entry_2"},
    ]
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f)

    db_path = tmp_path / "json_jobs.db"
    result = run_batch(
        manifest_path=manifest_file,
        max_workers=2,
        output_dir=tmp_path / "json_artifacts",
        db_path=db_path,
    )

    assert result.total == 2
    assert result.successful == 2
    assert result.failed == 0


def test_batch_runner_empty_manifest(tmp_path: Path):
    """Verify clean handling of empty manifest."""
    manifest_file = tmp_path / "empty.yaml"
    manifest_file.write_text("videos: []\n", encoding="utf-8")

    result = run_batch(manifest_file, max_workers=2, output_dir=tmp_path / "out")
    assert result.total == 0
    assert result.successful == 0
    assert result.failed == 0


def test_cmd_batch_cli(sample_video_path: Path, tmp_path: Path):
    """Verify cmd_batch CLI handler executes and returns 0."""
    manifest_file = tmp_path / "manifest.yaml"
    manifest_data = {
        "videos": [
            {"url": f"file://{sample_video_path}", "select": "1,2", "title": "cli_batch_1"},
        ]
    }
    with open(manifest_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(manifest_data, f)

    args = argparse.Namespace(
        manifest=str(manifest_file),
        json=True,
        parallel=2,
        output=str(tmp_path / "cli_artifacts"),
    )
    code = cmd_batch(args)
    assert code == 0
