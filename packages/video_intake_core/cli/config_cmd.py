"""Config validate command for video-intake-knowledge."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def run_config_validate(args: argparse.Namespace) -> int:
    """Valida la configuración actual."""
    config_path = getattr(args, "config", None) or "config/default.yaml"
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



def config_validate_command(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    config_p = subparsers.add_parser("config", help="Gestiona la configuración.")
    config_p.add_argument("subcommand", choices=["validate"], help="Subcomando.")
    config_p.add_argument("--config", type=str, default=None, help="Ruta al archivo de configuración YAML.")
    config_p.set_defaults(func=run_config_validate)
    return config_p
