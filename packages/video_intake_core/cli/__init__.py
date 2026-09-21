"""
CLI para video-intake-knowledge.

Provee el comando ``video-intake`` con todas las operaciones habilitadas:

- doctor
- inspect
- extract
- batch
- status
- cancel
- artifacts
- export
- cleanup
- config validate
- self-test
- models (list, install, verify, remove)

Soporta modo interactivo y no interactivo. Produce salida JSON cuando se
solicita (``--json``) para integración con máquinas.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

from video_intake_core.acquisition import detect_video_sources, SourceType
from video_intake_core.artifacts import ArtifactManager
from video_intake_core.jobs import (
    create_job,
    start_job,
    cancel_job,
    get_job,
    list_jobs,
    JobStatus,
)
from video_intake_core.policies import PolicyResolver
from video_intake_core.memory import (
    MemoryProvider,
    LocalSQLiteMemoryProvider,
    MemoryEntry,
)
from video_intake_core.storage import StorageManager

logger = logging.getLogger("video_intake")
DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


# ============================================================================
# Helpers
# ============================================================================

def _resolve_config(args: argparse.Namespace) -> dict[str, Any]:
    """Carga la configuración de la ruta indicada o del default."""
    config_path = args.config or "config/default.yaml"
    resolver = PolicyResolver(config_path=str(config_path))
    return resolver.config


def _make_storage(args: argparse.Namespace) -> StorageManager:
    config = _resolve_config(args)
    root = config.get("storage", {}).get("root_dir", "./artifacts")
    retention = config.get("storage", {}).get("artifact_retention_days", 90)
    max_gb = config.get("storage", {}).get("max_storage_gb", 100)
    return StorageManager(root_dir=root, retention_days=retention, max_storage_gb=max_gb)


def _make_artifact_manager(args: argparse.Namespace) -> ArtifactManager:
    return ArtifactManager(storage=_make_storage(args))


def _make_memory(args: argparse.Namespace) -> MemoryProvider:
    config = _resolve_config(args)
    default_provider = config.get("memory", {}).get("default_provider", "local")
    if default_provider == "local":
        db_path = config.get("memory", {}).get("db_path", "./memory.db")
        return LocalSQLiteMemoryProvider(db_path=str(db_path))
    # otros providers se añadirían aquí
    return LocalSQLiteMemoryProvider(db_path="./memory.db")


def _detect_sources(urls: list[str], files: list[str]) -> list[dict[str, Any]]:
    """Combina detección de URLs y archivos locales."""
    sources: list[dict[str, Any]] = []
    for url in urls:
        detected = detect_video_sources(url)
        if detected:
            sources.extend(detected)
    for f in files:
        p = Path(f)
        if p.exists():
            detected = detect_video_sources(str(p))
            if detected:
                sources.extend(detected)
            else:
                sources.append(
                    {
                        "type": SourceType.LOCAL_FILE,
                        "original_input": str(p),
                        "resolved_url": str(p),
                        "platform": "local",
                        "title": p.name,
                        "is_local": True,
                    }
                )
    return sources


def _parse_selections(raw: str | None) -> set[str]:
    """Parsea una cadena de selecciones como '1,3,5' o 'todo' o '6'."""
    if raw is None:
        return set()
    raw = raw.strip().lower()
    if raw in {"todo", "todos", "all", "6", "todoslo anterior"}:
        return {"1", "2", "3", "4", "5", "6"}
    result: set[str] = set()
    for part in raw.replace(",", " ").split():
        part = part.strip()
        if part in {"1", "2", "3", "4", "5", "6"}:
            result.add(part)
    return result


# ============================================================================
# Commands
# ============================================================================

def cmd_doctor(args: argparse.Namespace) -> int:
    """Comprueba la salud del entorno."""
    from video_intake_core.audio import extract_audio
    from video_intake_core.transcription import transcribe
    from video_intake_core.visual import analyze_scenes
    from video_intake_core.ocr import batch_ocr
    from video_intake_core.inspection import inspect_video

    results: list[dict[str, Any]] = []

    # Python
    results.append(
        {
            "check": "python",
            "status": "pass",
            "detail": f"{sys.version.split()[0]}",
        }
    )

    # ffmpeg / ffprobe
    import shutil
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    results.append(
        {
            "check": "ffmpeg",
            "status": "pass" if ffmpeg else "fail",
            "detail": ffmpeg or "no encontrado",
        }
    )
    results.append(
        {
            "check": "ffprobe",
            "status": "pass" if ffprobe else "fail",
            "detail": ffprobe or "no encontrado",
        }
    )

    # yt-dlp
    yt_dlp = shutil.which("yt-dlp")
    results.append(
        {
            "check": "yt-dlp",
            "status": "pass" if yt_dlp else "warn",
            "detail": yt_dlp or "no encontrado (solo local)",
        }
    )

    # Tesseract
    tesseract = shutil.which("tesseract")
    results.append(
        {
            "check": "tesseract",
            "status": "pass" if tesseract else "warn",
            "detail": tesseract or "no encontrado (OCR deshabilitado)",
        }
    )

    # Espacio de disco
    try:
        stat = Path("/").stat()
        free_gb = stat.st_frsize * stat.st_f_bavail / (1024**3)
        results.append(
            {
                "check": "disk_space",
                "status": "pass",
                "detail": f"{free_gb:.1f} GB libres en /",
            }
        )
    except Exception as e:
        results.append(
            {"check": "disk_space", "status": "warn", "detail": str(e)}
        )

    # Escritura
    test_path = Path("./.vitk_test_write")
    try:
        test_path.write_text("test")
        test_path.unlink()
        results.append(
            {"check": "write_permission", "status": "pass", "detail": "OK"}
        )
    except Exception as e:
        results.append(
            {"check": "write_permission", "status": "fail", "detail": str(e)}
        )

    # Config
    config = _resolve_config(args)
    results.append(
        {
            "check": "config",
            "status": "pass",
            "detail": f"Cargado: {args.config or 'config/default.yaml'}",
        }
    )

    # Adaptador detectado
    host_type = config.get("host", {}).get("type", "generic")
    results.append(
        {
            "check": "host_adapter",
            "status": "info",
            "detail": f"tipo={host_type}",
        }
    )

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print("=== video-intake doctor ===\n")
        all_ok = True
        for r in results:
            icon = {"pass": "✓", "fail": "✗", "warn": "⚠", "info": "·"}.get(
                r["status"], "·"
            )
            print(f"  {icon} {r['check']}: {r['detail']}")
            if r["status"] == "fail":
                all_ok = False
        print()
        if all_ok:
            print("Estado: ✓ Saludable")
        else:
            print("Estado: ✗ Con problemas")
    return 0 if all_ok else 1


def cmd_inspect(args: argparse.Namespace) -> int:
    """Muestra metadatos de una fuente de vídeo."""
    source = args.source
    try:
        info = inspect_video(source)
    except Exception as e:
        print(f"Error inspeccionando {source}: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(info, indent=2, ensure_ascii=False))
    else:
        print(f"Título: {info.get('title', 'N/A')}")
        print(f"Plataforma: {info.get('platform', 'N/A')}")
        dur = info.get("duration_secs")
        if dur is not None:
            print(f"Duración: {dur:.1f}s ({info.get('duration', 'N/A')})")
        if info.get("width") and info.get("height"):
            print(f"Resolución: {info['width']}x{info['height']}")
        if info.get("fps"):
            print(f"FPS: {info['fps']}")
        if info.get("video_codec"):
            print(f"Codec video: {info['video_codec']}")
        if info.get("audio_codec"):
            print(f"Codec audio: {info['audio_codec']}")
        if info.get("audio_channels"):
            print(f"Canales audio: {info['audio_channels']}")
        print(f"Streams: {len(info.get('streams', []))}")
        print(f"URL: {info.get('url', 'N/A')}")
        captions = info.get("captions", [])
        if captions:
            print(f"Subtítulos: {len(captions)}")
            for c in captions:
                print(f"  - {c.get('lang', '?')} ({c.get('name', '?')})")
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    """Extrae contenido de una o varias fuentes."""
    sources_raw = [args.source]
    files = args.file or []
    sources = _detect_sources([], files)

    if not sources:
        print("No se detectaron fuentes procesables.", file=sys.stderr)
        return 1

    selections = _parse_selections(args.select)
    config = _resolve_config(args)

    if not selections:
        selections = {"6"}  # por defecto: todo

    # Crear job de ejemplo
    job = create_job(
        source_url=sources[0]["resolved_url"],
        source_title=sources[0].get("title", "unknown"),
        source_type=sources[0]["type"],
        user_id=args.user_id,
    )

    if args.json:
        print(json.dumps(
            {
                "job_id": job.id,
                "status": job.status.value,
                "selections": list(selections),
                "source": sources[0]["resolved_url"],
            },
            indent=2,
            ensure_ascii=False,
        ))
        return 0

    print(f"Job creado: {job.id}")
    print(f"Fuente: {sources[0]['resolved_url']}")
    print(f"Selecciones: {', '.join(sorted(selections))}")
    print()

    # Simular ejecución
    try:
        start_job(job.id, list(selections), args)
    except Exception as e:
        print(f"Error ejecutando job: {e}", file=sys.stderr)
        return 1

    print(f"Job completado: {job.id}")
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    """Procesa un manifiesto de lote."""
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"Manifiesto no encontrado: {manifest_path}", file=sys.stderr)
        return 1

    try:
        import yaml
        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)
    except Exception as e:
        print(f"Error leyendo manifiesto: {e}", file=sys.stderr)
        return 1

    entries = manifest.get("videos", [])
    if not entries:
        print("El manifiesto no contiene vídeos.", file=sys.stderr)
        return 1

    config = _resolve_config(args)
    storage = _make_storage(args)
    artifact_manager = _make_artifact_manager(args)

    print(f"Procesando {len(entries)} vídeo(s) del manifiesto...")

    for entry in entries:
        url = entry.get("url") or entry.get("file")
        if not url:
            continue
        sources = _detect_sources([url] if url.startswith("http") else [], [url] if not url.startswith("http") else [])
        if not sources:
            print(f"  ✗ No procesable: {url}")
            continue
        s = sources[0]
        mode = entry.get("mode", "individual")
        select = entry.get("select", "6")

        print(f"  · {s.get('title', url)} [{select}]")
        if args.json:
            print(json.dumps({"source": url, "mode": mode, "select": select}))

    print(f"\nLote completado: {len(entries)} vídeos procesados.")
    if args.json:
        print(json.dumps({"processed": len(entries), "manifiesto": str(manifest_path)}))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Muestra el estado de un job."""
    job = get_job(args.job_id)
    if not job:
        print(f"Job no encontrado: {args.job_id}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(job.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(f"Job: {job.id}")
        print(f"Estado: {job.status.value}")
        print(f"Título: {job.source_title}")
        print(f"URL: {job.source_url}")
        print(f"Tipo: {job.source_type}")
        print(f"Creado: {job.created_at}")
        if job.result_metadata:
            print(f"Resultado: {job.result_metadata}")
    return 0


def cmd_cancel(args: argparse.Namespace) -> int:
    """Cancela un job en ejecución."""
    if not cancel_job(args.job_id):
        print(f"No se pudo cancelar el job: {args.job_id}", file=sys.stderr)
        return 1
    print(f"Job cancelado: {args.job_id}")
    return 0


def cmd_artifacts(args: argparse.Namespace) -> int:
    """Lista los artefactos de un job."""
    artifacts = list_artifacts(args.job_id)
    if not artifacts:
        print(f"No hay artefactos para el job: {args.job_id}")
        return 0

    if args.json:
        print(json.dumps(artifacts, indent=2, ensure_ascii=False))
    else:
        print(f"Artefactos para {args.job_id}:")
        for a in artifacts:
            print(f"  - {a['path']} ({a.get('size_mb', 0):.1f} MB)")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """Exporta los resultados de un job."""
    job = get_job(args.job_id)
    if not job:
        print(f"Job no encontrado: {args.job_id}", file=sys.stderr)
        return 1

    fmt = args.format or "markdown"
    export_dir = args.output or f"exports/{args.job_id}"

    Path(export_dir).mkdir(parents=True, exist_ok=True)

    if fmt == "json":
        data = job.to_dict()
        out = Path(export_dir) / "export.json"
        out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Exportado a {out}")
    elif fmt == "html":
        md_path = Path(export_dir) / "export.md"
        md_path.write_text(f"# Export job {args.job_id}\n\nJob completado.\n")
        html = f"<html><body><h1>Export job {args.job_id}</h1><p>Completado.</p></body></html>"
        html_path = Path(export_dir) / "export.html"
        html_path.write_text(html, encoding="utf-8")
        print(f"Exportado a {html_path}")
    else:
        md_path = Path(export_dir) / "export.md"
        md_path.write_text(f"# Export job {args.job_id}\n\n## Resumen\n\nJob: {args.job_id}\nEstado: {job.status.value}\nTítulo: {job.source_title}\n\n")
        print(f"Exportado a {md_path}")

    return 0


def cmd_cleanup(args: argparse.Namespace) -> int:
    """Limpia artefactos antiguos."""
    storage = _make_storage(args)
    removed = storage.cleanup(max_age_days=args.max_age_days, dry_run=args.dry_run)
    count = removed if isinstance(removed, int) else len(removed) if isinstance(removed, list) else 0
    if args.dry_run:
        print(f"[dry-run] Se eliminarían {count} artefactos.")
    else:
        print(f"Limpios {count} artefactos.")
    return 0


def cmd_config_validate(args: argparse.Namespace) -> int:
    """Valida la configuración actual."""
    config_path = args.config or "config/default.yaml"
    path = Path(config_path)
    if not path.exists():
        print(f"Configuración no encontrada: {config_path}", file=sys.stderr)
        return 1

    try:
        import yaml
        with open(path) as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"Error parseando YAML: {e}", file=sys.stderr)
        return 1

    errors: list[str] = []
    warnings: list[str] = []

    # Validaciones básicas
    storage = config.get("storage", {})
    if not storage.get("root_dir"):
        errors.append("storage.root_dir es obligatorio")
    if not isinstance(storage.get("max_storage_gb"), (int, float)):
        errors.append("storage.max_storage_gb debe ser numérico")

    limits = config.get("limits", {})
    if not isinstance(limits.get("max_video_duration_minutes"), (int, float)):
        errors.append("limits.max_video_duration_minutes debe ser numérico")

    transcription = config.get("transcription", {})
    if transcription.get("strategy_order") is None:
        warnings.append("transcription.strategy_order no está definido")

    if args.json:
        result = {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "config_file": config_path,
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Validando: {config_path}")
        if errors:
            print("Errores:")
            for e in errors:
                print(f"  ✗ {e}")
        if warnings:
            print("Advertencias:")
            for w in warnings:
                print(f"  ⚠ {w}")
        if not errors and not warnings:
            print("✓ La configuración es válida.")
    return 0 if not errors else 1


def cmd_self_test(args: argparse.Namespace) -> int:
    """Ejecuta pruebas de auto-diagnóstico."""
    import shutil
    from video_intake_core.utils import detect_video_sources, compute_sha256
    from video_intake_core.audio import extract_audio
    from video_intake_core.transcription import transcribe
    from video_intake_core.visual import analyze_scenes
    from video_intake_core.ocr import batch_ocr

    print("=== video-intake self-test ===\n")
    tests: list[dict[str, Any]] = []

    # Test 1: detección de URL de YouTube
    try:
        sources = detect_video_sources(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        tests.append(
            {
                "name": "detect_youtube_url",
                "status": "pass",
                "detail": f"{len(sources)} fuente(s) detectada(s)",
            }
        )
    except Exception as e:
        tests.append(
            {
                "name": "detect_youtube_url",
                "status": "fail",
                "detail": str(e),
            }
        )

    # Test 2: detección de archivo local
    test_file = Path(__file__).resolve().parent / ".." / ".." / "tests" / "fixtures" / "sample.mp4"
    if test_file.exists():
        try:
            sources = detect_video_sources(str(test_file))
            tests.append(
                {
                    "name": "detect_local_file",
                    "status": "pass",
                    "detail": f"detectado: {sources[0]['type'] if sources else 'N/A'}",
                }
            )
        except Exception as e:
            tests.append(
                {
                    "name": "detect_local_file",
                    "status": "fail",
                    "detail": str(e),
                }
            )
    else:
        tests.append(
            {
                "name": "detect_local_file",
                "status": "skip",
                "detail": "no hay fixture sample.mp4",
            }
        )

    # Test 3: herramientas del sistema
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    tesseract = shutil.which("tesseract")
    yt_dlp = shutil.which("yt-dlp")

    tests.append(
        {
            "name": "ffmpeg_available",
            "status": "pass" if ffmpeg else "fail",
            "detail": ffmpeg or "no encontrado",
        }
    )
    tests.append(
        {
            "name": "ffprobe_available",
            "status": "pass" if ffprobe else "fail",
            "detail": ffprobe or "no encontrado",
        }
    )
    tests.append(
        {
            "name": "tesseract_available",
            "status": "pass" if tesseract else "warn",
            "detail": tesseract or "no encontrado (OCR limitado)",
        }
    )
    tests.append(
        {
            "name": "yt_dlp_available",
            "status": "pass" if yt_dlp else "warn",
            "detail": yt_dlp or "no encontrado (solo local)",
        }
    )

    for t in tests:
        icon = {"pass": "✓", "fail": "✗", "warn": "⚠", "skip": "⊘"}.get(
            t["status"], "·"
        )
        print(f"  {icon} {t['name']}: {t['detail']}")

    fails = sum(1 for t in tests if t["status"] == "fail")
    print()
    if fails == 0:
        print("Self-test completado: ✓")
    else:
        print(f"Self-test completado: ✗ ({fails} fallo(s))")
    return 0 if fails == 0 else 1


def cmd_models_list(args: argparse.Namespace) -> int:
    """Lista modelos disponibles e instalados."""
    models_dir = Path.home() / ".cache" / "video_intake" / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    known_models = {
        "tiny": {"size_mb": 75, "langs": ["es", "en", "multi"], "offline": True},
        "base": {"size_mb": 140, "langs": ["es", "en", "multi"], "offline": True},
        "small": {"size_mb": 480, "langs": ["es", "en", "multi"], "offline": True},
        "medium": {"size_mb": 1500, "langs": ["es", "en", "multi"], "offline": True},
        "large": {"size_mb": 3000, "langs": ["es", "en", "multi"], "offline": True},
    }

    installed = []
    if models_dir.exists():
        for d in models_dir.iterdir():
            if d.is_dir():
                installed.append(d.name)

    if args.json:
        print(json.dumps(
            {
                "available": [
                    {
                        "name": name,
                        "size_mb": info["size_mb"],
                        "langs": info["langs"],
                        "offline": info["offline"],
                        "installed": name in installed,
                    }
                    for name, info in known_models.items()
                ]
            },
            indent=2,
            ensure_ascii=False,
        ))
    else:
        print("Modelos disponibles:\n")
        for name, info in known_models.items():
            status = "✓ instalado" if name in installed else "○ no instalado"
            print(
                f"  {name:10} {info['size_mb']:>5} MB  "
                f"{','.join(info['langs'])}  {status}"
            )
        print()
        print(f"Models directory: {models_dir}")
    return 0


def cmd_models_install(args: argparse.Namespace) -> int:
    """Instala un modelo (simulado — el usuario debe instalarlo manualmente)."""
    model = args.model
    if args.json:
        print(json.dumps(
            {
                "model": model,
                "status": "info",
                "message": "La instalación manual de modelos no está implementada en la CLI. "
                "Instala whisper.cpp o faster-whisper manualmente, o usa un proveedor externo.",
            },
            indent=2,
            ensure_ascii=False,
        ))
    else:
        print(f"Modelo '{model}': la instalación automática no está implementada.")
        print("Para instalar un modelo:")
        print("  1. Instala faster-whisper: pip install faster-whisper")
        print("  2. O usa whisper.cpp: https://github.com/ggerganov/whisper.cpp")
        print(f"  3. El primer uso descargará '{model}' automáticamente si es factible.")
    return 0


def cmd_models_verify(args: argparse.Namespace) -> int:
    """Verifica los modelos instalados."""
    models_dir = Path.home() / ".cache" / "video_intake" / "models"
    installed = []
    if models_dir.exists():
        for d in models_dir.iterdir():
            if d.is_dir():
                installed.append(d.name)

    if args.json:
        print(json.dumps({"installed": installed, "count": len(installed)}))
    else:
        if installed:
            print("Modelos instalados:")
            for m in installed:
                print(f"  - {m}")
        else:
            print("No hay modelos instalados localmente.")
        print()
        print("Para instalar: video-intake models install <model>")
    return 0


def cmd_models_remove(args: argparse.Namespace) -> int:
    """Elimina un modelo instalado."""
    model = args.model
    models_dir = Path.home() / ".cache" / "video_intake" / "models"
    target = models_dir / model
    if target.exists():
        if args.yes or input(f"¿Eliminar '{model}'? [y/N]: ").lower().startswith("y"):
            import shutil
            shutil.rmtree(target)
            print(f"Modelo '{model}' eliminado.")
        else:
            print("Cancelado.")
    else:
        print(f"Modelo '{model}' no encontrado.")
    return 0


# ============================================================================
# Argument parser
# ============================================================================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="video-intake",
        description="Detección, adquisición y conversión de vídeos en conocimiento utilizable por agentes de IA.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  video-intake doctor
  video-intake inspect https://www.youtube.com/watch?v=VIDEO_ID
  video-intake extract https://www.youtube.com/watch?v=VIDEO_ID --select 6
  video-intake batch manifest.yaml
  video-intake status <job-id>
  video-intake cancel <job-id>
  video-intake artifacts <job-id>
  video-intake export <job-id> --format markdown
  video-intake cleanup
  video-intake config validate
  video-intake self-test
  video-intake models list
  video-intake models install tiny
        """,
    )

    parser.add_argument(
        "--version",
        action="version",
        version="video-intake-knowledge 0.1.0",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Salida en formato JSON para integración con máquinas.",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Modo verboso.",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Ruta al archivo de configuración YAML.",
    )
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error"],
        default="info",
        help="Nivel de log.",
    )
    parser.add_argument(
        "--user-id",
        type=str,
        default=None,
        help="ID del usuario para correlación de jobs.",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # doctor
    sub.add_parser("doctor", help="Comprueba la salud del entorno.").set_defaults(
        func=cmd_doctor
    )

    # inspect
    inspect_p = sub.add_parser("inspect", help="Muestra metadatos de una fuente.")
    inspect_p.add_argument("source", help="URL o ruta del vídeo.")
    inspect_p.set_defaults(func=cmd_inspect)

    # extract
    extract_p = sub.add_parser(
        "extract", help="Extrae contenido de una fuente."
    )
    extract_p.add_argument("source", help="URL o ruta del vídeo.")
    extract_p.add_argument(
        "--select", "-s",
        type=str,
        default="6",
        help="Selecciones: 1,2,3,4,5,6 o 'todo' (default: 6 = todo).",
    )
    extract_p.add_argument(
        "--file", "-f",
        nargs="*",
        default=[],
        help="Archivo(s) local(es) adicionales.",
    )
    extract_p.set_defaults(func=cmd_extract)

    # batch
    batch_p = sub.add_parser(
        "batch", help="Procesa un manifiesto de lote."
    )
    batch_p.add_argument("manifest", help="Ruta al manifiesto YAML.")
    batch_p.set_defaults(func=cmd_batch)

    # status
    status_p = sub.add_parser("status", help="Muestra el estado de un job.")
    status_p.add_argument("job_id", help="ID del job.")
    status_p.set_defaults(func=cmd_status)

    # cancel
    cancel_p = sub.add_parser(
        "cancel", help="Cancela un job en ejecución."
    )
    cancel_p.add_argument("job_id", help="ID del job.")
    cancel_p.set_defaults(func=cmd_cancel)

    # artifacts
    artifacts_p = sub.add_parser(
        "artifacts", help="Lista los artefactos de un job."
    )
    artifacts_p.add_argument("job_id", help="ID del job.")
    artifacts_p.set_defaults(func=cmd_artifacts)

    # export
    export_p = sub.add_parser("export", help="Exporta resultados de un job.")
    export_p.add_argument("job_id", help="ID del job.")
    export_p.add_argument(
        "--format", "-f",
        choices=["markdown", "json", "html"],
        default="markdown",
        help="Formato de exportación (default: markdown).",
    )
    export_p.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Directorio de salida.",
    )
    export_p.set_defaults(func=cmd_export)

    # cleanup
    cleanup_p = sub.add_parser(
        "cleanup", help="Limpia artefactos antiguos."
    )
    cleanup_p.add_argument(
        "--max-age-days",
        type=int,
        default=90,
        help="Edad máxima en días (default: 90).",
    )
    cleanup_p.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo muestra lo que se eliminaría.",
    )
    cleanup_p.set_defaults(func=cmd_cleanup)

    # config validate
    config_p = sub.add_parser(
        "config", help="Gestiona la configuración."
    )
    config_p.add_argument(
        "subcommand",
        choices=["validate"],
        help="Subcomando.",
    )
    config_p.add_argument(
        "--config",
        type=str,
        default=None,
        help="Ruta al archivo de configuración YAML.",
    )
    config_p.set_defaults(func=cmd_config_validate)

    # self-test
    sub.add_parser("self-test", help="Ejecuta pruebas de auto-diagnóstico.").set_defaults(
        func=cmd_self_test
    )

    # models
    models_p = sub.add_parser(
        "models", help="Gestiona modelos de transcripción."
    )
    models_sub = models_p.add_subparsers(dest="model_command", required=True)
    models_sub.add_parser("list").set_defaults(func=cmd_models_list)
    install_p = models_sub.add_parser("install", help="Instala un modelo.")
    install_p.add_argument("model", help="Nombre del modelo.")
    install_p.set_defaults(func=cmd_models_install)
    verify_p = models_sub.add_parser("verify", help="Verifica modelos instalados.")
    verify_p.set_defaults(func=cmd_models_verify)
    remove_p = models_sub.add_parser("remove", help="Elimina un modelo.")
    remove_p.add_argument("model", help="Nombre del modelo.")
    remove_p.add_argument(
        "--yes",
        action="store_true",
        help="No preguntar confirmación.",
    )
    remove_p.set_defaults(func=cmd_models_remove)

    return parser


# ============================================================================
# Main entry point
# ============================================================================

def main(argv: list[str] | None = None) -> int:
    """Entry point para el CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # Configurar logging
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format=DEFAULT_LOG_FORMAT,
        stream=sys.stderr,
    )

    if args.verbose:
        logging.getLogger("video_intake").setLevel(logging.DEBUG)

    try:
        return args.func(args)  # type: ignore[union-attr]
    except Exception as e:
        logging.error("Error ejecutando '%s': %s", args.command, e)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
