import re
from pathlib import Path

cli_dir = Path("packages/video_intake_core/cli")
init_file = cli_dir / "__init__.py"
content = init_file.read_text()

# Extract functions using regex (match `def cmd_X(...) -> int:` to the end or next `def cmd_`)
functions = {}
matches = list(re.finditer(r"^def cmd_(\w+)\((.*?)\) -> int:\n(.*?)(?=\n^def cmd_|^def build_parser|^# ======)", content, flags=re.MULTILINE | re.DOTALL))
for m in matches:
    name = m.group(1)
    func_code = m.group(0)
    functions[name] = func_code

# We know cmd_doctor, cmd_cleanup, cmd_artifacts, cmd_export, cmd_extract, cmd_status
# cmd_models_list, cmd_models_install, cmd_models_verify, cmd_models_remove, cmd_config_validate
# are all duplicates.

# Create inspect_cmd.py
(cli_dir / "inspect_cmd.py").write_text(f'''"""Inspect command for video-intake-knowledge."""
from __future__ import annotations
import argparse
import json
import sys
from video_intake_core.inspection import inspect_video as _inspect_video

def run_inspect(args: argparse.Namespace) -> int:
{functions["inspect"].split("def cmd_inspect(args: argparse.Namespace) -> int:")[1]}

def inspect_command(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser = subparsers.add_parser("inspect", help="Muestra metadatos de una fuente.")
    parser.add_argument("source", help="URL o ruta del vídeo.")
    parser.set_defaults(func=run_inspect)
    return parser
''')

# Create cancel.py
(cli_dir / "cancel.py").write_text(f'''"""Cancel command for video-intake-knowledge."""
from __future__ import annotations
import argparse
import sys
from video_intake_core.jobs import cancel_job

def run_cancel(args: argparse.Namespace) -> int:
{functions["cancel"].split("def cmd_cancel(args: argparse.Namespace) -> int:")[1]}

def cancel_command(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser = subparsers.add_parser("cancel", help="Cancela un job en ejecución.")
    parser.add_argument("job_id", help="ID del job.")
    parser.set_defaults(func=run_cancel)
    return parser
''')

# Create self_test.py
(cli_dir / "self_test.py").write_text(f'''"""Self-test command for video-intake-knowledge."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

def run_self_test(args: argparse.Namespace) -> int:
{functions["self_test"].split("def cmd_self_test(args: argparse.Namespace) -> int:")[1]}

def self_test_command(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser = subparsers.add_parser("self-test", help="Ejecuta pruebas de auto-diagnóstico.")
    parser.set_defaults(func=run_self_test)
    return parser
''')

# Update __init__.py build_parser
new_build_parser = '''
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
'''

# Delete all the old subparser additions and functions
content = re.sub(r"def cmd_.*?(?=def build_parser)", "", content, flags=re.MULTILINE | re.DOTALL)
content = re.sub(r"def build_parser\(\) -> argparse\.ArgumentParser:.*(?=# ============================================================================)", new_build_parser + "\n\n", content, flags=re.MULTILINE | re.DOTALL)

# Delete unneeded lazy imports, because the functions above are gone
content = re.sub(r"def _get_.*?\n    return .*?\n\n\n", "", content, flags=re.MULTILINE | re.DOTALL)

# Rewrite __init__.py
init_file.write_text(content)

