"""Artifacts command for video-intake-knowledge."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from video_intake_core.artifacts import list_artifacts


def show_artifacts(args: argparse.Namespace) -> int:
    """Lista los artefactos de un job."""

    try:
        artifacts = list_artifacts(args.job_id)
    except Exception:
        artifacts = []

    job_dir = Path("artifacts") / args.job_id
    if not artifacts and job_dir.exists() and job_dir.is_dir():
        for p in sorted(job_dir.rglob("*")):
            if p.is_file():
                artifacts.append({
                    "path": str(p),
                    "size_mb": p.stat().st_size / (1024 * 1024),
                    "name": p.name,
                })

    if not artifacts:
        print(f"No hay artefactos para el job: {args.job_id}")
        return 0

    if args.json:
        print(json.dumps(artifacts, indent=2, ensure_ascii=False))
    else:
        print(f"Artefactos para {args.job_id}:")
        for a in artifacts:
            path_str = a.get("path") if isinstance(a, dict) else getattr(a, "path", str(a))
            size = a.get("size_mb", 0) if isinstance(a, dict) else (getattr(a, "size_bytes", 0) / (1024 * 1024))
            print(f"  - {path_str} ({size:.1f} MB)")
    return 0



def artifacts_command(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    artifacts_p = subparsers.add_parser("artifacts", help="Lista los artefactos de un job.")
    artifacts_p.add_argument("job_id", help="ID del job.")
    artifacts_p.set_defaults(func=show_artifacts)
    return artifacts_p
