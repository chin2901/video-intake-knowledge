"""
Proposals and interactive command integration for video-intake-knowledge.

Manages, displays, and dynamically scaffolds functional assets (Skill, Tool, Agent)
derived from extracted video knowledge, chapters, and topics.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import logging
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _extract_steps_from_content(
    title: str,
    summary: str,
    audio_ctx: str,
    transcript: str,
) -> list[dict[str, str]]:
    """Derive dynamic step-by-step instructions from transcript timestamps or audio context."""
    steps: list[dict[str, str]] = []

    # 1. Search for timestamps in transcript and audio context: e.g. [01:23] or (01:23) or 01:23 -
    ts_pattern = re.compile(
        r"(?:\[|\()?(?P<ts>\d{1,2}:\d{2}(?::\d{2})?)(?:\]|\))?[\s\-:]+(?P<desc>[^\n\r\.]+)",
        re.MULTILINE,
    )

    combined = f"{audio_ctx}\n{transcript}"
    matches = list(ts_pattern.finditer(combined))

    if matches:
        for m in matches[:8]:  # Up to 8 meaningful chapters/steps
            ts = m.group("ts").strip()
            desc = m.group("desc").strip(" -:[]()")
            if desc and len(desc) > 3:
                steps.append({"timestamp": ts, "title": desc})

    # 2. If no timestamps, search for bullet points or headings in audio_ctx
    if not steps:
        lines = [line.strip() for line in audio_ctx.splitlines() if line.strip()]
        for line in lines:
            if line.startswith(("-", "*", "•")) and len(line) > 5:
                cleaned = line.lstrip("-*• ").strip()
                steps.append({"timestamp": "", "title": cleaned})
            elif re.match(r"^\d+\.\s+", line):
                cleaned = re.sub(r"^\d+\.\s+", "", line).strip()
                steps.append({"timestamp": "", "title": cleaned})
            if len(steps) >= 6:
                break

    # 3. Fallback to thematic breakdown based on title and summary
    if not steps:
        steps = [
            {
                "timestamp": "00:00",
                "title": f"Preparación y Análisis de Requisitos para '{title}'",
            },
            {
                "timestamp": "01:30",
                "title": "Configuración y Ejecución del Flujo Operativo Principal",
            },
            {
                "timestamp": "03:00",
                "title": "Validación de Resultados, Criterios de Éxito y Puesta en Marcha",
            },
        ]

    return steps


def _derive_capabilities(title: str, summary: str, audio_ctx: str) -> list[str]:
    """Derive specialized agent capabilities from video keywords and topics."""
    text = f"{title} {summary} {audio_ctx}".lower()
    capabilities = ["ejecucion_guiada", "analisis_contextual"]

    keyword_map = [
        ("docker", "gestion_contenedores_docker"),
        ("kubernetes", "orquestacion_kubernetes"),
        ("nginx", "configuracion_servidor_nginx"),
        ("ssl", "gestion_certificados_ssl"),
        ("api", "integracion_apis_rest"),
        ("fastapi", "desarrollo_fastapi"),
        ("postgres", "administracion_postgresql"),
        ("database", "gestion_bases_datos"),
        ("whisper", "transcripcion_audio_whisper"),
        ("ocr", "extraccion_texto_ocr"),
        ("tesseract", "analisis_visual_tesseract"),
        ("ffmpeg", "procesamiento_multimedia_ffmpeg"),
        ("audio", "procesamiento_audio_digital"),
        ("video", "adquisicion_fuentes_video"),
        ("scraping", "extraccion_datos_web"),
        ("security", "auditoria_seguridad_aplicaciones"),
        ("deploy", "automatizacion_despliegue"),
        ("linux", "administracion_sistemas_linux"),
        ("python", "automatizacion_scripts_python"),
        ("testing", "ejecucion_pruebas_automatizadas"),
    ]

    for kw, cap in keyword_map:
        if kw in text and cap not in capabilities:
            capabilities.append(cap)

    if len(capabilities) == 2:
        # Add generic derived capability from title
        clean_slug = re.sub(r"[^a-zA-Z0-9]+", "_", title[:25]).strip("_").lower()
        if clean_slug:
            capabilities.append(f"especialista_{clean_slug}")

    return capabilities


def generate_elevated_scaffold(
    asset_type: str,
    asset_name: str,
    artifacts: dict[str, Any],
    output_base: Path | str = Path("./generated"),
) -> list[Path]:
    """
    Generates dynamic, syntactically valid scaffolding files derived from video
    transcripts, timestamps, chapters, and extracted topics.
    """
    base_dir = Path(output_base).resolve()
    sanitized_name = re.sub(r"[^a-zA-Z0-9_\-]", "-", asset_name).lower().strip("-")
    target_dir = base_dir / sanitized_name
    target_dir.mkdir(parents=True, exist_ok=True)

    created_files: list[Path] = []
    src = artifacts.get("sources", [{}])[0] if artifacts.get("sources") else {}
    title = src.get("title") or artifacts.get("title") or "Conocimiento de Vídeo"
    summary = (
        artifacts.get("summary")
        or artifacts.get("audio_context")
        or "Procedimiento estructurado a partir del contenido audiovisual."
    )
    audio_ctx = artifacts.get("audio_context") or ""
    vis_ctx = artifacts.get("visual_context") or ""
    transcripts = artifacts.get("transcripts") or []
    transcript_text = "\n".join(transcripts) if isinstance(transcripts, list) else str(transcripts)

    # Extract dynamic steps and capabilities
    dynamic_steps = _extract_steps_from_content(title, summary, audio_ctx, transcript_text)
    capabilities = _derive_capabilities(title, summary, audio_ctx)

    asset_upper = asset_type.upper()

    # ------------------------------------------------------------------
    # 1. SKILL Scaffolding
    # ------------------------------------------------------------------
    if asset_upper in {"SKILL", "SKILL.MD"}:
        skill_file = target_dir / "SKILL.md"

        steps_rendered = []
        for i, s in enumerate(dynamic_steps, 1):
            ts_str = f" `[{s['timestamp']}]`" if s.get("timestamp") else ""
            steps_rendered.append(
                f"{i}. **Paso {i}:{ts_str} {s['title']}**\n"
                f"   - Ejecutar las directivas correspondientes documentadas en el vídeo.\n"
                f"   - Verificar que los parámetros de salida son correctos antes de avanzar."
            )
        rendered_steps_str = "\n".join(steps_rendered)

        content = f"""---
name: {sanitized_name}
description: Procedimiento operativo y metodológico derivado del vídeo: {title}
version: 1.0.0
---

# SKILL: {title}

> Habilidad generada dinámicamente por `video-intake-knowledge`.
> **Fuente:** {src.get('resolved_url', 'N/A')}
> **Generado:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}

---

## 1. Resumen Metodológico
{summary}

---

## 2. Instrucciones de Ejecución Paso a Paso
{rendered_steps_str}

---

## 3. Conocimiento de Audio Extraído
{audio_ctx if audio_ctx.strip() else 'No se extrajo contexto de audio adicional.'}

---

## 4. Contexto Visual y Diagramas (OCR)
{vis_ctx if vis_ctx.strip() else 'No se detectaron diagramas ni texto visual OCR adicional.'}
"""
        skill_file.write_text(content, encoding="utf-8")
        created_files.append(skill_file)

    # ------------------------------------------------------------------
    # 2. TOOL Scaffolding
    # ------------------------------------------------------------------
    elif asset_upper in {"TOOL", "SCRIPT", "TOOL / SCRIPT"}:
        tool_file = target_dir / "tool.py"

        steps_funcs = []
        calls = []
        for i, s in enumerate(dynamic_steps[:5], 1):
            fn_name = f"step_{i}_{re.sub(r'[^a-zA-Z0-9]+', '_', s['title'][:20]).lower().strip('_')}"
            steps_funcs.append(
                f"def {fn_name}(target: str, verbose: bool = False) -> bool:\n"
                f'    """Ejecuta {s["title"]}."""\n'
                f'    if verbose:\n'
                f'        print(f"[*] Ejecutando: {s["title"]}...")\n'
                f'    # Lógica derivada del vídeo\n'
                f'    return True\n'
            )
            calls.append(f"    {fn_name}(args.target, args.verbose)")

        funcs_code = "\n".join(steps_funcs)
        calls_code = "\n".join(calls)

        content = f"""#!/usr/bin/env python3
\"\"\"
tool.py — Herramienta ejecutable generada dinámicamente por video-intake-knowledge
Origen: {title}
Fuente: {src.get('resolved_url', 'N/A')}
Generado: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}
\"\"\"

from __future__ import annotations

import argparse
import sys


{funcs_code}

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Herramienta operativa automatizada para: {title}"
    )
    parser.add_argument(
        "--target", "-t",
        default="",
        help="Objetivo o parámetro principal de ejecución",
    )
    parser.add_argument(
        "--config", "-c",
        default="default",
        help="Ruta al archivo de configuración",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Mostrar registro de ejecución detallado",
    )

    args = parser.parse_args(argv)

    print(f"[+] Iniciando herramienta: {title}")
    if args.target:
        print(f"    Target: {{args.target}}")

{calls_code}

    print("[✔] Ejecución completada con éxito.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
"""
        tool_file.write_text(content, encoding="utf-8")
        tool_file.chmod(0o755)
        created_files.append(tool_file)

    # ------------------------------------------------------------------
    # 3. AGENT Scaffolding
    # ------------------------------------------------------------------
    elif asset_upper in {"AGENTE", "AGENT", "WORKFLOW", "AGENTE / WORKFLOW"}:
        agent_yaml = target_dir / "agent.yaml"
        caps_yaml = "\n".join([f"  - {c}" for c in capabilities])

        yaml_content = f"""name: {sanitized_name}
version: 1.0.0
role: Especialista autónomo en '{title}'
system_prompt: prompts/system.md
capabilities:
{caps_yaml}
"""
        agent_yaml.write_text(yaml_content, encoding="utf-8")
        created_files.append(agent_yaml)

        prompts_dir = target_dir / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        sys_prompt = prompts_dir / "system.md"

        steps_agent = []
        for i, s in enumerate(dynamic_steps, 1):
            steps_agent.append(f"{i}. **{s['title']}**: Guiar al usuario con precisión técnica.")
        steps_agent_str = "\n".join(steps_agent)

        prompt_content = f"""# Prompt del Agente Especialista: {title}

Eres un agente de IA experto y autónomo especializado en la metodología de:
**{title}**
Fuente de referencia: `{src.get('resolved_url', 'N/A')}`

## 1. Tu Misión
Guiar al usuario y ejecutar deterministamente los procedimientos y flujos descritos en el material audiovisual:
{summary}

## 2. Capacidades y Responsabilidades
{steps_agent_str}

## 3. Directivas Operativas
- Aplica el principio de radical simplicidad (Menos es Más): soluciones directas sin sobre-ingeniería.
- No especules sobre parámetros no definidos: verifica el contexto del usuario.
- Valida los resultados en cada etapa antes de proseguir a la siguiente fase.

## 4. Contexto del Dominio
{audio_ctx[:1000] if audio_ctx else 'Contexto operativo obtenido del análisis del vídeo.'}
"""
        sys_prompt.write_text(prompt_content, encoding="utf-8")
        created_files.append(sys_prompt)

    return created_files


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
        # Search for most recent job manifest
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
    src = artifacts.get("sources", [{}])[0] if artifacts.get("sources") else {}
    title = src.get("title") or "Video Intake"

    print("=" * 70)
    print(f"  PROPUESTAS DE ACTIVOS CONSTRUIBLES — Job: {job_id}")
    print(f"  Título: {title}")
    print("=" * 70)

    clean_title_dash = re.sub(r"[^a-zA-Z0-9]+", "-", title[:25]).lower().strip("-") or "asset"
    clean_title_under = re.sub(r"[^a-zA-Z0-9]+", "_", title[:20]).lower().strip("_") or "tool"

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
            "descripcion": f"Script ejecutable que implementa la lógica o cálculo explicado en '{title}'.",
            "archivos": ["tool.py"],
            "viabilidad": "Alta (ejecución autónoma local)",
        },
        {
            "tipo": "AGENTE",
            "nombre": f"agente-{clean_title_dash[:18]}",
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
            created = generate_elevated_scaffold(
                asset_type=prop["tipo"],
                asset_name=prop["nombre"],
                artifacts=artifacts,
                output_base=out_dir,
            )
            print(f"\n[✔] {prop['tipo']} generado en:")
            for cf in created:
                print(f"    - {cf}")

    return 0


def run_interactive_cli(args: argparse.Namespace) -> int:
    """Entry point for video-intake interactive [URL]."""
    try:
        from scripts.interactive import run_interactive_flow
    except ImportError:
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        sys.path.insert(0, str(repo_root))
        from scripts.interactive import run_interactive_flow

    inputs = [args.source] if getattr(args, "source", None) else []
    output_dir = getattr(args, "output", "./artifacts") or "./artifacts"
    select = getattr(args, "select", None)

    return run_interactive_flow(inputs=inputs, output_dir=output_dir, select=select)


def proposals_command(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """Add the proposals and interactive subcommands to the parser."""
    # 1. Register proposals subcommand
    parser = subparsers.add_parser(
        "proposals",
        help="Muestra o genera propuestas de Tool, Skill o Agente",
    )
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

    # 2. Register interactive subcommand
    interactive_parser = subparsers.add_parser(
        "interactive",
        help="Orquestador interactivo en 2 fases (extracción y enrutamiento de conocimiento)",
    )
    interactive_parser.add_argument(
        "source",
        nargs="?",
        default=None,
        help="URL o ruta del vídeo a procesar",
    )
    interactive_parser.add_argument(
        "--output", "-o",
        default="./artifacts",
        help="Directorio para guardar artefactos locales (default: ./artifacts)",
    )
    interactive_parser.add_argument(
        "--select", "-s",
        help="Preselección de operaciones (ej: '1,3,5' o '6')",
    )
    interactive_parser.set_defaults(func=run_interactive_cli)

    # 3. Enhance extract subcommand if present to support --interactive flag and interactive TTY
    extract_parser = subparsers.choices.get("extract")
    if extract_parser:
        with contextlib.suppress(argparse.ArgumentError):
            extract_parser.add_argument(
                "--interactive", "-i",
                action="store_true",
                help="Ejecutar en modo interactivo en 2 fases",
            )

        original_func = extract_parser.get_default("func")

        def wrapped_extract(args: argparse.Namespace) -> int:
            # If user explicitly requested interactive or invoked without args in a TTY
            if getattr(args, "interactive", False):
                return run_interactive_cli(args)
            if original_func:
                return original_func(args)
            return 0

        extract_parser.set_defaults(func=wrapped_extract)

    return parser
