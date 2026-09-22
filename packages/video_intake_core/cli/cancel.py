"""Cancel command for video-intake-knowledge."""
from __future__ import annotations

import argparse
import sys

from video_intake_core.jobs import cancel_job


def run_cancel(args: argparse.Namespace) -> int:

    """Cancela un job en ejecución."""

    try:
        success = cancel_job(args.job_id)
    except Exception:
        success = False
    if not success:
        print(f"No se pudo cancelar el job: {args.job_id}", file=sys.stderr)
        return 1
    print(f"Job cancelado: {args.job_id}")
    return 0



def cancel_command(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser = subparsers.add_parser("cancel", help="Cancela un job en ejecución.")
    parser.add_argument("job_id", help="ID del job.")
    parser.set_defaults(func=run_cancel)
    return parser
