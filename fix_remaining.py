import re
import subprocess
from pathlib import Path

out = subprocess.check_output(["git", "show", "HEAD:packages/video_intake_core/cli/__init__.py"], text=True)

def extract_func(name):
    m = re.search(f"^def cmd_{name}\\(args: argparse\\.Namespace\\) -> int:\n(.*?)(?=\n^def cmd_|\n# ====)", out, flags=re.MULTILINE | re.DOTALL)
    if not m:
        # Fallback to look until next def
        m = re.search(f"^def cmd_{name}\\(args: argparse\\.Namespace\\) -> int:\n(.*?)(?=\n^def )", out, flags=re.MULTILINE | re.DOTALL)
    return m.group(1) if m else ""

# status.py
status_body = extract_func("status")
if status_body:
    content = f'''"""Status command for video-intake-knowledge."""
from __future__ import annotations
import argparse
import sys
import json
from pathlib import Path
from video_intake_core.jobs import get_job

def run_status(args: argparse.Namespace) -> int:
{status_body}

def status_command(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    status_p = subparsers.add_parser("status", help="Muestra el estado de un job.")
    status_p.add_argument("job_id", help="ID del job.")
    status_p.set_defaults(func=run_status)
    return status_p
'''
    Path("packages/video_intake_core/cli/status.py").write_text(content)

# artifacts.py
artifacts_body = extract_func("artifacts")
if artifacts_body:
    content = f'''"""Artifacts command for video-intake-knowledge."""
from __future__ import annotations
import argparse
import sys
import json
from pathlib import Path
from video_intake_core.artifacts import list_artifacts

def show_artifacts(args: argparse.Namespace) -> int:
{artifacts_body}

def artifacts_command(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    artifacts_p = subparsers.add_parser("artifacts", help="Lista los artefactos de un job.")
    artifacts_p.add_argument("job_id", help="ID del job.")
    artifacts_p.set_defaults(func=show_artifacts)
    return artifacts_p
'''
    Path("packages/video_intake_core/cli/artifacts.py").write_text(content)

# export.py
export_body = extract_func("export")
if export_body:
    content = f'''"""Export command for video-intake-knowledge."""
from __future__ import annotations
import argparse
import sys
import json
from pathlib import Path
from video_intake_core.jobs import get_job

def run_export(args: argparse.Namespace) -> int:
{export_body}

def export_command(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    export_p = subparsers.add_parser("export", help="Exporta resultados de un job.")
    export_p.add_argument("job_id", help="ID del job.")
    export_p.add_argument("--format", "-f", choices=["markdown", "json", "html"], default="markdown", help="Formato de exportación (default: markdown).")
    export_p.add_argument("--output", "-o", type=str, default=None, help="Directorio de salida.")
    export_p.set_defaults(func=run_export)
    return export_p
'''
    Path("packages/video_intake_core/cli/export.py").write_text(content)

# cleanup.py
cleanup_body = extract_func("cleanup")
if cleanup_body:
    content = f'''"""Cleanup command for video-intake-knowledge."""
from __future__ import annotations
import argparse
import sys
from video_intake_core.cli import _make_storage

def run_storage_cleanup(args: argparse.Namespace) -> int:
{cleanup_body}

def cleanup_command(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    cleanup_p = subparsers.add_parser("cleanup", help="Limpia artefactos antiguos.")
    cleanup_p.add_argument("--max-age-days", type=int, default=90, help="Edad máxima en días (default: 90).")
    cleanup_p.add_argument("--dry-run", action="store_true", help="Solo muestra lo que se eliminaría.")
    cleanup_p.set_defaults(func=run_storage_cleanup)
    return cleanup_p
'''
    Path("packages/video_intake_core/cli/cleanup.py").write_text(content)

# doctor.py (Wait, cmd_doctor also had special things!)
doctor_body = extract_func("doctor")
if doctor_body:
    content = f'''"""Doctor command for video-intake-knowledge."""
from __future__ import annotations
import argparse
import sys
import json
from pathlib import Path
from video_intake_core.cli import _resolve_config

def run_doctor(args: argparse.Namespace) -> int:
{doctor_body}

def doctor_command(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    doctor_p = subparsers.add_parser("doctor", help="Comprueba la salud del entorno.")
    doctor_p.set_defaults(func=run_doctor)
    return doctor_p
'''
    Path("packages/video_intake_core/cli/doctor.py").write_text(content)

