import re

# I'll restore cmd_extract and cmd_config_validate to what they were.
# Actually, I can just grab them from git.
import subprocess
from pathlib import Path

out = subprocess.check_output(["git", "show", "HEAD:packages/video_intake_core/cli/__init__.py"], text=True)

# Extract original cmd_extract
m_ext = re.search(r"^def cmd_extract\(args: argparse\.Namespace\) -> int:\n(.*?)(?=\n^def cmd_)", out, flags=re.MULTILINE | re.DOTALL)
cmd_extract_body = m_ext.group(1)

extract_file = Path("packages/video_intake_core/cli/extract.py")
extract_content = f'''"""Extract command for video-intake-knowledge."""
from __future__ import annotations
import argparse
import sys
import json
from pathlib import Path
from video_intake_core.cli import _detect_sources, _resolve_config

def run_extraction(args: argparse.Namespace) -> int:
{cmd_extract_body}

def extract_command(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    extract_p = subparsers.add_parser("extract", help="Extrae contenido de una fuente.")
    extract_p.add_argument("source", help="URL o ruta del vídeo.")
    extract_p.add_argument("--select", "-s", type=str, default="6", help="Selecciones: 1,2,3,4,5,6 o 'todo' (default: 6 = todo).")
    extract_p.add_argument("--file", "-f", nargs="*", default=[], help="Archivo(s) local(es) adicionales.")
    extract_p.set_defaults(func=run_extraction)
    return extract_p
'''
extract_file.write_text(extract_content)

# Extract original cmd_config_validate
m_cfg = re.search(r"^def cmd_config_validate\(args: argparse\.Namespace\) -> int:\n(.*?)(?=\n^def cmd_)", out, flags=re.MULTILINE | re.DOTALL)
cmd_config_validate_body = m_cfg.group(1)

config_file = Path("packages/video_intake_core/cli/config_cmd.py")
config_content = f'''"""Config validate command for video-intake-knowledge."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

def run_config_validate(args: argparse.Namespace) -> int:
{cmd_config_validate_body}

def config_validate_command(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    config_p = subparsers.add_parser("config", help="Gestiona la configuración.")
    config_p.add_argument("subcommand", choices=["validate"], help="Subcomando.")
    config_p.add_argument("--config", type=str, default=None, help="Ruta al archivo de configuración YAML.")
    config_p.set_defaults(func=run_config_validate)
    return config_p
'''
config_file.write_text(config_content)

