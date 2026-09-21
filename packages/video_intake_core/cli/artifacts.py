"""
Artifacts command for video-intake-knowledge.

Manages and displays job artifacts.
"""

from __future__ import annotations

import argparse
import logging

from video_intake_core.artifacts import ArtifactManager
from video_intake_core.jobs import get_job
from video_intake_core.storage import StorageManager

logger = logging.getLogger(__name__)


def show_artifacts(args: argparse.Namespace) -> int:
    """Execute the artifacts command."""
    job_id = args.job_id
    job = get_job(job_id)

    if job is None:
        print(f"Job not found: {job_id}")
        return 1

    if not job.result_path:
        print(f"No artifacts available for job: {job_id}")
        return 0

    storage = StorageManager(storage_root=job.result_path)
    artifact_manager = ArtifactManager(storage=storage)
    artifacts = artifact_manager.get_artifacts_for_job(job_id)

    if not artifacts:
        print(f"No artifacts found for job: {job_id}")
        return 0

    print(f"Artifacts for job: {job_id}")
    print()
    for artifact in artifacts:
        size_str = ""
        size = artifact.get("size_bytes", 0)
        if size > 0:
            if size < 1024:
                size_str = f" ({size} B)"
            elif size < 1024 * 1024:
                size_str = f" ({size / 1024:.1f} KB)"
            else:
                size_str = f" ({size / (1024 * 1024):.1f} MB)"

        art_type = artifact.get("artifact_type", "unknown")
        path = artifact.get("storage_path", "unknown")
        print(f"  {art_type}{size_str}")
        print(f"    Path: {path}")
        if artifact.get("description"):
            print(f"    Desc: {artifact['description']}")

    return 0


def artifacts_command(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """Add the artifacts subcommand to the parser."""
    parser = subparsers.add_parser("artifacts", help="List artifacts for a job")
    parser.add_argument("job_id", help="Job ID to show artifacts for")
    parser.set_defaults(func=show_artifacts)
    return parser
