#!/usr/bin/env python3
"""
scripts/extract.py — Script utilitario directo para extracción de vídeo.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "packages"))

from video_intake_core.acquisition import detect_video_sources  # noqa: E402

from scripts.interactive import check_and_extract, parse_extraction_choices  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Extrae contenido de un vídeo de forma directa.")
    parser.add_argument("source", help="URL o archivo local de vídeo")
    parser.add_argument(
        "-s", "--select",
        default="6",
        help="Operaciones a realizar (1=video, 2=audio, 3=transcript, 4=context, 5=visual, 6=todo). Def: 6",
    )
    parser.add_argument(
        "-o", "--output-dir",
        default="./artifacts",
        help="Directorio de artefactos",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Salida en formato JSON",
    )

    args = parser.parse_args()
    source_val = args.source.strip()
    p = Path(source_val)

    if p.exists() and p.is_file():
        sources = [{
            "type": "local",
            "original_input": str(p),
            "resolved_url": str(p.resolve()),
            "platform": "local",
            "title": p.stem,
            "is_local": True,
        }]
    else:
        detected = detect_video_sources(source_val)
        if detected:
            sources = [{
                "type": getattr(s, "source_type", "url"),
                "original_input": source_val,
                "resolved_url": getattr(s, "url", source_val),
                "platform": getattr(s, "source_type", "web"),
                "title": getattr(s, "title", None) or p.stem,
                "is_local": False,
            } for s in detected]
        else:
            sources = [{
                "type": "url",
                "original_input": source_val,
                "resolved_url": source_val,
                "platform": "generic",
                "title": "video",
                "is_local": False,
            }]

    ops = parse_extraction_choices(args.select)
    artifacts = check_and_extract(sources, ops, Path(args.output_dir))

    if args.json:
        print(json.dumps(artifacts, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
