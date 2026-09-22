"""Cleanup command for video-intake-knowledge."""
from __future__ import annotations

import argparse

from video_intake_core.cli import _make_storage


def run_storage_cleanup(args: argparse.Namespace) -> int:
    """Limpia artefactos antiguos."""
    storage = _make_storage(args)
    removed = storage.cleanup(max_age_days=args.max_age_days, dry_run=args.dry_run)
    if isinstance(removed, dict):
        jobs_val = removed.get("removed_jobs", 0)
        count = len(jobs_val) if isinstance(jobs_val, list) else jobs_val
    elif isinstance(removed, list):
        count = len(removed)
    else:
        count = int(removed) if isinstance(removed, (int, float)) else 0

    if args.dry_run:
        print(f"[dry-run] Se eliminarían {count} artefactos.")
    else:
        print(f"Limpios {count} artefactos.")
    return 0



def cleanup_command(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    cleanup_p = subparsers.add_parser("cleanup", help="Limpia artefactos antiguos.")
    cleanup_p.add_argument("--max-age-days", type=int, default=90, help="Edad máxima en días (default: 90).")
    cleanup_p.add_argument("--dry-run", action="store_true", help="Solo muestra lo que se eliminaría.")
    cleanup_p.set_defaults(func=run_storage_cleanup)
    return cleanup_p
