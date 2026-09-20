"""
Unit tests for the video-intake-knowledge CLI.

Focused on CLI parsing, command handling, and edge cases.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


# =============================================================================
# CLI structure tests
# =============================================================================

class TestCLIStructure:
    """Test that the CLI module exists and has expected attributes."""

    def test_cli_module_exists(self):
        """The CLI module is importable."""
        import video_intake_core.cli
        assert video_intake_core.cli is not None

    def test_cli_version(self):
        """The CLI module has a version."""
        import video_intake_core
        assert hasattr(video_intake_core, "__version__")

    def test_cli_doctor_exists(self):
        """The doctor command exists in CLI."""
        from video_intake_core.cli.doctor import (
            doctor_checks,
            run_doctor,
        )
        assert callable(run_doctor)

    def test_cli_cleanup_exists(self):
        """The cleanup command exists in CLI."""
        from video_intake_core.cli.cleanup import (
            cleanup_command,
            run_storage_cleanup,
        )
        assert callable(cleanup_command)

    def test_cli_extract_exists(self):
        """The extract command exists in CLI."""
        from video_intake_core.cli.extract import (
            extract_command,
            run_extraction,
        )
        assert callable(extract_command)

    def test_cli_status_exists(self):
        """The status command exists in CLI."""
        from video_intake_core.cli.status import (
            status_command,
            run_status,
        )
        assert callable(status_command)

    def test_cli_artifacts_exists(self):
        """The artifacts command exists in CLI."""
        from video_intake_core.cli.artifacts import (
            artifacts_command,
            show_artifacts,
        )
        assert callable(artifacts_command)

    def test_cli_export_exists(self):
        """The export command exists in CLI."""
        from video_intake_core.cli.export import (
            export_command,
            run_export,
        )
        assert callable(export_command)

    def test_cli_proposals_exists(self):
        """The proposals command exists in CLI."""
        from video_intake_core.cli.proposals import (
            proposals_command,
            show_proposals,
        )
        assert callable(proposals_command)

    def test_cli_memory_exists(self):
        """The memory command exists in CLI."""
        from video_intake_core.cli.memory import (
            memory_command,
            show_memory,
        )
        assert callable(memory_command)

    def test_cli_config_exists(self):
        """The config command exists in CLI."""
        from video_intake_core.cli.config_cmd import (
            config_validate_command,
        )
        assert callable(config_validate_command)

    def test_cli_models_exists(self):
        """The models command exists in CLI."""
        from video_intake_core.cli.models import (
            models_list_command,
            models_install_command,
            models_verify_command,
        )
        assert callable(models_list_command)
        assert callable(models_install_command)
        assert callable(models_verify_command)


class TestCLIMenu:
    """Tests for the interactive menu parser."""

    def test_menu_parser_single_option(self):
        """Single option like '1' is parsed correctly."""
        from video_intake_core.cli.menu import parse_menu_selection

        result = parse_menu_selection("1")
        assert 1 in result

    def test_menu_parser_multiple_options(self):
        """Comma-separated options like '1,3,5' are parsed."""
        from video_intake_core.cli.menu import parse_menu_selection

        result = parse_menu_selection("1,3,5")
        assert 1 in result
        assert 3 in result
        assert 5 in result

    def test_menu_parser_space_separated(self):
        """Space-separated options like '1 3 5' are parsed."""
        from video_intake_core.cli.menu import parse_menu_selection

        result = parse_menu_selection("1 3 5")
        assert 1 in result
        assert 3 in result
        assert 5 in result

    def test_menu_parser_all(self):
        """'todo' or 'todos' selects all options."""
        from video_intake_core.cli.menu import parse_menu_selection

        result_todo = parse_menu_selection("todo")
        assert 1 in result_todo
        assert 2 in result_todo
        assert 3 in result_todo
        assert 4 in result_todo
        assert 5 in result_todo
        assert 6 in result_todo

        result_todos = parse_menu_selection("todos")
        assert 1 in result_todos
        assert 6 in result_todos

    def test_menu_parser_six(self):
        """'6' or 'todo' equivalent selects all."""
        from video_intake_core.cli.menu import parse_menu_selection

        result = parse_menu_selection("6")
        assert 1 in result
        assert 2 in result
        assert 3 in result
        assert 4 in result
        assert 5 in result
        assert 6 in result

    def test_menu_parser_cancel(self):
        """'0' or 'cancelar' cancels."""
        from video_intake_core.cli.menu import parse_menu_selection

        result_0 = parse_menu_selection("0")
        assert 0 in result_0

        result_cancelar = parse_menu_selection("cancelar")
        assert 0 in result_cancelar

    def test_menu_parser_invalid(self):
        """Invalid selections return False."""
        from video_intake_core.cli.menu import parse_menu_selection

        # Empty string
        assert parse_menu_selection("") is False
        # Invalid number
        assert parse_menu_selection("9") is False
        # Non-numeric garbage
        assert parse_menu_selection("xyz") is False


class TestCLIConfig:
    """Tests for CLI configuration handling."""

    def test_config_default_yaml_exists(self):
        """The default.yaml config file exists."""
        from pathlib import Path
        config_path = Path(__file__).parent.parent.parent / "config" / "default.yaml"
        assert config_path.exists()

    def test_config_offline_yaml_exists(self):
        """The offline.yaml config file exists."""
        from pathlib import Path
        config_path = Path(__file__).parent.parent.parent / "config" / "offline.yaml"
        assert config_path.exists()

    def test_config_low_cost_yaml_exists(self):
        """The low-cost.yaml config file exists."""
        from pathlib import Path
        config_path = Path(__file__).parent.parent.parent / "config" / "low-cost.yaml"
        assert config_path.exists()

    def test_config_production_yaml_exists(self):
        """The production.yaml config file exists."""
        from pathlib import Path
        config_path = Path(__file__).parent.parent.parent / "config" / "production.yaml"
        assert config_path.exists()

    def test_policy_resolve_default(self):
        """Policy can be resolved from default.yaml."""
        from video_intake_core.policies import resolve_policy
        from pathlib import Path

        config_path = Path(__file__).parent.parent.parent / "config" / "default.yaml"
        policy = resolve_policy(config_yaml=str(config_path))
        assert policy is not None
        assert policy.transcription.model in ("auto", "whisper", "none")

    def test_source_policy_resolve(self):
        """Source policy can be resolved from config."""
        from video_intake_core.policies import resolve_source_policy
        from pathlib import Path

        config_path = Path(__file__).parent.parent.parent / "config" / "default.yaml"
        policy = resolve_source_policy("youtube", config_yaml=str(config_path))
        assert policy is not None


class TestCLIStorage:
    """Tests for CLI storage handling."""

    def test_storage_manager_exists(self):
        """The storage manager class exists."""
        from video_intake_core.storage import StorageManager
        assert StorageManager is not None

    def test_artifact_types_exist(self):
        """Artifact types are defined."""
        from video_intake_core.storage import ArtifactType, ArtifactKind
        assert ArtifactType.VIDEO is not None
        assert ArtifactType.AUDIO is not None
        assert ArtifactType.TRANSCRIPT is not None
        assert ArtifactType.OCR is not None
        assert ArtifactType.CONTEXT is not None
        assert ArtifactType.FRAMES is not None
        assert ArtifactKind.ORIGINAL is not None
        assert ArtifactKind.PROCESSED is not None
        assert ArtifactKind.TRANSCRIPT is not None
        assert ArtifactKind.CAPTION is not None


class TestCLIArtifacts:
    """Tests for artifact handling in CLI context."""

    def test_artifact_manager_exists(self):
        """The artifacts module exists."""
        from video_intake_core.artifacts import ArtifactManager
        assert ArtifactManager is not None

    def test_artifact_creation(self, tmp_path: Path):
        """Can create an artifact manager and register an artifact."""
        from video_intake_core.artifacts import ArtifactManager
        from video_intake_core.storage import ArtifactType, ArtifactKind
        from video_intake_core.jobs import JobManager, JobState
        from video_intake_core.acquisition import detect_video_sources

        import tempfile
        import os

        # Setup temp storage
        storage_dir = tmp_path / "storage"
        storage_dir.mkdir()
        job_db = tmp_path / "jobs.db"

        # Create job
        job_manager = JobManager(str(job_db))
        job = job_manager.create_job(
            video_path="http://example.com/test.mp4",
            source_type="local",
            selected_operations=["download"],
        )

        # Create artifact manager
        artifact_manager = ArtifactManager(str(storage_dir), str(job_db))

        # Verify artifact manager is usable
        assert artifact_manager.storage is not None

        # Verify storage directory structure exists
        assert (storage_dir / "jobs").exists()
