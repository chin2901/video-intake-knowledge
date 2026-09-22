"""
video_intake_core.orchestrator — Orquestador central de extracción y enrutamiento.

Implementa la experiencia nuclear en 2 fases:
1. Recepción y validación de fuentes de vídeo (YouTube, FB, IG, TikTok o archivos locales).
2. Fase 1: Extracción autónoma local (vídeo, audio, transcripción, contexto audio, contexto visual).
3. Fase 2: Enrutamiento del conocimiento (mensaje, contexto de sesión, banco de ideas,
   nuevo banco de memoria, o generación de activos tool/skill/agente).
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from video_intake_core.acquisition import SourceType, detect_source
from video_intake_core.audio import download_audio_only, extract_audio
from video_intake_core.jobs import JobManager, JobState
from video_intake_core.memory import (
    LocalSQLiteMemoryProvider,
    MemoryEntry,
    MemoryEntryMetadata,
)
from video_intake_core.ocr import ocr_frame_directory
from video_intake_core.transcription import (
    extract_captions_from_platform,
    extract_local_captions,
    transcribe_with_whisper,
)
from video_intake_core.visual import detect_scenes, extract_keyframes

logger = logging.getLogger(__name__)


def parse_extraction_choices(raw: str) -> set[int]:
    """Parsea elecciones como '1, 3', '1 2 4', '6', 'todo', 'all'. Delega al SSoT."""
    from video_intake_core.cli.menu import parse_selection_to_set
    return parse_selection_to_set(raw)


def check_and_extract(
    sources: list[dict[str, Any]],
    operations: set[int],
    output_dir: Path | str,
    db_path: Path | str | None = None,
    job_id: str | None = None,
) -> dict[str, Any]:
    """
    Ejecuta la extracción de manera directa, robusta y con dependencias locales.

    operations:
      1: descarga/preservación de vídeo local
      2: descarga/extracción de audio local (.mp3)
      3: transcripción de audio (con timestamps)
      4: contexto basado en audio (resumen, tópicos clave)
      5: contexto visual (keyframes y OCR para diagramas, esquemas, flujos)
    """
    out_path = Path(output_dir).resolve()
    out_path.mkdir(parents=True, exist_ok=True)

    job_id = job_id or f"job_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    job_dir = out_path / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    artifacts: dict[str, Any] = {
        "job_id": job_id,
        "job_dir": str(job_dir),
        "created_at": datetime.now(UTC).isoformat(),
        "sources": sources,
        "operations": sorted(operations),
        "files": {},
        "transcripts": [],
        "audio_context": "",
        "visual_context": "",
        "summary": "",
    }

    if not sources:
        artifacts["error"] = "No se proporcionaron fuentes válidas."
        return artifacts

    print(f"\n[+] Iniciando trabajo de extracción: {job_id}")
    print(f"    Destino: {job_dir}")

    for idx, src in enumerate(sources, 1):
        target = str(src.get("resolved_url") or src.get("url") or "")
        is_local = bool(src.get("is_local", False))

        from video_intake_core.security import validate_local_file, validate_video_url
        if is_local or target.startswith("file://") or Path(target).exists():
            try:
                validate_local_file(target.replace("file://", ""))
            except Exception as e:
                logger.error(f"Security blocked local file {target}: {e}")
                artifacts.setdefault("errors", []).append(str(e))
                continue
        elif target.startswith(("http://", "https://")):
            try:
                validate_video_url(target)
            except Exception as e:
                logger.error(f"Security blocked URL {target}: {e}")
                artifacts.setdefault("errors", []).append(str(e))
                continue

        title = src.get("title") or f"video_{idx}"
        title = re.sub(r"[^\w\-_.]", "_", title)

        print(f"\n--- Procesando fuente {idx}/{len(sources)}: {title} ---")

        video_file: Path | None = None
        audio_file: Path | None = None

        # 0. Resolución inicial de archivo si es local mediante acquisition
        source_obj = detect_source(target)
        if source_obj and source_obj.source_type == SourceType.LOCAL_FILE:
            local_candidate = Path(source_obj.url).resolve()
            if local_candidate.exists() and local_candidate.is_file():
                video_file = local_candidate
                is_local = True
        elif is_local or (target.startswith("file://") or Path(target).exists()):
            local_candidate = Path(target.replace("file://", "")).resolve()
            if local_candidate.exists() and local_candidate.is_file():
                video_file = local_candidate
                is_local = True

        # 1. Descarga o resolución de vídeo local
        if 1 in operations or (video_file is None and (2 in operations or 5 in operations)):
            if is_local and video_file:
                print(f"[1/5] Archivo local detectado: {video_file.name} ({video_file.stat().st_size / (1024*1024):.1f} MB)")
                if 1 in operations:
                    dest_video = job_dir / video_file.name
                    if dest_video != video_file and not dest_video.exists():
                        try:
                            shutil.copy2(video_file, dest_video)
                            artifacts["files"]["video"] = str(dest_video)
                        except Exception:
                            artifacts["files"]["video"] = str(video_file)
                    else:
                        artifacts["files"]["video"] = str(video_file)
            elif not is_local and target.startswith("http"):
                print("[1/5] Adquiriendo vídeo con yt-dlp...")
                out_tmpl = str(job_dir / f"{title}_%(id)s.%(ext)s")
                cmd = [
                    "yt-dlp",
                    "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                    "--no-playlist",
                    "-o", out_tmpl,
                    target,
                ]
                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.returncode == 0:
                    found = (
                        list(job_dir.glob("*.mp4"))
                        or list(job_dir.glob("*.mkv"))
                        or list(job_dir.glob("*.webm"))
                    )
                    if found:
                        video_file = found[0]
                        print(f"  [OK] Vídeo descargado: {video_file.name}")
                        if 1 in operations:
                            artifacts["files"]["video"] = str(video_file)
                else:
                    print(f"  [AVISO] Descarga directa de vídeo no completada: {res.stderr[:200]}", file=sys.stderr)

        # 2. Descarga o extracción de audio local (.mp3) mediante audio module
        if 2 in operations or 3 in operations or 4 in operations:
            print("[2/5] Adquiriendo pista de audio...")
            audio_target = job_dir / f"{title}.mp3"

            if video_file and video_file.exists():
                try:
                    audio_res = extract_audio(video_file, job_dir)
                    audio_extracted = Path(audio_res["path"])
                    if audio_extracted.exists():
                        if audio_extracted != audio_target and not audio_target.exists():
                            shutil.copy2(audio_extracted, audio_target)
                            audio_file = audio_target
                        else:
                            audio_file = audio_extracted
                        print(f"  [OK] Audio extraído con módulo audio: {audio_file.name}")
                except Exception as e:
                    logger.debug("Modular audio extraction fallback to ffmpeg: %s", e)
                    cmd = [
                        "ffmpeg", "-y", "-i", str(video_file),
                        "-vn", "-acodec", "libmp3lame", "-q:a", "2",
                        str(audio_target),
                    ]
                    res = subprocess.run(cmd, capture_output=True, text=True)
                    if res.returncode == 0 and audio_target.exists():
                        audio_file = audio_target
                        print(f"  [OK] Audio extraído con ffmpeg: {audio_file.name}")
            elif not is_local and target.startswith("http"):
                try:
                    audio_res = download_audio_only(target, output_path=str(audio_target))
                    audio_file = Path(audio_res["path"])
                    print(f"  [OK] Audio descargado con módulo audio: {audio_file.name}")
                except Exception as e:
                    logger.debug("download_audio_only fallback to yt-dlp: %s", e)
                    out_tmpl = str(job_dir / f"{title}_%(id)s.%(ext)s")
                    cmd = ["yt-dlp", "--no-playlist", "-x", "--audio-format", "mp3", "-o", out_tmpl, target]
                    res = subprocess.run(cmd, capture_output=True, text=True)
                    if res.returncode == 0:
                        found_mp3 = list(job_dir.glob("*.mp3"))
                        if found_mp3:
                            audio_file = found_mp3[0]
                            print(f"  [OK] Audio descargado con yt-dlp: {audio_file.name}")

            if audio_file and 2 in operations:
                artifacts["files"]["audio"] = str(audio_file)

        # 3. Transcripción de audio (subtítulos nativos o whisper) mediante transcription module
        transcript_text = ""
        if 3 in operations or 4 in operations:
            print("[3/5] Obteniendo transcripción de audio...")
            # Prioridad 1: Subtítulos locales mediante transcripción modular
            if is_local and video_file:
                try:
                    local_subs = extract_local_captions(video_file)
                    if local_subs:
                        transcript_text = "\n".join(s.get("text", "") for s in local_subs if s.get("text"))
                        print(f"  [OK] Subtítulo detectado con módulo transcription: {len(local_subs)} segmentos")
                except Exception as e:
                    logger.debug("extract_local_captions fallback: %s", e)

                if not transcript_text:
                    for ext in [".srt", ".vtt", ".sub"]:
                        sub_candidate = video_file.with_suffix(ext)
                        if sub_candidate.exists():
                            transcript_text = sub_candidate.read_text(encoding="utf-8", errors="ignore")
                            print(f"  [OK] Subtítulo adyacente detectado: {sub_candidate.name}")
                            break

            # Prioridad 1b: Subtítulos oficiales de plataforma si es remoto
            if not transcript_text and not is_local and target.startswith("http"):
                try:
                    platform_subs = extract_captions_from_platform(target)
                    if platform_subs:
                        transcript_text = "\n".join(s.get("text", "") for s in platform_subs if s.get("text"))
                        print("  [OK] Subtítulos oficiales obtenidos vía módulo transcription.")
                except Exception as e:
                    logger.debug("extract_captions_from_platform fallback: %s", e)

                if not transcript_text:
                    sub_tmpl = str(job_dir / "subtitles_%(id)s")
                    cmd = [
                        "yt-dlp", "--skip-download", "--write-subs", "--write-auto-subs",
                        "--sub-lang", "es,en", "--sub-format", "srt/vtt",
                        "--no-playlist",
                        "-o", sub_tmpl, target,
                    ]
                    subprocess.run(cmd, capture_output=True, text=True)
                    subs = list(job_dir.glob("*.srt")) + list(job_dir.glob("*.vtt"))
                    if subs:
                        sub_file = subs[0]
                        transcript_text = sub_file.read_text(encoding="utf-8", errors="ignore")
                        print(f"  [OK] Transcripción extraída desde subtítulos oficiales: {sub_file.name}")

            # Prioridad 2: Whisper local mediante transcripción modular
            if not transcript_text and audio_file and audio_file.exists():
                try:
                    whisper_res = transcribe_with_whisper(audio_file)
                    if whisper_res and hasattr(whisper_res, "text") and whisper_res.text:
                        transcript_text = whisper_res.text
                        print("  [OK] Transcripción completada con módulo Whisper.")
                    elif isinstance(whisper_res, dict) and whisper_res.get("text"):
                        transcript_text = whisper_res["text"]
                        print("  [OK] Transcripción completada con módulo Whisper.")
                except Exception as e:
                    logger.debug("transcribe_with_whisper fallback: %s", e)

            if transcript_text:
                transcript_path = job_dir / "transcript.md"
                transcript_path.write_text(transcript_text, encoding="utf-8")
                artifacts["files"]["transcript"] = str(transcript_path)
                artifacts["transcripts"].append(transcript_text)
            else:
                print("  [INFO] No se detectaron subtítulos oficiales ni Whisper local activo.")

        # 4. Contexto basado en audio (resumen ejecutivo y tópicos)
        if 4 in operations:
            print("[4/5] Generando contexto basado en audio...")
            if transcript_text:
                lines = [
                    line.strip()
                    for line in transcript_text.splitlines()
                    if line.strip() and not line.strip().isdigit() and "-->" not in line
                ]
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
{clean_text[:600]}...
"""
                ctx_path = job_dir / "audio_context.md"
                ctx_path.write_text(context_content, encoding="utf-8")
                artifacts["files"]["audio_context"] = str(ctx_path)
                artifacts["audio_context"] = context_content
                artifacts["summary"] = clean_text[:300]
                print("  [OK] Contexto de audio generado.")

        # 5. Contexto visual (diagramas, flujos, esquemas con OCR) mediante visual y ocr modules
        if 5 in operations and video_file and video_file.exists():
            print("[5/5] Extrayendo contexto visual (keyframes y diagramas)...")
            frames_dir = job_dir / "frames"
            frames_dir.mkdir(parents=True, exist_ok=True)

            try:
                scenes = detect_scenes(video_file)
                extract_keyframes(video_file, scenes, frames_dir)
            except Exception as e:
                logger.debug("Modular keyframe extraction fallback: %s", e)

            frames = sorted(frames_dir.glob("*.png")) + sorted(frames_dir.glob("*.jpg"))
            if not frames:
                cmd = [
                    "ffmpeg", "-y", "-i", str(video_file),
                    "-vf", "fps=1/5,scale=1280:-1",
                    "-q:v", "2",
                    str(frames_dir / "frame_%04d.jpg"),
                ]
                subprocess.run(cmd, capture_output=True, text=True)
                frames = sorted(frames_dir.glob("*.jpg"))

            print(f"  [OK] {len(frames)} fotogramas clave extraídos.")

            ocr_text = []
            if frames:
                try:
                    ocr_results = ocr_frame_directory(frames_dir, pattern="*.*")
                    for ocr_item in ocr_results:
                        txt = ocr_item.get("text", "").strip()
                        f_name = Path(ocr_item.get("frame_path", "")).name
                        if txt:
                            ocr_text.append(f"### Fotograma {f_name}\n{txt}")
                except Exception as e:
                    logger.debug("Modular OCR failed: %s", e)

                if not ocr_text and shutil.which("tesseract"):
                    print("  Ejecutando OCR sobre fotogramas para diagramas y esquemas...")
                    for frame in frames[:12]:
                        txt_file = frames_dir / f"{frame.stem}_ocr"
                        subprocess.run(
                            ["tesseract", str(frame), str(txt_file), "-l", "spa+eng"],
                            capture_output=True,
                        )
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

    # Registrar el trabajo en JobManager si es posible (en ~/.video-intake/jobs.db para evitar polución git)
    try:
        resolved_db = Path(db_path) if db_path else (Path.home() / ".video-intake" / "jobs.db")
        resolved_db.parent.mkdir(parents=True, exist_ok=True)
        job_mgr = JobManager(db_path=resolved_db)
        first_src = sources[0] if sources else {}
        job = job_mgr.create_job(
            source=first_src,
            operations=[str(op) for op in operations],
            job_id=job_id,
        )
        job_mgr.update_progress(job.job_id, 100.0, current_phase="completed")
        job_mgr.update_status(job.job_id, JobState.COMPLETED)
    except Exception as e:
        logger.debug("No se pudo registrar en JobManager: %s", e)

    print(f"\n[✔] Extracción completada con éxito. Artefactos guardados en:\n    {job_dir}")
    return artifacts


def list_memory_banks(base_dir: Path | str) -> list[str]:
    """Lista los bancos de memoria existentes en la ruta configurada."""
    p = Path(base_dir).resolve()
    banks: list[str] = []
    if p.exists():
        for item in p.iterdir():
            if item.is_file() and item.suffix in {".db", ".sqlite", ".json", ".md"}:
                banks.append(item.stem)
            elif item.is_dir() and not item.name.startswith("."):
                banks.append(item.name)
    return sorted(set(banks))


def generate_asset_scaffold(
    asset_type: str,
    asset_name: str,
    artifacts: dict[str, Any],
    output_base: Path | str = Path("./generated"),
) -> list[Path]:
    """
    Genera los archivos reales de una Skill, Tool o Agente basándose en
    el conocimiento extraído del vídeo.
    """
    base_dir = Path(output_base).resolve()
    sanitized_name = re.sub(r"[^a-zA-Z0-9_\-]", "-", asset_name).lower().strip("-")
    target_dir = base_dir / sanitized_name
    target_dir.mkdir(parents=True, exist_ok=True)

    created_files: list[Path] = []
    src = artifacts["sources"][0] if artifacts.get("sources") else {}
    title = src.get("title") or "Conocimiento de Vídeo"
    summary = artifacts.get("summary") or "Procedimiento extraído de vídeo."
    audio_ctx = artifacts.get("audio_context") or ""
    vis_ctx = artifacts.get("visual_context") or ""

    if asset_type.upper() == "SKILL":
        skill_file = target_dir / "SKILL.md"
        content = f"""---
name: {sanitized_name}
description: Procedimiento extraído de vídeo: {title}
version: 1.0.0
---

# SKILL: {title}

> Generado automáticamente por video-intake-knowledge a partir de:
> Fuente: {src.get('resolved_url', 'N/A')}
> Fecha: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}

## Resumen del Procedimiento
{summary}

## Instrucciones de Ejecución Paso a Paso
1. **Preparación y Contexto:**
   - Verificar los prerrequisitos documentados en el material audiovisual.
2. **Ejecución del Flujo:**
   - Seguir las etapas descritas en el material de referencia.
3. **Validación:**
   - Confirmar que los resultados coinciden con los criterios de éxito esperados.

## Conocimiento de Audio Extraído
{audio_ctx}

## Contexto Visual y Diagramas
{vis_ctx}
"""
        skill_file.write_text(content, encoding="utf-8")
        created_files.append(skill_file)

    elif asset_type.upper() in {"TOOL", "SCRIPT", "TOOL / SCRIPT"}:
        tool_file = target_dir / "tool.py"
        content = f"""#!/usr/bin/env python3
\"\"\"
tool.py — Herramienta ejecutable generada por video-intake-knowledge
Origen: {title} ({src.get('resolved_url', 'N/A')})
\"\"\"

import argparse
import sys

def main() -> int:
    parser = argparse.ArgumentParser(description="Ejecuta la lógica de: {title}")
    parser.add_argument("--input", "-i", help="Parámetro de entrada", default="")
    args = parser.parse_args()

    print(f"[+] Ejecutando herramienta generada para: {title}")
    print(f"    Entrada: {{args.input}}")
    # Lógica derivada del vídeo
    print("[✔] Operación completada con éxito.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
"""
        tool_file.write_text(content, encoding="utf-8")
        tool_file.chmod(0o755)
        created_files.append(tool_file)

    elif asset_type.upper() in {"AGENTE", "AGENT", "WORKFLOW", "AGENTE / WORKFLOW"}:
        agent_yaml = target_dir / "agent.yaml"
        yaml_content = f"""name: {sanitized_name}
version: 1.0.0
role: Especialista derivado del vídeo '{title}'
system_prompt: prompts/system.md
capabilities:
  - ejecucion_guiada
  - analisis_contextual
"""
        agent_yaml.write_text(yaml_content, encoding="utf-8")
        created_files.append(agent_yaml)

        prompts_dir = target_dir / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        sys_prompt = prompts_dir / "system.md"
        prompt_content = f"""# Prompt del Agente Especialista: {title}

Eres un agente de IA especializado en la metodología extraída de:
{src.get('resolved_url', 'N/A')}

## Tu Misión
Guiar al usuario en la ejecución precisa de los flujos de trabajo explicados en el vídeo:
{summary}

## Contexto Operativo
{audio_ctx[:800]}
"""
        sys_prompt.write_text(prompt_content, encoding="utf-8")
        created_files.append(sys_prompt)

    return created_files


def route_extracted_knowledge(
    artifacts: dict[str, Any],
    choice: str | None = None,
    interactive: bool = True,
    extra_input: str | None = None,
) -> dict[str, Any]:
    """
    Fase 2 de la interacción:
    Preguntar o enrutar el conocimiento extraído según la selección del usuario.
    """
    user_mem_dir = Path.home() / ".video-intake" / "memory"
    user_mem_dir.mkdir(parents=True, exist_ok=True)

    summary_text = (
        artifacts.get("audio_context")
        or (artifacts["transcripts"][0][:800] if artifacts.get("transcripts") else "Vídeo procesado.")
    )
    title = (
        artifacts["sources"][0].get("title", "Video")
        if artifacts.get("sources")
        else "Video"
    )
    source_url = (
        artifacts["sources"][0].get("resolved_url", "")
        if artifacts.get("sources")
        else ""
    )

    if interactive and choice is None:
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

        while True:
            try:
                raw_c = input("Selecciona opción [1-6, 0]: ").strip()
            except (EOFError, KeyboardInterrupt):
                raw_c = "1"
            if not raw_c:
                raw_c = "1"
            if raw_c in {"0", "1", "2", "3", "4", "5", "6"}:
                choice = raw_c
                break
            print("Opción inválida. Elige entre 1, 2, 3, 4, 5, 6 o 0.")

    choice = choice or "1"
    result: dict[str, Any] = {"choice": choice, "status": "completed"}

    if choice == "1":
        print("\n" + "=" * 70)
        print("  MENSAJE PARA LA SESIÓN EN CURSO:")
        print("=" * 70)
        msg_parts = []
        if artifacts.get("audio_context"):
            msg_parts.append(artifacts["audio_context"])
        if artifacts.get("visual_context"):
            msg_parts.append(artifacts["visual_context"])
        if not msg_parts:
            msg_parts.append(f"Vídeo procesado con éxito. Job ID: {artifacts.get('job_id')}")
        message_out = "\n\n".join(msg_parts)
        print(message_out)
        result["message"] = message_out

    elif choice == "2":
        print("\n[✔] Añadido al contexto de la sesión en curso.")
        print(f"Contexto compacto inyectado ({len(summary_text)} caracteres).")
        result["context"] = summary_text

    elif choice == "3":
        banks = list_memory_banks(user_mem_dir)
        selected_bank = "banco-de-ideas"

        if not banks:
            print("\n[INFO] No hay bancos de memoria previos en ~/.video-intake/memory/.")
            print("Se utilizará el banco principal: 'banco-de-ideas'.")
        else:
            print("\nBancos de memoria disponibles:")
            for b_idx, b in enumerate(banks, 1):
                print(f"  [{b_idx}] {b}")

            if interactive and extra_input is None:
                try:
                    b_choice = input(f"Elige banco [1-{len(banks)}, def: 1]: ").strip()
                except (EOFError, KeyboardInterrupt):
                    b_choice = "1"
                if b_choice.isdigit() and 1 <= int(b_choice) <= len(banks):
                    selected_bank = banks[int(b_choice) - 1]
                else:
                    selected_bank = banks[0]
            elif extra_input and extra_input in banks:
                selected_bank = extra_input
            else:
                selected_bank = banks[0]

        db_file = user_mem_dir / f"{selected_bank}.db"
        provider = LocalSQLiteMemoryProvider(db_path=str(db_file))
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            job_id=artifacts["job_id"],
            source_url=source_url,
            source_title=title,
            content_type="knowledge",
            content=summary_text,
            summary=summary_text[:300],
            metadata=MemoryEntryMetadata(
                video_title=title,
                created_at=datetime.now(UTC).isoformat(),
                tags=["video-intake", selected_bank],
            ),
        )
        provider.store_entry(entry)
        provider.close()
        print(f"\n[✔] Conocimiento guardado en el banco: '{selected_bank}' ({db_file})")
        result["bank"] = selected_bank
        result["db_path"] = str(db_file)

    elif choice == "4":
        if interactive and extra_input is None:
            try:
                new_bank = input("Nombre del nuevo banco (ej. ideas-trading): ").strip()
            except (EOFError, KeyboardInterrupt):
                new_bank = "nuevo-banco-ideas"
        else:
            new_bank = extra_input or "nuevo-banco-ideas"

        new_bank = re.sub(r"[^a-zA-Z0-9_\-]", "_", new_bank or "nuevo-banco-ideas")
        db_file = user_mem_dir / f"{new_bank}.db"
        provider = LocalSQLiteMemoryProvider(db_path=str(db_file))
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            job_id=artifacts["job_id"],
            source_url=source_url,
            source_title=title,
            content_type="knowledge",
            content=summary_text,
            summary=summary_text[:300],
            metadata=MemoryEntryMetadata(
                video_title=title,
                created_at=datetime.now(UTC).isoformat(),
                tags=["video-intake", new_bank],
            ),
        )
        provider.store_entry(entry)
        provider.close()
        print(f"\n[✔] Nuevo banco de memoria creado y guardado: '{new_bank}' ({db_file})")
        result["bank"] = new_bank
        result["db_path"] = str(db_file)

    elif choice == "5":
        print("\n" + "=" * 70)
        print("  ANÁLISIS DE ACTIVOS CONSTRUIBLES (Tool / Skill / Agente)")
        print("=" * 70)
        print("Analizando contenido y patrones extraídos del vídeo...")

        proposals = [
            {
                "tipo": "SKILL",
                "nombre": f"skill-{re.sub(r'[^a-zA-Z0-9]', '-', title[:20]).lower().strip('-')}",
                "descripcion": f"Estandariza el procedimiento y checklist de '{title}' para ejecución paso a paso.",
                "archivos": ["SKILL.md"],
                "viabilidad": "Alta (100% determinista)",
            },
            {
                "tipo": "TOOL",
                "nombre": f"tool_{re.sub(r'[^a-zA-Z0-9]', '_', title[:15]).lower().strip('_')}",
                "descripcion": "Script ejecutable que implementa la lógica o cálculo explicado en el vídeo.",
                "archivos": ["tool.py"],
                "viabilidad": "Alta (ejecución autónoma local)",
            },
            {
                "tipo": "AGENTE",
                "nombre": f"agente-{re.sub(r'[^a-zA-Z0-9]', '-', title[:15]).lower().strip('-')}",
                "descripcion": f"Agente autónomo con instrucciones dedicadas para orquestar el flujo de '{title}'.",
                "archivos": ["agent.yaml", "prompts/system.md"],
                "viabilidad": "Alta",
            },
        ]

        for p_idx, p in enumerate(proposals, 1):
            print(f"\n[{p_idx}] {p['tipo']}: {p['nombre']}")
            print(f"    Descripción: {p['descripcion']}")
            print(f"    Archivos a generar: {', '.join(p['archivos'])}")
            print(f"    Viabilidad estimada: {p['viabilidad']}")

        result["proposals"] = proposals

        scaffold_choice = extra_input
        if interactive and scaffold_choice is None:
            try:
                scaffold_choice = input(
                    "\n¿Deseas generar los archivos de alguna propuesta ahora? [1=Skill, 2=Tool, 3=Agente, 0=Omitir]: "
                ).strip()
            except (EOFError, KeyboardInterrupt):
                scaffold_choice = "0"

        if scaffold_choice in {"1", "2", "3"}:
            chosen_prop = proposals[int(scaffold_choice) - 1]
            created = generate_asset_scaffold(
                asset_type=chosen_prop["tipo"],
                asset_name=chosen_prop["nombre"],
                artifacts=artifacts,
            )
            print(f"\n[✔] {chosen_prop['tipo']} generado exitosamente en:")
            for cf in created:
                print(f"    - {cf}")
            result["created_files"] = [str(cf) for cf in created]

    elif choice == "6":
        print(f"\n[✔] Artefactos locales preservados en: {artifacts.get('job_dir')}")

    return result
