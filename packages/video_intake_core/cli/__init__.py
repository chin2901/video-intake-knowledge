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

logger = logging.getLogger("video_intake")
DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


# ============================================================================
# Lazy imports - only import when needed
# ============================================================================


# ============================================================================
# Helpers
# ============================================================================

def _resolve_config(args: argparse.Namespace) -> dict[str, Any]:
    """Carga la configuración de la ruta indicada o del default."""
    config_path = getattr(args, "config", None) or "config/default.yaml"
    from video_intake_core.policies import PolicyResolver
    resolver = PolicyResolver(config_path=str(config_path))
    return resolver.config


def _make_storage(args: argparse.Namespace) -> StorageManager:
    config = _resolve_config(args)
    root = config.get("storage", {}).get("root_dir", "./artifacts")
    retention = config.get("storage", {}).get("artifact_retention_days", 90)
    max_gb = config.get("storage", {}).get("max_storage_gb", 100)
    from video_intake_core.storage import StorageManager as StorageManagerClass
    return StorageManagerClass(storage_root=root, retention_days=retention, max_storage_gb=max_gb)


def _make_artifact_manager(args: argparse.Namespace) -> ArtifactManager:
    from video_intake_core.artifacts import ArtifactManager as ArtifactManagerClass
    return ArtifactManagerClass(storage=_make_storage(args))


def _make_memory(args: argparse.Namespace) -> MemoryProvider:
    import os
    config = _resolve_config(args)
    default_provider = config.get("memory", {}).get("default_provider", "local")
    from video_intake_core.memory import MemoryProvider, LocalSQLiteMemoryProvider
    default_db = Path.home() / ".video-intake" / "memory.db"
    raw_path = getattr(args, "db_path", None) or os.environ.get("VITK_MEMORY_DB") or config.get("memory", {}).get("db_path") or str(default_db)
    db_path = Path(os.path.expanduser(str(raw_path)))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return LocalSQLiteMemoryProvider(db_path=str(db_path))


def _detect_sources(urls: list[str], files: list[str]) -> list[dict[str, Any]]:
    """Combina detección de URLs y archivos locales."""
    from video_intake_core.acquisition import detect_video_sources, SourceType
    sources: list[dict[str, Any]] = []

    def _to_dict(item: Any, original: str) -> dict[str, Any]:
        if isinstance(item, dict):
            return item
        source_type = getattr(item, "source_type", "url")
        url_val = getattr(item, "url", original)
        resolved = getattr(item, "resolved_path", None) or url_val
        title_val = getattr(item, "title", None) or Path(url_val).stem
        return {
            "type": source_type,
            "original_input": original,
            "resolved_url": resolved,
            "platform": str(source_type),
            "title": title_val,
            "is_local": source_type == "local",
        }

    for url in urls:
        detected = detect_video_sources(url)
        if detected:
            for s in detected:
                sources.append(_to_dict(s, url))
        else:
            sources.append({
                "type": "url",
                "original_input": url,
                "resolved_url": url,
                "platform": "generic",
                "title": "video",
                "is_local": False,
            })
    for f in files:
        p = Path(f)
        sources.append({
            "type": "local",
            "original_input": str(p),
            "resolved_url": str(p.resolve()) if p.exists() else str(p),
            "platform": "local",
            "title": p.stem,
            "is_local": True,
        })
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="video-intake",
        description="Detección, adquisición y conversión de vídeos en conocimiento utilizable por agentes de IA.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version="video-intake-knowledge 0.1.0")
    parser.add_argument("--json", action="store_true", help="Salida en formato JSON para integración con máquinas.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Modo verboso.")
    parser.add_argument("--config", type=str, default=None, help="Ruta al archivo de configuración YAML.")
    parser.add_argument("--log-level", choices=["debug", "info", "warning", "error"], default="info", help="Nivel de log.")
    parser.add_argument("--user-id", type=str, default=None, help="ID del usuario para correlación de jobs.")

    sub = parser.add_subparsers(dest="command", required=True)

    from video_intake_core.cli.doctor import doctor_command
    doctor_command(sub)

    from video_intake_core.cli.inspect_cmd import inspect_command
    inspect_command(sub)

    from video_intake_core.cli.extract import extract_command
    extract_command(sub)

    # batch
    batch_p = sub.add_parser("batch", help="Procesa un manifiesto de lote.")
    batch_p.add_argument("manifest", help="Ruta al manifiesto YAML.")
    from video_intake_core.batch import cmd_batch
    batch_p.set_defaults(func=cmd_batch)

    from video_intake_core.cli.status import status_command
    status_command(sub)

    from video_intake_core.cli.cancel import cancel_command
    cancel_command(sub)

    from video_intake_core.cli.artifacts import artifacts_command
    artifacts_command(sub)

    from video_intake_core.cli.export import export_command
    export_command(sub)

    from video_intake_core.cli.cleanup import cleanup_command
    cleanup_command(sub)

    # config validate
    config_p = sub.add_parser("config", help="Gestiona la configuración.")
    config_p.add_argument("subcommand", choices=["validate"], help="Subcomando.")
    config_p.add_argument("--config", type=str, default=None, help="Ruta al archivo de configuración YAML.")
    from video_intake_core.cli.config_cmd import run_config_validate
    config_p.set_defaults(func=run_config_validate)

    from video_intake_core.cli.self_test import self_test_command
    self_test_command(sub)

    from video_intake_core.cli.models import models_command
    models_command(sub)

    from video_intake_core.cli.proposals import proposals_command
    proposals_command(sub)

    from video_intake_core.cli.memory import memory_command
    memory_command(sub)

    return parser


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
