import re
from pathlib import Path

# 1. Update test_orchestrator_execution.py
test_file = Path("tests/unit/test_orchestrator_execution.py")
test_content = test_file.read_text()

# Replace the imports
new_imports = """
from video_intake_core.cli.artifacts import show_artifacts as cmd_artifacts
from video_intake_core.cli.cancel import run_cancel as cmd_cancel
from video_intake_core.cli.cleanup import run_storage_cleanup as cmd_cleanup
from video_intake_core.cli.config_cmd import run_config_validate as cmd_config_validate
from video_intake_core.cli.doctor import run_doctor as cmd_doctor
from video_intake_core.cli.export import run_export as cmd_export
from video_intake_core.cli.extract import run_extraction as cmd_extract
from video_intake_core.cli.inspect_cmd import run_inspect as cmd_inspect
from video_intake_core.cli.models import models_list_command as cmd_models_list, models_verify_command as cmd_models_verify
from video_intake_core.cli.self_test import run_self_test as cmd_self_test
from video_intake_core.cli.status import run_status as cmd_status
from video_intake_core.batch import cmd_batch
"""

# Regex to replace the from video_intake_core.cli import (...)
test_content = re.sub(
    r"from video_intake_core\.cli import \([\s\S]*?\)",
    new_imports.strip(),
    test_content
)
test_file.write_text(test_content)

