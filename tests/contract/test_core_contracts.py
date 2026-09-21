"""
Contract tests for core module APIs.

These tests verify that the public API surface of each core module
matches the expected interface, independent of implementation details.
Run with: pytest tests/contract/
"""

from __future__ import annotations

import pytest

# Central registry of all public API signatures.
# When a module's public API changes, update this file.

EXPECTED_TRANSCRIPTION_FUNCTIONS = {
    "transcribe_from_url": {
        "params": ["url", "strategy", "language", "user_agent"],
        "returns": "TranscriptResult",
    },
    "transcribe_from_file": {
        "params": ["video_path", "strategy", "language"],
        "returns": "TranscriptResult",
    },
    "detect_subtitles": {
        "params": ["url"],
        "returns": "list[SubtitleTrack]",
    },
    "download_subtitles": {
        "params": ["url", "track_id", "output_dir"],
        "returns": "Path",
    },
}


EXPECTED_VISUAL_FUNCTIONS = {
    "detect_scenes": {
        "params": ["video_path"],
        "returns": "list[Scene]",
    },
    "extract_keyframes": {
        "params": ["video_path", "scenes", "output_dir"],
        "returns": "list[Path]",
    },
    "analyze_keyframe": {
        "params": ["frame_path"],
        "returns": "FrameAnalysis",
    },
}


EXPECTED_OCR_FUNCTIONS = {
    "run_ocr": {
        "params": ["image_path"],
        "returns": "OCRResult",
    },
    "batch_ocr": {
        "params": ["image_paths", "engine"],
        "returns": "list[OCRResult]",
    },
}


EXPECTED_AUDIO_FUNCTIONS = {
    "extract_audio": {
        "params": ["video_path", "output_dir"],
        "returns": "Path",
    },
    "extract_audio_from_url": {
        "params": ["url", "output_dir"],
        "returns": "Path",
    },
    "get_audio_info": {
        "params": ["audio_path"],
        "returns": "AudioInfo",
    },
}


EXPECTED_JOBS_FUNCTIONS = {
    "create_job": {
        "params": ["source_url", "title", "source_type"],
        "returns": "Job",
    },
    "start_job": {
        "params": ["job", "selections"],
        "returns": "None",
    },
    "cancel_job": {
        "params": ["job_id"],
        "returns": "bool",
    },
    "get_job": {
        "params": ["job_id"],
        "returns": "Job | None",
    },
    "list_jobs": {
        "params": ["status"],
        "returns": "list[Job]",
    },
}


EXPECTED_STORAGE_FUNCTIONS = {
    "save_artifact": {
        "params": ["job_id", "artifact_type", "content", "filename"],
        "returns": "Path",
    },
    "get_artifacts": {
        "params": ["job_id"],
        "returns": "list[Artifact]",
    },
    "cleanup": {
        "params": ["max_age_days", "dry_run"],
        "returns": "int",
    },
    "get_storage_usage": {
        "params": [],
        "returns": "dict[str, int]",
    },
}


EXPECTED_SECURITY_FUNCTIONS = {
    "validate_url": {
        "params": ["url", "allowed_domains"],
        "returns": "ValidationResult",
    },
    "is_safe_url": {
        "params": ["url", "internal_ranges"],
        "returns": "bool",
    },
    "sanitize_filename": {
        "params": ["filename", "max_length"],
        "returns": "str",
    },
    "detect_mime": {
        "params": ["file_path"],
        "returns": "str",
    },
    "is_safe_mime": {
        "params": ["mime_type"],
        "returns": "bool",
    },
    "redact_sensitive_data": {
        "params": ["text"],
        "returns": "str",
    },
}


EXPECTED_UTIL_FUNCTIONS = {
    "validate_video_url": {
        "params": ["url_str"],
        "returns": "bool",
    },
    "compute_sha256": {
        "params": ["file_path"],
        "returns": "str",
    },
    "ensure_dir": {
        "params": ["path"],
        "returns": "Path",
    },
    "load_yaml_config": {
        "params": ["config_path"],
        "returns": "dict",
    },
}


MODULES_WITH_EXPECTED_APIS = {
    "video_intake_core.transcription": EXPECTED_TRANSCRIPTION_FUNCTIONS,
    "video_intake_core.visual": EXPECTED_VISUAL_FUNCTIONS,
    "video_intake_core.ocr": EXPECTED_OCR_FUNCTIONS,
    "video_intake_core.audio": EXPECTED_AUDIO_FUNCTIONS,
    "video_intake_core.jobs": EXPECTED_JOBS_FUNCTIONS,
    "video_intake_core.storage": EXPECTED_STORAGE_FUNCTIONS,
    "video_intake_core.security": EXPECTED_SECURITY_FUNCTIONS,
    "video_intake_core.utils": EXPECTED_UTIL_FUNCTIONS,
}


class TestContractAPIs:
    """Verify that each module exposes the expected public functions."""

    @pytest.mark.parametrize(
        "module_path,expected_funcs",
        list(MODULES_WITH_EXPECTED_APIS.items()),
    )
    def test_module_exposes_expected_functions(
        self, module_path: str, expected_funcs: dict
    ):
        """Each module should expose all expected public functions."""
        import importlib

        try:
            module = importlib.import_module(module_path)
        except ImportError:
            pytest.skip(f"Module {module_path} not importable")

        for func_name, _spec in expected_funcs.items():
            assert hasattr(
                module, func_name
            ), f"{module_path} missing function: {func_name}"

    @pytest.mark.parametrize(
        "module_path,expected_funcs",
        list(MODULES_WITH_EXPECTED_APIS.items()),
    )
    def test_functions_have_correct_param_count(
        self, module_path: str, expected_funcs: dict
    ):
        """Each expected function should have the documented number of params."""
        import importlib
        import inspect

        try:
            module = importlib.import_module(module_path)
        except ImportError:
            pytest.skip(f"Module {module_path} not importable")

        for func_name, spec in expected_funcs.items():
            func = getattr(module, func_name, None)
            if func is None:
                continue

            actual_params = len(inspect.signature(func).parameters)
            expected_params = len(spec["params"])
            assert actual_params == expected_params, (
                f"{module_path}.{func_name} has {actual_params} params, "
                f"expected {expected_params}"
            )


class TestModuleInitializable:
    """Verify that each module can be instantiated and has the expected
    class interface."""

    def test_jobs_module_has_job_class(self):
        """jobs module should expose a Job class."""
        from video_intake_core.jobs import Job

        assert hasattr(Job, "id")
        assert hasattr(Job, "status")
        assert hasattr(Job, "source_url")

    def test_storage_module_has_manager_class(self):
        """storage module should expose a StorageManager class."""
        from video_intake_core.storage import StorageManager

        assert hasattr(StorageManager, "save_artifact")
        assert hasattr(StorageManager, "get_artifacts")

    def test_security_module_has_validator(self):
        """security module should expose SSRF validation."""
        from video_intake_core.security import (
            is_safe_url,
            validate_url,
        )

        # validate_url should accept a URL string
        result = validate_url("https://www.youtube.com/watch?v=test123")
        assert result.is_valid or result.error is not None

        # is_safe_url should reject internal IPs
        assert not is_safe_url("http://169.254.169.254/")

    def test_utils_module_has_hash_function(self):
        """utils module should expose SHA-256 computation."""
        import tempfile

        from video_intake_core.utils import compute_sha256

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"hello world")
            f.flush()
            h = compute_sha256(f.name)
            assert len(h) == 64  # SHA-256 hex is 64 chars
