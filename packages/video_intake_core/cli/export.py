"""
Export command for video-intake-knowledge.

Exports job artifacts in various formats.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from video_intake_core.artifacts import ArtifactManager
from video_intake_core.jobs import get_job
from video_intake_core.storage import StorageManager

logger = logging.getLogger(__name__)


def run_export(args: argparse.Namespace) -> int:
    """Execute the export command."""
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

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build export structure
    export_data = {
        "job_id": job_id,
        "source_url": job.source.url if job.source else "",
        "source_type": job.source.source_type.value if job.source else "",
        "operations": job.operations,
        "status": job.status.value,
        "created_at": job.created_at_utc,
        "completed_at": job.completed_at_utc,
        "artifacts": [],
    }

    for artifact in artifacts:
        export_data["artifacts"].append({
            "type": artifact.get("artifact_type", "unknown"),
            "path": artifact.get("storage_path", ""),
            "size_bytes": artifact.get("size_bytes", 0),
            "sha256": artifact.get("sha256", ""),
            "metadata": artifact.get("metadata", {}),
        })

    if args.format == "json":
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
    elif args.format == "md":
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# Export: {job_id}\n\n")
            f.write(f"**Source:** {export_data['source_url']}\n")
            f.write(f"**Type:** {export_data['source_type']}\n")
            f.write(f"**Status:** {export_data['status']}\n")
            f.write(f"**Created:** {export_data['created_at']}\n")
            if export_data['completed_at']:
                f.write(f"**Completed:** {export_data['completed_at']}\n")
            f.write("\n## Artifacts\n\n")
            for art in export_data["artifacts"]:
                f.write(f"- **{art['type']}** ({art['size_bytes']} bytes)\n")
                f.write(f"  - Path: {art['path']}\n")
                f.write(f"  - SHA256: {art['sha256']}\n")

    print(f"Exported to: {output_path}")
    return 0


def export_command(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """Add the export subcommand to the parser."""
    parser = subparsers.add_parser("export", help="Export job artifacts")
    parser.add_argument("job_id", help="Job ID to export")
    parser.add_argument(
        "-o", "--output",
        default="./export.json",
        help="Output file path (default: ./export.json)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "md"],
        default="json",
        help="Export format (default: json)",
    )
    parser.set_defaults(func=run_export)
    return parser
