"""
Config validation command for video-intake-knowledge.

Validates configuration files.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


def run_config_validate(args: argparse.Namespace) -> int:
    """Execute the config validate command."""
    config_path = Path(args.config_file)

    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        if config is None:
            print(f"Config file is empty: {config_path}")
            return 1

        # Basic validation
        required_sections = [
            "transcription", "visual", "models", "security",
            "limits", "storage", "acquisition", "memory", "host"
        ]

        missing = [s for s in required_sections if s not in config]
        if missing:
            print(f"Warning: Missing config sections: {', '.join(missing)}")
        else:
            print("All required sections present.")

        # Check types
        errors = []
        if "limits" in config:
            limits = config["limits"]
            for key, expected_type in [
                ("max_video_duration_minutes", int),
                ("max_download_size_mb", int),
                ("max_batch_items", int),
                ("max_parallel_jobs", int),
                ("timeout_seconds", int),
            ]:
                if key in limits and not isinstance(limits[key], expected_type):
                    errors.append(f"limits.{key} should be {expected_type.__name__}")

        if errors:
            print("Validation errors:")
            for e in errors:
                print(f"  - {e}")
            return 1

        print(f"Config file '{config_path}' is valid!")
        return 0

    except yaml.YAMLError as e:
        print(f"YAML error: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def config_validate_command(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """Add the config validate subcommand to the parser."""
    parser = subparsers.add_parser("config", help="Validate configuration files")
    subparsers_config = parser.add_subparsers(dest="config_action", required=True)

    validate_parser = subparsers_config.add_parser("validate", help="Validate a config file")
    validate_parser.add_argument("config_file", help="Path to config YAML file")
    validate_parser.set_defaults(func=run_config_validate)

    return parser
