#!/usr/bin/env python3
"""
scripts/interactive.py — Orquestador interactivo en 2 fases de video-intake-knowledge

Implementa la experiencia de usuario canónica solicitada:
1. Recepción de vídeo(s) (YouTube, Facebook, Instagram, TikTok o archivos locales).
2. Fase 1: Preguntar qué extraer (vídeo, audio, transcripción, contexto audio, contexto visual).
3. Ejecución: Extracción robusta con herramientas locales (yt-dlp, ffmpeg, tesseract, whisper si disponible).
4. Fase 2: Preguntar qué hacer con lo extraído (mensaje a sesión, contexto, banco de ideas existente,
   nuevo banco de memoria, o crear herramienta/skill/agente con propuestas reales).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

# Añadir packages y raíz al path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "packages"))

from video_intake_core.acquisition import detect_video_sources  # noqa: E402
from video_intake_core.orchestrator import (  # noqa: E402
    check_and_extract,
    generate_asset_scaffold,
    list_memory_banks,
    parse_extraction_choices,
    route_extracted_knowledge,
)

__all__ = [
    "check_and_extract",
    "parse_extraction_choices",
    "route_extracted_knowledge",
    "list_memory_banks",
    "generate_asset_scaffold",
]


def print_banner() -> None:
    print("=" * 70)
    print("  🎬 Video Intake Knowledge — Orquestador Interactivo Multi-Entorno")
    print("=" * 70)


def prompt_selection(prompt_text: str, valid_options: set[str], default: str = "") -> str:
    """Solicita una opción validada al usuario por terminal interactivo."""
    while True:
        try:
            choice = input(prompt_text).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nOperación cancelada por el usuario.")
            sys.exit(0)

        if not choice and default:
            return default
        if choice in valid_options:
            return choice
        print(f"Opción no válida ('{choice}'). Opciones disponibles: {', '.join(sorted(valid_options))}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Video Intake Knowledge — Orquestador interactivo en 2 fases"
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="URLs de vídeo (YouTube, FB, IG, TikTok) o rutas a archivos locales",
    )
    parser.add_argument(
        "-o", "--output-dir",
        default="./artifacts",
        help="Directorio para guardar artefactos locales (por defecto: ./artifacts)",
    )
    parser.add_argument(
        "--select",
        help="Preselección de operaciones (ej: '1,3,5' o '6' / 'todo')",
    )

    args = parser.parse_args()
    print_banner()

    inputs = list(args.inputs)
    if not inputs:
        print("Pega uno o varios enlaces de vídeo (YouTube, Facebook, Instagram, TikTok)")
        print("o rutas a archivos locales (.mp4, .mov, .mkv, .webm):")
        try:
            line = input("> ").strip()
            if line:
                inputs = re.split(r"[,;\s]+", line)
        except (EOFError, KeyboardInterrupt):
            print("\nSalida.")
            sys.exit(0)

    if not inputs:
        print("No se proporcionó ningún vídeo o enlace. Saliendo.", file=sys.stderr)
        sys.exit(1)

    # Detección de fuentes
    sources: list[dict[str, Any]] = []
    for item in inputs:
        item = item.strip()
        if not item:
            continue
        p = Path(item)
        if p.exists() and p.is_file():
            sources.append({
                "type": "local",
                "original_input": str(p),
                "resolved_url": str(p.resolve()),
                "platform": "local",
                "title": p.stem,
                "is_local": True,
            })
        else:
            detected = detect_video_sources(item)
            if detected:
                for s in detected:
                    stype = getattr(s, "source_type", "url")
                    sources.append({
                        "type": stype,
                        "original_input": item,
                        "resolved_url": getattr(s, "resolved_path", None) or getattr(s, "url", item),
                        "platform": str(stype),
                        "title": getattr(s, "title", None) or Path(item).stem,
                        "is_local": stype == "local",
                    })
            else:
                sources.append({
                    "type": "url",
                    "original_input": item,
                    "resolved_url": item,
                    "platform": "generic",
                    "title": "video",
                    "is_local": False,
                })

    print(f"\n[+] Se detectaron {len(sources)} vídeo(s):")
    for idx, s in enumerate(sources, 1):
        print(f"  {idx}. [{s['platform']}] {s['title']} ({s['resolved_url']})")

    # Fase 1: Preguntar qué extraer
    if args.select:
        operations = parse_extraction_choices(args.select)
    else:
        print("\n" + "=" * 70)
        print("  FASE 1: ¿QUÉ NECESITAS EXTRAER DEL VÍDEO?")
        print("=" * 70)
        print("  [1] Descarga del vídeo de manera local")
        print("  [2] Descarga del audio del vídeo de manera local")
        print("  [3] Transcripción de audio (con timestamps)")
        print("  [4] Contexto basado en audio")
        print("  [5] Contexto extraído de manera visual (para diagramas, flujos, esquemas)")
        print("  [6] Todo lo anterior (1, 2, 3, 4 y 5)")
        print("-" * 70)
        print("Puedes seleccionar uno (ej: 1), varios (ej: 1, 3, 5) o todo (6):")
        choice = prompt_selection(
            "Selecciona opción [1-6]: ",
            {"1", "2", "3", "4", "5", "6", "todo", "todos", ""},
            default="6",
        )
        operations = parse_extraction_choices(choice)

    print(f"\nOperaciones seleccionadas: {sorted(operations)}")

    # Ejecución
    out_dir = Path(args.output_dir)
    artifacts = check_and_extract(sources, operations, out_dir)

    # Fase 2: Preguntar qué hacer con lo extraído
    route_extracted_knowledge(artifacts)


if __name__ == "__main__":
    main()
