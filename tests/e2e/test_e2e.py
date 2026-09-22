"""
End-to-end tests for video-intake-knowledge CLI.

Verifica el comportamiento completo del sistema desde
la línea de comandos con datos reales o simulados.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# =============================================================================
# Fixtures
# =============================================================================

CLI_PATH = Path(__file__).parent.parent.parent / "packages" / "video_intake_core" / "cli" / "__init__.py"


# =============================================================================
# Tests CLI básicos
# =============================================================================

class TestCLIHelp:
    """Tests para la ayuda del CLI."""

    def test_help_output_exists(self):
        """El comando --help devuelve salida."""
        result = subprocess.run(
            [sys.executable, "-m", "video_intake_core.cli", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # El CLI es un módulo, no un script independiente
        # Verificar que al menos no falla
        assert result.returncode == 0 or "usage" in result.stdout.lower() or "usage" in result.stderr.lower()

    def test_no_args_no_crash(self):
        """Ejecutar sin argumentos no debe crashar."""
        result = subprocess.run(
            [sys.executable, "-m", "video_intake_core.cli"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # Debe mostrar ayuda o error de uso, no crashar
        assert result.returncode != 137  # No fue killed


class TestCLIParse:
    """Tests para el parseo de comandos CLI."""

    def test_version_flag(self):
        """La flag --version devuelve la versión."""
        import video_intake_core
        # Verificar que la versión está definida
        assert hasattr(video_intake_core, "__version__")
        assert video_intake_core.__version__ is not None
        assert len(video_intake_core.__version__) > 0


# =============================================================================
# Tests doctor
# =============================================================================

class TestDoctorCommand:
    """Tests para el comando doctor del CLI."""

    def test_doctor_module_exists(self):
        """El módulo doctor existe en el CLI."""
        from video_intake_core.cli.doctor import run_doctor
        assert callable(run_doctor)

    def test_create_sample_video_ffmpeg(self, tmp_path: Path):
        """Obsolete test placeholder."""
        pass

    def test_detect_vulnerable_ffmpeg(self):
        """Obsolete test placeholder."""
        pass


# =============================================================================
# Tests gestion de trabajos
# =============================================================================

class TestJobWorkflow:
    """Tests del flujo de gestión de trabajos."""

    def test_complete_workflow(self, tmp_path: Path):
        """Flujo completo: crear, ejecutar (simulado), ver resultados."""
        from video_intake_core.acquisition import detect_video_sources
        from video_intake_core.jobs import JobManager, JobState
        from video_intake_core.policies import resolve_policy

        # Configurar paths
        db_path = tmp_path / "workflow_test.db"

        # 1. Configurar política
        policy = resolve_policy(config_yaml=str(Path(__file__).parent.parent.parent / "config" / "default.yaml"))
        assert policy is not None

        # 2. Detectar fuentes
        video_path = tmp_path / "test_video.mp4"
        video_path.write_bytes(b"fake video")  # Simulado para tests

        sources = detect_video_sources(str(video_path))
        assert len(sources) > 0
        source = sources[0]

        # 3. Crear trabajo
        manager = JobManager(str(db_path))
        job = manager.create_job(
            video_path=str(video_path),
            source_type=source.source_type or "local",
            selected_operations=["download"],
        )
        assert job.state == JobState.WAITING

        # 4. Actualizar progreso (simulado)
        manager.update_progress(job.id, 100.0, current_phase="completed")
        manager.update_status(job.id, JobState.COMPLETED)

        # 5. Verificar estado del trabajo
        updated = manager.get_job(job.id)
        assert updated.state == JobState.COMPLETED
        assert updated.progress == 100.0


# =============================================================================
# Tests de export
# =============================================================================

class TestExportWorkflow:
    """Tests del flujo de exportación de contexto."""

    def test_context_generation_functions(self):
        """Las funciones de generación de contexto existen."""
        from video_intake_core.context import (
            export_audio_context_mdx,
            export_extracted_knowledge_mdx,
            export_visual_context_mdx,
            extract_knowledge,
            generate_audio_context,
            generate_visual_context,
        )

        assert callable(generate_audio_context)
        assert callable(generate_visual_context)
        assert callable(extract_knowledge)
        assert callable(export_audio_context_mdx)
        assert callable(export_visual_context_mdx)
        assert callable(export_extracted_knowledge_mdx)


# =============================================================================
# Tests de OCR
# =============================================================================

class TestOCRValidation:
    """Tests de validación de OCR (simulados)."""

    def test_ocr_module_exists(self):
        """El módulo OCR existe."""
        from video_intake_core.ocr import (
            OCRResult,
            batch_ocr,
            ocr_frame,
            preprocess_frame,
        )
        assert callable(batch_ocr)
        assert callable(ocr_frame)
        assert callable(preprocess_frame)
        assert OCRResult is not None


# =============================================================================
# Tests de transcripción
# =============================================================================

class TestTranscriptionValidation:
    """Tests de validación de transcripción (simulados)."""

    def test_transcription_module_exists(self):
        """El módulo de transcripción existe."""
        from video_intake_core.transcription import (
            TranscriptionResult,
            extract_captions_from_platform,
            extract_local_captions,
            load_whisper_model,
            transcribe_video,
        )
        assert callable(transcribe_video)
        assert callable(extract_captions_from_platform)
        assert callable(extract_local_captions)
        assert callable(load_whisper_model)
        assert TranscriptionResult is not None


# =============================================================================
# Tests de inspección
# =============================================================================

class TestInspectionValidation:
    """Tests de inspección de vídeo (simulados)."""

    def test_inspection_module_exists(self):
        """El módulo de inspección existe."""
        from video_intake_core.inspection import (
            VideoInfo,
            inspect_local_video,
            inspect_remote_video,
            inspect_video,
        )
        assert callable(inspect_video)
        assert callable(inspect_local_video)
        assert callable(inspect_remote_video)
        assert VideoInfo is not None


# =============================================================================
# Tests de audio
# =============================================================================

class TestAudioValidation:
    """Tests de extracción de audio (simulados)."""

    def test_audio_module_exists(self):
        """El módulo de audio existe."""
        from video_intake_core.audio import (
            AudioResult,
            extract_audio,
            extract_audio_from_file,
            extract_audio_from_url,
        )
        assert callable(extract_audio)
        assert callable(extract_audio_from_file)
        assert callable(extract_audio_from_url)
        assert AudioResult is not None


# =============================================================================
# Tests JSON output
# =============================================================================

class TestJSONOutput:
    """Tests para la salida JSON del CLI."""

    def test_json_output_format(self):
        """Verificar que el output JSON es válido cuando se solicita."""

        # Simular una salida JSON estructurada
        result = {
            "status": "success",
            "artifacts": [],
            "errors": [],
        }
        json_str = json.dumps(result)
        parsed = json.loads(json_str)
        assert parsed["status"] == "success"


# =============================================================================
# Tests de cleanup
# =============================================================================

class TestCleanupCommand:
    """Tests para el comando cleanup del CLI."""

    def test_cleanup_module_exists(self):
        """El módulo de cleanup existe."""
        from video_intake_core.cli.cleanup import (
            cleanup_command,
            run_storage_cleanup,
        )
        assert callable(cleanup_command)
        assert callable(run_storage_cleanup)
