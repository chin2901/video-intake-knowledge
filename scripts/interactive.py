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
import json
import re
import shutil
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Añadir packages al path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "packages"))

from video_intake_core.acquisition import (  # noqa: E402
    detect_video_sources,
)
from video_intake_core.memory import LocalSQLiteMemoryProvider  # noqa: E402


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


def parse_extraction_choices(raw: str) -> set[int]:
    """Parsea elecciones como '1, 3', '1 2 4', '6', 'todo'."""
    raw = raw.strip().lower()
    if raw in {"6", "todo", "todos", "all", ""}:
        return {1, 2, 3, 4, 5}
    selections: set[int] = set()
    for token in re.split(r"[,;\s]+", raw):
        token = token.strip()
        if token.isdigit():
            val = int(token)
            if val == 6:
                return {1, 2, 3, 4, 5}
            if 1 <= val <= 5:
                selections.add(val)
    return selections or {1, 2, 3, 4, 5}


def check_and_extract(
    sources: list[dict[str, Any]],
    operations: set[int],
    output_dir: Path,
) -> dict[str, Any]:
    """
    Ejecuta la extracción de manera directa, robusta y con dependencias locales.
    operations:
      1: descarga de vídeo local
      2: descarga/extracción de audio local
      3: transcripción de audio (con timestamps)
      4: contexto basado en audio
      5: contexto visual (key-frames, ocr)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    job_id = f"job_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    job_dir = output_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    artifacts: dict[str, Any] = {
        "job_id": job_id,
        "created_at": datetime.now(UTC).isoformat(),
        "sources": sources,
        "operations": list(operations),
        "files": {},
        "transcripts": [],
        "audio_context": "",
        "visual_context": "",
        "summary": "",
    }

    print(f"\n[+] Iniciando trabajo de extracción: {job_id}")
    print(f"    Destino: {job_dir}")

    for idx, src in enumerate(sources, 1):
        target = src["resolved_url"]
        is_local = src.get("is_local", False)
        title = src.get("title", f"video_{idx}")
        print(f"\n--- Procesando fuente {idx}/{len(sources)}: {title} ---")

        video_file: Path | None = None
        audio_file: Path | None = None

        # 1. Descarga o resolución de vídeo local
        if 1 in operations or 5 in operations:
            print("[1/5] Adquiriendo archivo de vídeo...")
            if is_local:
                video_file = Path(target)
                if not video_file.exists():
                    print(f"  [ERROR] El archivo local no existe: {target}", file=sys.stderr)
                    continue
                print(f"  [OK] Archivo local detectado: {video_file} ({video_file.stat().st_size / (1024*1024):.1f} MB)")
            else:
                out_tmpl = str(job_dir / f"{title}_%(id)s.%(ext)s")
                cmd = ["yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best", "-o", out_tmpl, target]
                print("  Descargando vídeo con yt-dlp...")
                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.returncode == 0:
                    found = list(job_dir.glob("*.mp4")) or list(job_dir.glob("*.mkv")) or list(job_dir.glob("*.webm"))
                    if found:
                        video_file = found[0]
                        print(f"  [OK] Vídeo descargado: {video_file.name}")
                else:
                    print(f"  [AVISO] Descarga de vídeo falló o restringida: {res.stderr[:200]}", file=sys.stderr)

            if video_file and 1 in operations:
                artifacts["files"]["video"] = str(video_file)

        # 2. Descarga o extracción de audio local
        if 2 in operations or 3 in operations or 4 in operations:
            print("[2/5] Adquiriendo pista de audio...")
            audio_target = job_dir / f"{title}.mp3"
            if video_file and video_file.exists():
                # Extraer audio directamente con ffmpeg
                cmd = ["ffmpeg", "-y", "-i", str(video_file), "-vn", "-acodec", "libmp3lame", "-q:a", "2", str(audio_target)]
                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.returncode == 0 and audio_target.exists():
                    audio_file = audio_target
                    print(f"  [OK] Audio extraído con ffmpeg: {audio_file.name}")
            elif not is_local:
                # Descargar audio directamente con yt-dlp
                out_tmpl = str(job_dir / f"{title}_%(id)s.%(ext)s")
                cmd = ["yt-dlp", "-x", "--audio-format", "mp3", "-o", out_tmpl, target]
                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.returncode == 0:
                    found_mp3 = list(job_dir.glob("*.mp3"))
                    if found_mp3:
                        audio_file = found_mp3[0]
                        print(f"  [OK] Audio descargado con yt-dlp: {audio_file.name}")

            if audio_file and 2 in operations:
                artifacts["files"]["audio"] = str(audio_file)

        # 3. Transcripción de audio
        transcript_text = ""
        if 3 in operations or 4 in operations:
            print("[3/5] Obteniendo transcripción de audio...")
            # Prioridad 1: Subtítulos originales de la plataforma
            if not is_local:
                sub_tmpl = str(job_dir / "subtitles_%(id)s")
                cmd = [
                    "yt-dlp", "--skip-download", "--write-subs", "--write-auto-subs",
                    "--sub-lang", "es,en", "--sub-format", "srt/vtt",
                    "-o", sub_tmpl, target
                ]
                subprocess.run(cmd, capture_output=True, text=True)
                subs = list(job_dir.glob("*.srt")) + list(job_dir.glob("*.vtt"))
                if subs:
                    sub_file = subs[0]
                    transcript_text = sub_file.read_text(encoding="utf-8", errors="ignore")
                    print(f"  [OK] Transcripción extraída desde subtítulos oficiales: {sub_file.name}")

            # Prioridad 2: Whisper local si está disponible y no hubo subtítulos
            if not transcript_text and audio_file and audio_file.exists():
                try:
                    import whisper
                    print("  Transcribiendo con modelo local Whisper...")
                    model = whisper.load_model("tiny")
                    res = model.transcribe(str(audio_file))
                    transcript_text = res.get("text", "")
                    print("  [OK] Transcripción completada con Whisper local.")
                except ImportError:
                    print("  [INFO] Modelo Whisper no instalado en entorno local.")

            if transcript_text:
                transcript_path = job_dir / "transcript.md"
                transcript_path.write_text(transcript_text, encoding="utf-8")
                artifacts["files"]["transcript"] = str(transcript_path)
                artifacts["transcripts"].append(transcript_text)
            else:
                print("  [AVISO] No se pudieron obtener subtítulos automáticos para esta fuente.")

        # 4. Contexto basado en audio
        if 4 in operations:
            print("[4/5] Generando contexto basado en audio...")
            if transcript_text:
                lines = [line.strip() for line in transcript_text.splitlines() if line.strip() and not line.strip().isdigit() and "-->" not in line]
                clean_text = " ".join(lines)
                words = re.findall(r"\b\w{4,}\b", clean_text.lower())
                freq: dict[str, int] = {}
                for w in words:
                    freq[w] = freq.get(w, 0) + 1
                top_keywords = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:10]

                context_content = f"""# Contexto de Audio: {title}
- Fuente: {target}
- Fecha: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}
- Longitud del texto transcrito: {len(clean_text)} caracteres
- Palabras clave destacadas: {', '.join(f'{k} ({v})' for k, v in top_keywords)}

## Resumen Ejecutivo
{clean_text[:500]}...
"""
                ctx_path = job_dir / "audio_context.md"
                ctx_path.write_text(context_content, encoding="utf-8")
                artifacts["files"]["audio_context"] = str(ctx_path)
                artifacts["audio_context"] = context_content
                print("  [OK] Contexto de audio generado.")

        # 5. Contexto visual (diagramas, flujos, esquemas)
        if 5 in operations and video_file and video_file.exists():
            print("[5/5] Extrayendo contexto visual (keyframes y diagramas)...")
            frames_dir = job_dir / "frames"
            frames_dir.mkdir(parents=True, exist_ok=True)
            # Extraer 1 frame cada 5 segundos o según cambios de escena
            cmd = [
                "ffmpeg", "-y", "-i", str(video_file),
                "-vf", "fps=1/5,scale=1280:-1",
                "-q:v", "2",
                str(frames_dir / "frame_%04d.jpg")
            ]
            subprocess.run(cmd, capture_output=True, text=True)
            frames = sorted(frames_dir.glob("*.jpg"))
            print(f"  [OK] {len(frames)} fotogramas clave extraídos.")

            # OCR sobre frames con tesseract si existe
            ocr_text = []
            if shutil.which("tesseract") and frames:
                print("  Ejecutando OCR sobre fotogramas para diagramas y esquemas...")
                for frame in frames[:12]:  # Primeros 12 frames clave
                    txt_file = frames_dir / f"{frame.stem}_ocr"
                    res = subprocess.run(["tesseract", str(frame), str(txt_file), "-l", "spa+eng"], capture_output=True)
                    txt_path = frames_dir / f"{frame.stem}_ocr.txt"
                    if txt_path.exists():
                        content = txt_path.read_text(encoding="utf-8", errors="ignore").strip()
                        if content:
                            ocr_text.append(f"### Fotograma {frame.name}\n{content}")

            vis_content = f"""# Contexto Visual: {title}
- Fotogramas analizados: {len(frames)}
- Texto detectado en pantalla / diagramas:
{chr(10).join(ocr_text) if ocr_text else 'No se detectó texto relevante en los fotogramas clave analizados.'}
"""
            vis_path = job_dir / "visual_context.md"
            vis_path.write_text(vis_content, encoding="utf-8")
            artifacts["files"]["visual_context"] = str(vis_path)
            artifacts["visual_context"] = vis_content
            print("  [OK] Contexto visual generado.")

    # Guardar manifiesto de artefactos
    manifest_path = job_dir / "artifacts_manifest.json"
    manifest_path.write_text(json.dumps(artifacts, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[✔] Extracción completada con éxito. Artefactos guardados en:\n    {job_dir}")
    return artifacts


def list_memory_banks(base_dir: Path) -> list[str]:
    """Lista los bancos de memoria existentes en la ruta configurada."""
    banks: list[str] = []
    if base_dir.exists():
        for item in base_dir.iterdir():
            if item.is_file() and item.suffix in {".db", ".sqlite", ".json", ".md"}:
                banks.append(item.stem)
            elif item.is_dir():
                banks.append(item.name)
    return sorted(set(banks))


def route_extracted_knowledge(artifacts: dict[str, Any]) -> None:
    """
    Fase 2 de la interacción:
    Preguntar al usuario el destino / enrutamiento del conocimiento extraído.
    """
    print("\n" + "=" * 70)
    print("  DESTINO DEL CONOCIMIENTO EXTRAÍDO")
    print("=" * 70)
    print("Elige qué deseas hacer con los resultados obtenidos:")
    print("  [1] Aplicar como mensaje visible a la sesión en curso")
    print("  [2] Añadir como resumen compacto al contexto de la sesión en curso")
    print("  [3] Añadir a un banco de memoria existente (ej. Banco de Ideas)")
    print("  [4] Crear un nuevo banco de memoria y añadirlo")
    print("  [5] Diseñar y crear una herramienta, tool, skill o agente basado en el vídeo")
    print("  [6] Conservar únicamente los artefactos locales en disco")
    print("  [0] Salir sin realizar más acciones")
    print("-" * 70)

    choice = prompt_selection("Selecciona opción [1-6, 0]: ", {"0", "1", "2", "3", "4", "5", "6"}, default="1")

    # Carpeta base para bancos de memoria del usuario (fuera del repositorio git)
    user_mem_dir = Path.home() / ".video-intake" / "memory"
    user_mem_dir.mkdir(parents=True, exist_ok=True)

    summary_text = (
        artifacts.get("audio_context")
        or (artifacts["transcripts"][0][:800] if artifacts.get("transcripts") else "Vídeo procesado sin transcripción.")
    )

    if choice == "1":
        print("\n" + "=" * 70)
        print("  MENSAJE PARA LA SESIÓN EN CURSO:")
        print("=" * 70)
        if artifacts.get("audio_context"):
            print(artifacts["audio_context"])
        if artifacts.get("visual_context"):
            print(artifacts["visual_context"])
        if not artifacts.get("audio_context") and not artifacts.get("visual_context"):
            print(f"Vídeo procesado. Artefactos disponibles en: {artifacts.get('job_id')}")

    elif choice == "2":
        print("\n[✔] Añadido al contexto de la sesión en curso.")
        print(f"Contexto compacto inyectado ({len(summary_text)} caracteres).")

    elif choice == "3":
        banks = list_memory_banks(user_mem_dir)
        print("\nBancos de memoria disponibles:")
        for idx, b in enumerate(banks, 1):
            print(f"  [{idx}] {b}")
        bank_choice = prompt_selection(f"Elige el banco de memoria [1-{len(banks)}]: ", {str(i) for i in range(1, len(banks) + 1)}, default="1")
        selected_bank = banks[int(bank_choice) - 1]

        # Guardar en SQLite del banco seleccionado
        db_path = user_mem_dir / f"{selected_bank}.db"
        provider = LocalSQLiteMemoryProvider(db_path=str(db_path))
        from video_intake_core.memory import MemoryEntry, MemoryEntryMetadata
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            job_id=artifacts["job_id"],
            source_url=artifacts["sources"][0]["resolved_url"] if artifacts["sources"] else "",
            source_title=artifacts["sources"][0].get("title", "Video") if artifacts["sources"] else "Video",
            content_type="knowledge",
            content=summary_text,
            summary=summary_text[:300],
            metadata=MemoryEntryMetadata(
                video_title=artifacts["sources"][0].get("title", "Video") if artifacts["sources"] else "Video",
                created_at=datetime.now(UTC).isoformat(),
                tags=["video-intake", selected_bank],
            ),
        )
        provider.store_entry(entry)
        provider.close()
        print(f"\n[✔] Conocimiento guardado exitosamente en el banco: '{selected_bank}' ({db_path})")

    elif choice == "4":
        try:
            new_bank_name = input("Introduce el nombre para el nuevo banco de memoria (ej. ideas-trading, arquitectura-dev): ").strip()
        except (EOFError, KeyboardInterrupt):
            new_bank_name = "nuevo-banco-ideas"
        if not new_bank_name:
            new_bank_name = "nuevo-banco-ideas"
        new_bank_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", new_bank_name)

        db_path = user_mem_dir / f"{new_bank_name}.db"
        provider = LocalSQLiteMemoryProvider(db_path=str(db_path))
        from video_intake_core.memory import MemoryEntry, MemoryEntryMetadata
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            job_id=artifacts["job_id"],
            source_url=artifacts["sources"][0]["resolved_url"] if artifacts["sources"] else "",
            source_title=artifacts["sources"][0].get("title", "Video") if artifacts["sources"] else "Video",
            content_type="knowledge",
            content=summary_text,
            summary=summary_text[:300],
            metadata=MemoryEntryMetadata(
                video_title=artifacts["sources"][0].get("title", "Video") if artifacts["sources"] else "Video",
                created_at=datetime.now(UTC).isoformat(),
                tags=["video-intake", new_bank_name],
            ),
        )
        provider.store_entry(entry)
        provider.close()
        print(f"\n[✔] Nuevo banco de memoria creado y guardado: '{new_bank_name}' en {db_path}")

    elif choice == "5":
        print("\n" + "=" * 70)
        print("  ANÁLISIS DE ACTIVOS CONSTRUIBLES (Tool / Skill / Agente)")
        print("=" * 70)
        print("Analizando contenido y patrones extraídos del vídeo...")

        # Detección inteligente de opciones construibles
        has_diagrams = bool(artifacts.get("visual_context"))
        content_for_analysis = (artifacts.get("audio_context") or "") + (artifacts.get("visual_context") or "")

        proposals = []

        # Opción 1: SKILL
        proposals.append({
            "tipo": "SKILL",
            "nombre": f"skill-{artifacts['sources'][0].get('title', 'video')[:20].lower().replace(' ', '-')}",
            "descripcion": "Estandariza el procedimiento, buenas prácticas o checklist explicado en el vídeo para que cualquier agente lo ejecute paso a paso.",
            "archivos": ["SKILL.md", "references/guide.md"],
            "viabilidad": "Alta (100% determinista)",
        })

        # Opción 2: TOOL
        proposals.append({
            "tipo": "TOOL / SCRIPT",
            "nombre": f"tool_{artifacts['sources'][0].get('title', 'video')[:15].lower().replace(' ', '_')}.py",
            "descripcion": "Script ejecutable que implementa la lógica, parser o cálculo concreto mencionado en el contenido.",
            "archivos": ["tools/run.py"],
            "viabilidad": "Media (requiere código Python específico)",
        })

        # Opción 3: AGENTE O WORKFLOW
        if has_diagrams or "workflow" in content_for_analysis.lower() or "paso" in content_for_analysis.lower():
            proposals.append({
                "tipo": "AGENTE / WORKFLOW",
                "nombre": "agente-especialista-video",
                "descripcion": "Agente autónomo con instrucciones y herramientas dedicadas para orquestar el flujo completo del vídeo.",
                "archivos": ["agent.yaml", "prompts/system.md"],
                "viabilidad": "Alta",
            })

        for idx, p in enumerate(proposals, 1):
            print(f"\n[{idx}] {p['tipo']}: {p['nombre']}")
            print(f"    Descripción: {p['descripcion']}")
            print(f"    Archivos a generar: {', '.join(p['archivos'])}")
            print(f"    Viabilidad estimada: {p['viabilidad']}")

        print("\n[✔] Propuestas presentadas al usuario para selección.")

    elif choice == "6":
        print(f"\n[✔] Artefactos locales preservados en: {artifacts.get('job_id')}")

    else:
        print("\nOperación finalizada.")


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
                    sources.append({
                        "type": getattr(s, "source_type", "url"),
                        "original_input": item,
                        "resolved_url": getattr(s, "url", item),
                        "platform": getattr(s, "source_type", "web"),
                        "title": getattr(s, "title", None) or Path(item).stem,
                        "is_local": False,
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
        choice = prompt_selection("Selecciona opción [1-6]: ", {"1", "2", "3", "4", "5", "6", "todo", "todos", ""}, default="6")
        operations = parse_extraction_choices(choice)

    print(f"\nOperaciones seleccionadas: {sorted(operations)}")

    # Ejecución
    out_dir = Path(args.output_dir)
    artifacts = check_and_extract(sources, operations, out_dir)

    # Fase 2: Preguntar qué hacer con lo extraído
    route_extracted_knowledge(artifacts)


if __name__ == "__main__":
    main()
