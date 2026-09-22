"""Extract command for video-intake-knowledge."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from video_intake_core.cli import _detect_sources, _resolve_config


def run_extraction(args: argparse.Namespace) -> int:
    """Extrae contenido de una o varias fuentes."""
    sources_raw = [args.source] if getattr(args, "source", None) else []
    files = getattr(args, "file", None) or []
    sources = _detect_sources(sources_raw, files)

    if not sources:
        print("No se detectaron fuentes procesables.", file=sys.stderr)
        return 1

    from video_intake_core.orchestrator import check_and_extract, parse_extraction_choices

    select_raw = getattr(args, "select", "6") or "6"
    operations = parse_extraction_choices(select_raw)
    config = _resolve_config(args)
    root_out = getattr(args, "output", None) or config.get("storage", {}).get("root_dir", "./artifacts")

    artifacts = check_and_extract(sources, operations, Path(root_out))

    if args.json:
        print(json.dumps(artifacts, indent=2, ensure_ascii=False))
        return 0

    print(f"\nExtracción completada. Job ID: {artifacts.get('job_id')}")
    print(f"Directorio de artefactos: {artifacts.get('job_dir')}")
    if artifacts.get("files"):
        print("Archivos generados:")
        for k, v in artifacts["files"].items():
            print(f"  - {k}: {v}")
    return 0



def extract_command(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    extract_p = subparsers.add_parser("extract", help="Extrae contenido de una fuente.")
    extract_p.add_argument("source", help="URL o ruta del vídeo.")
    extract_p.add_argument("--select", "-s", type=str, default="6", help="Selecciones: 1,2,3,4,5,6 o 'todo' (default: 6 = todo).")
    extract_p.add_argument("--file", "-f", nargs="*", default=[], help="Archivo(s) local(es) adicionales.")
    extract_p.set_defaults(func=run_extraction)
    return extract_p
