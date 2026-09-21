"""
Policies module.

Manages model and processing policies from YAML configuration.
Provides policy resolution, model selection, and processing strategy
determination based on configuration and system capabilities.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)


class PolicyResolver:
    """Resolves processing policies from configuration.

    Determines which models, engines, and strategies to use
    based on configuration, system capabilities, and user preferences.
    """

    def __init__(
        self,
        config_path: Optional[str | Path] = None,
        config_dict: Optional[dict[str, Any]] = None,
    ):
        self.config: dict[str, Any] = {}

        if config_dict:
            self.config = config_dict
        elif config_path:
            self._load_config(config_path)

        self._transcription_policy = self.config.get("transcription", {})
        self._visual_policy = self.config.get("visual", {})
        self._models_policy = self.config.get("models", {})
        self._security_policy = self.config.get("security", {})

    # Convenience properties for direct attribute access
    @property
    def transcription(self) -> Any:
        """Access transcription policy as object with attributes."""
        class TranscriptionPolicy:
            def __init__(self, policy: dict[str, Any]):
                self.model = policy.get("model", "tiny")
                self.language = policy.get("language")
                self.local_engine = policy.get("local_engine", "whisper")
                self.strategy_order = policy.get("strategy_order", ["platform_captions", "local_captions", "whisper"])
                self.fallback_enabled = policy.get("fallback_enabled", True)
                self.device = policy.get("device", "cpu")
        return TranscriptionPolicy(self._transcription_policy)

    @property
    def visual(self) -> Any:
        """Access visual policy as object with attributes."""
        class VisualPolicy:
            def __init__(self, policy: dict[str, Any]):
                self.scene_detection = policy.get("scene_detection", True)
                self.frame_sampling = policy.get("frame_sampling", "scene_based")
                self.max_candidate_frames = policy.get("max_candidate_frames", 20)
                self.ocr_engine = policy.get("ocr_engine", "tesseract")
                self.vision_fallback_enabled = policy.get("vision_fallback_enabled", False)
                self.scene_detection_threshold = policy.get("scene_detection_threshold", 30.0)
                self.min_scene_length = policy.get("min_scene_length", 2.0)
        return VisualPolicy(self._visual_policy)

    @property
    def models(self) -> Any:
        """Access models policy as object with attributes."""
        class ModelsPolicy:
            def __init__(self, policy: dict[str, Any]):
                self.priority = policy.get("priority", {})
                self.allow_external_providers = policy.get("allow_external_providers", False)
                self.require_explicit_approval_for_paid = policy.get("require_explicit_approval_for_paid", True)
                self.configured_providers = policy.get("configured_providers", {})
        return ModelsPolicy(self._models_policy)

    @property
    def security(self) -> Any:
        """Access security policy as object with attributes."""
        class SecurityPolicy:
            def __init__(self, policy: dict[str, Any]):
                self.strict_url_validation = policy.get("strict_url_validation", True)
                self.ssrf_protection = policy.get("ssrf_protection", True)
                self.allowed_domains = policy.get("allowed_domains", [])
                self.scan_downloaded_files = policy.get("scan_downloaded_files", False)
                self.redact_sensitive_data = policy.get("redact_sensitive_data", False)
                self.prompt_injection_protection = policy.get("prompt_injection_protection", True)
                self.sanitize_filenames = policy.get("sanitize_filenames", True)
        return SecurityPolicy(self._security_policy)

    def _load_config(self, path: str | Path) -> None:
        """Load configuration from YAML file."""
        path = Path(path)
        if not path.exists():
            logger.warning(f"Config file not found: {path}")
            return
        with open(path) as f:
            self.config = yaml.safe_load(f) or {}

    # ------------------------------------------------------------------
    # Transcription policy
    # ------------------------------------------------------------------

    def get_transcription_strategy_order(self) -> list[str]:
        """Get the ordered list of transcription strategies to try."""
        strategies = self._transcription_policy.get("strategy_order", [])
        if not strategies:
            return [
                "platform_captions",
                "local_captions",
                "whisper",
            ]
        return strategies

    def get_transcription_language(self) -> Optional[str]:
        """Get the preferred transcription language."""
        return self._transcription_policy.get("language")

    def get_transcription_local_engine(self) -> str:
        """Get the local transcription engine to use."""
        return self._transcription_policy.get("local_engine", "whisper")

    def get_transcription_model(self) -> str:
        """Get the default transcription model."""
        return self._transcription_policy.get("model", "tiny")

    def is_transcription_fallback_enabled(self) -> bool:
        """Check if fallback to alternative strategies is enabled."""
        return self._transcription_policy.get("fallback_enabled", True)

    def get_transcription_device(self) -> str:
        """Get the device to use for transcription (cpu, cuda, etc.)."""
        return self._transcription_policy.get("device", "cpu")

    # ------------------------------------------------------------------
    # Visual policy
    # ------------------------------------------------------------------

    def is_scene_detection_enabled(self) -> bool:
        """Check if scene detection is enabled."""
        return self._visual_policy.get("scene_detection", True)

    def get_frame_sampling_method(self) -> str:
        """Get the frame sampling method."""
        return self._visual_policy.get("frame_sampling", "scene_based")

    def get_max_candidate_frames(self) -> int:
        """Get the maximum number of candidate frames for analysis."""
        return self._visual_policy.get("max_candidate_frames", 20)

    def get_ocr_engine(self) -> str:
        """Get the OCR engine to use."""
        return self._visual_policy.get("ocr_engine", "tesseract")

    def is_vision_fallback_enabled(self) -> bool:
        """Check if vision model fallback is enabled."""
        return self._visual_policy.get("vision_fallback_enabled", False)

    def get_scene_detection_threshold(self) -> float:
        """Get the scene detection threshold."""
        return self._visual_policy.get("scene_detection_threshold", 30.0)

    def get_min_scene_length(self) -> float:
        """Get the minimum scene length in seconds."""
        return self._visual_policy.get("min_scene_length", 2.0)

    # ------------------------------------------------------------------
    # Model policy
    # ------------------------------------------------------------------

    def get_model_priority(self, model_type: str) -> list[str]:
        """Get the priority list for a specific model type.

        Args:
            model_type: One of 'transcript', 'visual', 'reasoning'.

        Returns:
            Priority-ordered list of model identifiers.
        """
        priorities = self._models_policy.get("priority", {})
        return priorities.get(model_type, [])

    def is_external_providers_allowed(self) -> bool:
        """Check if external model providers are allowed."""
        return self._models_policy.get("allow_external_providers", False)

    def is_paid_model_approval_required(self) -> bool:
        """Check if explicit approval is required for paid models."""
        return self._models_policy.get(
            "require_explicit_approval_for_paid", True
        )

    def get_configured_providers(self) -> dict[str, Any]:
        """Get the list of configured model providers."""
        return self._models_policy.get("configured_providers", {})

    # ------------------------------------------------------------------
    # Security policy
    # ------------------------------------------------------------------

    def is_url_validation_strict(self) -> bool:
        """Check if strict URL validation is enabled."""
        return self._security_policy.get("strict_url_validation", True)

    def is_ssrf_protection_enabled(self) -> bool:
        """Check if SSRF protection is enabled."""
        return self._security_policy.get("ssrf_protection", True)

    def get_allowed_domains(self) -> list[str]:
        """Get the list of allowed domains."""
        return self._security_policy.get("allowed_domains", [])

    def is_file_scanning_enabled(self) -> bool:
        """Check if downloaded file scanning is enabled."""
        return self._security_policy.get("scan_downloaded_files", False)

    def is_sensitive_data_redaction_enabled(self) -> bool:
        """Check if sensitive data redaction is enabled."""
        return self._security_policy.get("redact_sensitive_data", False)

    def is_prompt_injection_protection_enabled(self) -> bool:
        """Check if prompt injection protection is enabled."""
        return self._security_policy.get("prompt_injection_protection", True)

    def is_filename_sanitization_enabled(self) -> bool:
        """Check if filename sanitization is enabled."""
        return self._security_policy.get("sanitize_filenames", True)

    # ------------------------------------------------------------------
    # Limits
    # ------------------------------------------------------------------

    def get_max_video_duration_minutes(self) -> int:
        """Get the maximum video duration in minutes."""
        return self.config.get("limits", {}).get(
            "max_video_duration_minutes", 600
        )

    def get_max_download_size_mb(self) -> int:
        """Get the maximum download size in MB."""
        return self.config.get("limits", {}).get(
            "max_download_size_mb", 5000
        )

    def get_max_batch_items(self) -> int:
        """Get the maximum number of items in a batch."""
        return self.config.get("limits", {}).get(
            "max_batch_items", 50
        )

    def get_max_parallel_jobs(self) -> int:
        """Get the maximum number of parallel jobs."""
        return self.config.get("limits", {}).get(
            "max_parallel_jobs", 4
        )

    def get_timeout_seconds(self) -> int:
        """Get the default timeout in seconds."""
        return self.config.get("limits", {}).get(
            "timeout_seconds", 3600
        )

    # ------------------------------------------------------------------
    # Storage policy
    # ------------------------------------------------------------------

    def get_storage_root_dir(self) -> str:
        """Get the root directory for artifact storage."""
        return self.config.get("storage", {}).get(
            "root_dir", "./artifacts"
        )

    def get_artifact_retention_days(self) -> int:
        """Get the artifact retention period in days."""
        return self.config.get("storage", {}).get(
            "artifact_retention_days", 90
        )

    def get_max_storage_gb(self) -> int:
        """Get the maximum storage in GB."""
        return self.config.get("storage", {}).get(
            "max_storage_gb", 100
        )

    def get_cleanup_policy(self) -> str:
        """Get the cleanup policy."""
        return self.config.get("storage", {}).get(
            "cleanup_policy", "age"
        )

    # ------------------------------------------------------------------
    # Acquisition policy
    # ------------------------------------------------------------------

    def get_enabled_sources(self) -> list[str]:
        """Get the list of enabled video sources."""
        sources = self.config.get("acquisition", {}).get(
            "enabled_sources", ["youtube", "facebook", "instagram", "tiktok", "local"]
        )
        return sources

    def get_preferred_video_quality(self) -> str:
        """Get the preferred video quality."""
        return self.config.get("acquisition", {}).get(
            "preferred_video_quality", "best"
        )

    def get_preferred_audio_quality(self) -> str:
        """Get the preferred audio quality."""
        return self.config.get("acquisition", {}).get(
            "preferred_audio_quality", "best"
        )

    def is_captions_first(self) -> bool:
        """Check if captions should be tried before transcription."""
        return self.config.get("acquisition", {}).get(
            "captions_first", True
        )

    def is_cache_enabled(self) -> bool:
        """Check if download/cache is enabled."""
        return self.config.get("acquisition", {}).get(
            "cache_enabled", True
        )

    # ------------------------------------------------------------------
    # Memory policy
    # ------------------------------------------------------------------

    def is_memory_enabled(self) -> bool:
        """Check if memory integration is enabled."""
        return self.config.get("memory", {}).get("enabled", True)

    def get_default_memory_provider(self) -> str:
        """Get the default memory provider."""
        return self.config.get("memory", {}).get(
            "default_provider", "local"
        )

    def is_memory_confirmation_required(self) -> bool:
        """Check if confirmation is required before storing memory."""
        return self.config.get("memory", {}).get(
            "require_confirmation", True
        )

    def get_max_context_tokens(self) -> int:
        """Get the maximum tokens for session context."""
        return self.config.get("memory", {}).get(
            "max_context_tokens", 4000
        )

    # ------------------------------------------------------------------
    # Host policy
    # ------------------------------------------------------------------

    def get_host_type(self) -> str:
        """Get the host type."""
        return self.config.get("host", {}).get("type", "generic")

    def get_session_context_strategy(self) -> str:
        """Get the session context strategy."""
        return self.config.get("host", {}).get(
            "session_context_strategy", "compact"
        )

    def is_auto_detect_messages_enabled(self) -> bool:
        """Check if automatic message detection is enabled."""
        return self.config.get("host", {}).get(
            "auto_detect_messages", True
        )

    def is_auto_detect_attachments_enabled(self) -> bool:
        """Check if automatic attachment detection is enabled."""
        return self.config.get("host", {}).get(
            "auto_detect_attachments", True
        )


# ----------------------------------------------------------------------
# Module-level convenience functions
# ----------------------------------------------------------------------


def resolve_policy(config_path: str | Path | None = None, config_dict: dict[str, Any] | None = None, config_yaml: str | Path | None = None) -> PolicyResolver:
    """
    Create a PolicyResolver instance from config file or dict.

    Args:
        config_path: Path to YAML configuration file (deprecated, use config_yaml).
        config_dict: Configuration dictionary (takes precedence over file).
        config_yaml: Path to YAML configuration file.

    Returns:
        Configured PolicyResolver instance.
    """
    # Support config_yaml alias for backward compatibility
    if config_yaml is not None and config_path is None:
        config_path = config_yaml
    return PolicyResolver(config_path=config_path, config_dict=config_dict)


def resolve_source_policy(source: str | None = None, config_path: str | Path | None = None, config_dict: dict[str, Any] | None = None, config_yaml: str | Path | None = None) -> PolicyResolver:
    """
    Create a PolicyResolver with source-specific defaults.

    Args:
        source: Video source name (e.g., "youtube") - accepted for compatibility.
        config_path: Path to YAML configuration file (deprecated, use config_yaml).
        config_dict: Configuration dictionary.
        config_yaml: Path to YAML configuration file.

    Returns:
        Configured PolicyResolver instance.
    """
    # Support config_yaml alias for backward compatibility
    if config_yaml is not None and config_path is None:
        config_path = config_yaml
    return resolve_policy(config_path=config_path, config_dict=config_dict)
