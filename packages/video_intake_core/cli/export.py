"""Export command for video-intake-knowledge."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from video_intake_core.jobs import get_job


def run_export(args: argparse.Namespace) -> int:
    """Exporta los resultados de un job."""

    job = get_job(args.job_id)
    manifest_data = None
    if not job:
        manifest_file = Path("artifacts") / args.job_id / "artifacts_manifest.json"
        if manifest_file.exists():
            manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))

    if not job and not manifest_data:
        print(f"Job no encontrado: {args.job_id}", file=sys.stderr)
        return 1

    fmt = args.format or "markdown"
    export_dir = args.output or f"exports/{args.job_id}"
    Path(export_dir).mkdir(parents=True, exist_ok=True)

    title = job.source_title if job else manifest_data.get("sources", [{}])[0].get("title", "Video")
    status_val = (
        (job.status.value if hasattr(job.status, "value") else str(job.status))
        if job
        else "completed"
    )

    if fmt == "json":
        data = job.to_dict() if job else manifest_data
        out = Path(export_dir) / "export.json"
        out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Exportado a {out}")
    elif fmt == "html":
        html = f"<html><body><h1>Export job {args.job_id}</h1><p>Título: {title}</p><p>Estado: {status_val}</p></body></html>"
        html_path = Path(export_dir) / "export.html"
        html_path.write_text(html, encoding="utf-8")
        print(f"Exportado a {html_path}")
    else:
        md_path = Path(export_dir) / "export.md"
        md_path.write_text(f"# Export job {args.job_id}\n\n## Resumen\n\nJob: {args.job_id}\nEstado: {status_val}\nTítulo: {title}\n\n")
        print(f"Exportado a {md_path}")

    return 0



def export_command(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    export_p = subparsers.add_parser("export", help="Exporta resultados de un job.")
    export_p.add_argument("job_id", help="ID del job.")
    export_p.add_argument("--format", "-f", choices=["markdown", "json", "html"], default="markdown", help="Formato de exportación (default: markdown).")
    export_p.add_argument("--output", "-o", type=str, default=None, help="Directorio de salida.")
    export_p.set_defaults(func=run_export)
    return export_p
