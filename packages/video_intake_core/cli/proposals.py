"""
Proposals command for video-intake-knowledge.

Manages and displays build proposals.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

from video_intake_core.orchestrator import generate_asset_scaffold

logger = logging.getLogger(__name__)


def show_proposals(args: argparse.Namespace) -> int:
    """Execute the proposals command."""
    artifacts_dir = Path(getattr(args, "artifacts_dir", None) or "artifacts")
    manifest_file: Path | None = None

    if getattr(args, "job_id", None):
        job_cand = Path(args.job_id)
        if job_cand.is_dir() and (job_cand / "artifacts_manifest.json").exists():
            manifest_file = job_cand / "artifacts_manifest.json"
        elif job_cand.is_file() and job_cand.name == "artifacts_manifest.json":
            manifest_file = job_cand
        else:
            candidate = artifacts_dir / args.job_id / "artifacts_manifest.json"
            if candidate.exists():
                manifest_file = candidate
            else:
                print(f"No se encontró el manifiesto para el job: {args.job_id}", file=sys.stderr)
                return 1
    else:
        # Buscar el job más reciente
        if artifacts_dir.exists():
            manifests = sorted(
                artifacts_dir.glob("*/artifacts_manifest.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if manifests:
                manifest_file = manifests[0]

    if not manifest_file or not manifest_file.exists():
        print("No hay extracciones previas con artefactos disponibles.", file=sys.stderr)
        print("Ejecuta primero: video-intake extract <URL_O_ARCHIVO>", file=sys.stderr)
        return 1

    try:
        artifacts: dict[str, Any] = json.loads(manifest_file.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Error leyendo manifiesto {manifest_file}: {e}", file=sys.stderr)
        return 1

    job_id = artifacts.get("job_id", manifest_file.parent.name)
    src = artifacts.get("sources", [{}])[0]
    title = src.get("title") or "Video Intake"

    print("=" * 70)
    print(f"  PROPUESTAS DE ACTIVOS CONSTRUIBLES — Job: {job_id}")
    print(f"  Título: {title}")
    print("=" * 70)

    clean_title_dash = re.sub(r"[^a-zA-Z0-9]", "-", title[:20]).lower().strip("-")
    clean_title_under = re.sub(r"[^a-zA-Z0-9]", "_", title[:15]).lower().strip("_")

    proposals = [
        {
            "tipo": "SKILL",
            "nombre": f"skill-{clean_title_dash}",
            "descripcion": f"Estandariza el procedimiento y checklist de '{title}' para ejecución paso a paso.",
            "archivos": ["SKILL.md"],
            "viabilidad": "Alta (100% determinista)",
        },
        {
            "tipo": "TOOL",
            "nombre": f"tool_{clean_title_under}",
            "descripcion": "Script ejecutable que implementa la lógica o cálculo explicado en el vídeo.",
            "archivos": ["tool.py"],
            "viabilidad": "Alta (ejecución autónoma local)",
        },
        {
            "tipo": "AGENTE",
            "nombre": f"agente-{clean_title_dash[:15]}",
            "descripcion": f"Agente autónomo con instrucciones dedicadas para orquestar el flujo de '{title}'.",
            "archivos": ["agent.yaml", "prompts/system.md"],
            "viabilidad": "Alta",
        },
    ]

    for idx, p in enumerate(proposals, 1):
        print(f"\n[{idx}] {p['tipo']}: {p['nombre']}")
        print(f"    Descripción: {p['descripcion']}")
        print(f"    Archivos a generar: {', '.join(p['archivos'])}")
        print(f"    Viabilidad: {p['viabilidad']}")

    scaffold_target = getattr(args, "scaffold", None)
    out_dir = Path(getattr(args, "output", None) or "./generated")

    if scaffold_target:
        to_generate = []
        if scaffold_target in {"skill", "all"}:
            to_generate.append(proposals[0])
        if scaffold_target in {"tool", "all"}:
            to_generate.append(proposals[1])
        if scaffold_target in {"agent", "agente", "all"}:
            to_generate.append(proposals[2])

        for prop in to_generate:
            created = generate_asset_scaffold(
                asset_type=prop["tipo"],
                asset_name=prop["nombre"],
                artifacts=artifacts,
                output_base=out_dir,
            )
            print(f"\n[✔] {prop['tipo']} generado en:")
            for cf in created:
                print(f"    - {cf}")

    return 0


def proposals_command(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """Add the proposals subcommand to the parser."""
    parser = subparsers.add_parser("proposals", help="Muestra o genera propuestas de Tool, Skill o Agente")
    parser.add_argument("--job-id", help="ID del job del cual generar propuestas")
    parser.add_argument(
        "--scaffold",
        choices=["skill", "tool", "agent", "all"],
        help="Genera directamente los archivos de la propuesta seleccionada",
    )
    parser.add_argument(
        "--output", "-o",
        default="./generated",
        help="Directorio de destino para los activos generados (default: ./generated)",
    )
    parser.add_argument(
        "--artifacts-dir",
        default=None,
        help="Directorio base de artefactos (default: ./artifacts)",
    )
    parser.set_defaults(func=show_proposals)
    return parser
