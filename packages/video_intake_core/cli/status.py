"""Status command for video-intake-knowledge."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from video_intake_core.jobs import get_job


def run_status(args: argparse.Namespace) -> int:
    """Muestra el estado de un job."""

    job = get_job(args.job_id)
    if not job:
        manifest_file = Path("artifacts") / args.job_id / "artifacts_manifest.json"
        if manifest_file.exists():
            data = json.loads(manifest_file.read_text(encoding="utf-8"))
            if args.json:
                print(json.dumps(data, indent=2, ensure_ascii=False))
            else:
                print(f"Job: {data.get('job_id', args.job_id)}")
                print("Estado: completed (desde artefactos locales)")
                srcs = data.get("sources", [])
                if srcs:
                    print(f"Fuente: {srcs[0].get('resolved_url')}")
                    print(f"Título: {srcs[0].get('title', 'N/A')}")
                print(f"Creado: {data.get('created_at', 'N/A')}")
            return 0
        print(f"Job no encontrado: {args.job_id}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(job.to_dict(), indent=2, ensure_ascii=False))
    else:
        status_val = job.status.value if hasattr(job.status, "value") else str(job.status)
        print(f"Job: {job.id}")
        print(f"Estado: {status_val}")
        print(f"Título: {job.source_title}")
        print(f"URL: {job.source_url}")
        print(f"Tipo: {job.source_type}")
        print(f"Creado: {job.created_at}")
        if job.result_metadata:
            print(f"Resultado: {job.result_metadata}")
    return 0



def status_command(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    status_p = subparsers.add_parser("status", help="Muestra el estado de un job.")
    status_p.add_argument("job_id", help="ID del job.")
    status_p.set_defaults(func=run_status)
    return status_p
