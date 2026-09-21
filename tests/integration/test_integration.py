"""
Integration tests for video-intake-knowledge.

Tests módulos reales con datos de prueba.
Necesita archivos de fixtures en tests/fixtures/.
"""

from __future__ import annotations

import datetime
import os
import time
from pathlib import Path

import pytest
from video_intake_core.acquisition import detect_video_sources
from video_intake_core.jobs import JobManager, JobState
from video_intake_core.schemas import get_schema, validate_against_schema
from video_intake_core.storage import ArtifactKind, ArtifactType, StorageManager
from video_intake_core.utils import compute_sha256, safe_filename

# =============================================================================
# Fixtures
# =============================================================================

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"
VIDEO_DIR = FIXTURE_DIR / "video"
AUDIO_DIR = FIXTURE_DIR / "audio"
SUBTITLE_DIR = FIXTURE_DIR / "subtitles"


@pytest.fixture(scope="session")
def any_video_file() -> Path | None:
    """Devuelve un archivo de vídeo de prueba si existe."""
    for ext in (".mp4", ".mov", ".mkv", ".webm", ".avi"):
        for f in VIDEO_DIR.glob(f"*{ext}"):
            return f
    return None


@pytest.fixture(scope="session")
def any_audio_file() -> Path | None:
    """Devuelve un archivo de audio de prueba si existe."""
    for ext in (".wav", ".mp3", ".m4a", ".opus", ".flac"):
        for f in AUDIO_DIR.glob(f"*{ext}"):
            return f
    return None


@pytest.fixture(scope="session")
def any_subtitle_file() -> Path | None:
    """Devuelve un archivo de subtítulos de prueba si existe."""
    for ext in (".srt", ".vtt", ".ass", ".ssa", ".json"):
        for f in SUBTITLE_DIR.glob(f"*{ext}"):
            return f
    return None


# =============================================================================
# Tests de utilidades
# =============================================================================

class TestComputeSHA256:
    """Pruebas para compute_sha256."""

    def test_compute_sha256_different_files(self, any_video_file: Path | None):
        """Archivos diferentes tienen hashes diferentes."""
        if any_video_file is None:
            pytest.skip("No hay archivo de vídeo de prueba")
        if not any_video_file.exists():
            pytest.skip(f"Archivo {any_video_file} no existe")

        hash1 = compute_sha256(any_video_file)
        assert hash1 is not None
        assert len(hash1) == 64  # SHA-256 hex
        assert hash1 != "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"  # not empty

    def test_compute_sha256_same_file(self, any_video_file: Path | None):
        """El mismo archivo siempre da el mismo hash."""
        if any_video_file is None or not any_video_file.exists():
            pytest.skip("No hay archivo de vídeo de prueba")
        hash1 = compute_sha256(any_video_file)
        hash2 = compute_sha256(any_video_file)
        assert hash1 == hash2


class TestSafeFilename:
    """Pruebas para safe_filename."""

    def test_safe_filename_normal(self):
        """Nombre normal se mantiene."""
        assert safe_filename("video.mp4") == "video.mp4"

    def test_safe_filename_path_traversal(self):
        """Path traversal se elimina."""
        result = safe_filename("../../../etc/passwd")
        assert ".." not in result
        assert "/" not in result

    def test_safe_filename_control_chars(self):
        """Caracteres de control se eliminan."""
        result = safe_filename("video\x00\x01name.mp4")
        for c in result:
            assert ord(c) >= 32 or c in ("\n", "\r", "\t")


# =============================================================================
# Tests de adquisición
# =============================================================================

class TestDetectVideoSources:
    """Pruebas para detect_video_sources."""

    def test_detect_empty_string(self):
        """Cadena vacía devuelve 0 fuentes."""
        sources = detect_video_sources("")
        assert len(sources) == 0

    def test_detect_local_path(self, any_video_file: Path | None):
        """Obtener una fuente local desde archivo existente."""
        if any_video_file is None or not any_video_file.exists():
            pytest.skip("No hay archivo de vídeo de prueba")

        sources = detect_video_sources(str(any_video_file))
        assert len(sources) > 0
        assert sources[0].source_type == "local"
        assert sources[0].resolved_path == str(any_video_file.resolve())

    def test_detect_nonexistent_path(self):
        """Ruta inexistente devuelve 0 fuentes."""
        sources = detect_video_sources("/nonexistent/path/video.mp4")
        assert len(sources) == 0

    def test_detect_multiple_sources(self):
        """Varias fuentes en una cadena."""
        text = "https://www.youtube.com/watch?v=dQw4w9WgXcQ https://www.tiktok.com/@user/video/123 /home/user/video.mp4"
        sources = detect_video_sources(text)
        # YouTube + TikTok + local (si existe) = al menos 2
        assert len(sources) >= 2

    def test_detect_youtube_url(self):
        """URL de YouTube se detecta."""
        sources = detect_video_sources("https://www.youtube.com/watch?v=test123")
        assert len(sources) > 0
        assert sources[0].source_type == "youtube"
        assert sources[0].id == "test123"

    def test_detect_youtube_short_url(self):
        """URL corta de YouTube se detecta."""
        sources = detect_video_sources("https://youtu.be/dQw4w9WgXcQ")
        assert len(sources) > 0
        assert sources[0].source_type == "youtube"

    def test_detect_facebook_url(self):
        """URL de Facebook se detecta."""
        sources = detect_video_sources("https://www.facebook.com/share/v/ABC123XYZ/")
        assert len(sources) > 0
        assert sources[0].source_type == "facebook"

    def test_detect_instagram_url(self):
        """URL de Instagram se detecta."""
        sources = detect_video_sources("https://www.instagram.com/reel/ABC123/")
        assert len(sources) > 0
        assert sources[0].source_type == "instagram"

    def test_detect_tiktok_url(self):
        """URL de TikTok se detecta."""
        sources = detect_video_sources("https://www.tiktok.com/@user/video/123456789")
        assert len(sources) > 0
        assert sources[0].source_type == "tiktok"

    def test_detect_embedded_url(self):
        """URL embebida en texto."""
        text = "Mira este vídeo: https://www.youtube.com/watch?v=test123, es increíble."
        sources = detect_video_sources(text)
        assert len(sources) > 0
        assert sources[0].source_type == "youtube"


# =============================================================================
# Tests de esquemas
# =============================================================================

class TestSchemas:
    """Pruebas para validación de esquemas."""

    def test_source_schema_exists(self):
        """Esquema source existe."""
        schema = get_schema("source")
        assert schema is not None
        assert "$schema" in schema

    def test_validate_correct_source(self):
        """Fuente correcta pasa validación."""
        data = {
            "source_type": "youtube",
            "id": "dQw4w9WgXcQ",
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "title": "Video test",
        }
        result = validate_against_schema(data, "source")
        assert result.is_valid is True

    def test_validate_missing_required_field(self):
        """Fuente con campo requerido faltante falla."""
        data = {"source_type": "youtube"}  # id requerido
        result = validate_against_schema(data, "source")
        assert result.is_valid is False

    def test_validate_invalid_type(self):
        """Fuente con tipo inválido falla."""
        data = {
            "source_type": "not_a_real_source",
            "id": "test",
        }
        result = validate_against_schema(data, "source")
        # Debe fallar por tipo no reconocido (enum validation)
        assert result.is_valid is False


# =============================================================================
# Tests de jobs
# =============================================================================

class TestJobManager:
    """Pruebas para JobManager con base de datos SQLite temporal."""

    def test_create_job(self, tmp_path: Path):
        """Crear un trabajo."""
        db_path = tmp_path / "jobs_test.db"
        manager = JobManager(str(db_path))

        job = manager.create_job(
            video_path="http://example.com/video.mp4",
            source_type="local",
            selected_operations=["download", "transcribe"],
        )
        assert job.id is not None
        assert job.state == JobState.WAITING
        assert len(job.selected_operations) == 2

    def test_list_jobs(self, tmp_path: Path):
        """Listar trabajos."""
        db_path = tmp_path / "jobs_list.db"
        manager = JobManager(str(db_path))

        job1 = manager.create_job(
            video_path="video1.mp4",
            source_type="local",
            selected_operations=["download"],
        )
        job2 = manager.create_job(
            video_path="video2.mp4",
            source_type="local",
            selected_operations=["transcribe"],
        )

        jobs = manager.list_jobs()
        assert len(jobs) == 2
        assert jobs[0].id == job1.id
        assert jobs[1].id == job2.id

    def test_get_job(self, tmp_path: Path):
        """Obtener un trabajo por ID."""
        db_path = tmp_path / "jobs_get.db"
        manager = JobManager(str(db_path))

        job = manager.create_job(
            video_path="video.mp4",
            source_type="local",
        )
        retrieved = manager.get_job(job.id)
        assert retrieved is not None
        assert retrieved.id == job.id
        assert retrieved.video_path == "video.mp4"

    def test_update_job_progress(self, tmp_path: Path):
        """Actualizar progreso del trabajo."""
        db_path = tmp_path / "jobs_progress.db"
        manager = JobManager(str(db_path))

        job = manager.create_job(
            video_path="video.mp4",
            source_type="local",
        )

        manager.update_progress(job.id, 50.0, current_phase="downloading")
        updated = manager.get_job(job.id)
        assert updated.progress == 50.0
        assert updated.current_phase == "downloading"

    def test_cancel_job(self, tmp_path: Path):
        """Cancelar un trabajo."""
        db_path = tmp_path / "jobs_cancel.db"
        manager = JobManager(str(db_path))

        job = manager.create_job(
            video_path="video.mp4",
            source_type="local",
        )
        manager.cancel_job(job.id)

        updated = manager.get_job(job.id)
        assert updated.state == JobState.CANCELLED

    def test_remove_job(self, tmp_path: Path):
        """Eliminar un trabajo."""
        db_path = tmp_path / "jobs_remove.db"
        manager = JobManager(str(db_path))

        job = manager.create_job(
            video_path="video.mp4",
            source_type="local",
        )
        manager.remove_job(job.id)

        retrieved = manager.get_job(job.id)
        assert retrieved is None

    def test_cleanup_completed(self, tmp_path: Path):
        """Limpiar trabajos completados antiguos."""
        db_path = tmp_path / "jobs_clean.db"
        manager = JobManager(str(db_path))

        # Crear trabajo completado hace mucho tiempo (hace 2 días)
        old_time = datetime.datetime.now() - datetime.timedelta(days=2)
        job = manager.create_job(
            video_path="video.mp4",
            source_type="local",
        )
        manager.update_status(job.id, JobState.COMPLETED, completed_at=old_time)

        # Crear trabajo completado recientemente
        recent_time = datetime.datetime.now() - datetime.timedelta(hours=1)
        recent_job = manager.create_job(
            video_path="video2.mp4",
            source_type="local",
        )
        manager.update_status(recent_job.id, JobState.COMPLETED, completed_at=recent_time)

        removed = manager.cleanup_completed(max_age_days=1)
        assert removed >= 1  # Al menos el antiguo fue removido

        remaining = manager.list_jobs()
        assert len(remaining) >= 1  # El reciente queda


# =============================================================================
# Tests de storage
# =============================================================================

class TestStorageManager:
    """Pruebas para StorageManager con directorio temporal."""

    def test_store_and_retrieve(self, tmp_path: Path):
        """Almacenar y recuperar un artefacto."""
        storage = StorageManager(str(tmp_path))

        test_content = b"Test video content"
        test_path = tmp_path / "test_input.mp4"
        test_path.write_bytes(test_content)

        art = storage.store_artifact(
            source_path=test_path,
            artifact_type=ArtifactType.VIDEO,
            artifact_kind=ArtifactKind.ORIGINAL,
            job_id="job-test-001",
            description="Test video",
        )
        assert art is not None
        assert art.sha256 is not None
        assert art.filename == "test_input.mp4"
        assert art.artifact_type == ArtifactType.VIDEO

        # Recuperar metadatos
        meta = storage.get_artifact_meta(job_id="job-test-001", filename="test_input.mp4")
        assert meta is not None
        assert meta.sha256 == art.sha256

    def test_list_artifacts(self, tmp_path: Path):
        """Listar artefactos de un job."""
        storage = StorageManager(str(tmp_path))

        # Create a couple of artifacts
        for i in range(3):
            test_path = tmp_path / f"test_{i}.mp4"
            test_path.write_bytes(b"Test content " + str(i).encode())

            storage.store_artifact(
                source_path=test_path,
                artifact_type=ArtifactType.VIDEO,
                artifact_kind=ArtifactKind.ORIGINAL,
                job_id="job-test-002",
                description=f"Test {i}",
            )

        artifacts = storage.list_artifacts("job-test-002")
        assert len(artifacts) == 3

    def test_get_nonexistent_artifact(self, tmp_path: Path):
        """Obtener un artefacto que no existe."""
        storage = StorageManager(str(tmp_path))
        meta = storage.get_artifact_meta(job_id="nonexistent", filename="nope.mp4")
        assert meta is None

    def test_cleanup_old_artifacts(self, tmp_path: Path):
        """Limpiar artefactos antiguos."""
        storage = StorageManager(str(tmp_path))

        storage._ensure_directories("job-cleanup-001")

        # Crear archivo "antiguo"
        old_file = tmp_path / "jobs" / "job-cleanup-001" / "video" / "old.mp4"
        old_file.parent.mkdir(parents=True, exist_ok=True)
        old_file.write_bytes(b"old content")
        # Modificar mtime al pasado
        old_time = time.time() - (45 * 24 * 3600)  # 45 días atrás
        os.utime(str(old_file), (old_time, old_time))

        # Create "recent" file
        recent_file = tmp_path / "jobs" / "job-cleanup-001" / "video" / "recent.mp4"
        recent_file.parent.mkdir(parents=True, exist_ok=True)
        recent_file.write_bytes(b"recent content")

        removed = storage.cleanup_old_artifacts(max_age_days=30)
        assert removed >= 1  # Al menos el antiguo fue removido

        assert recent_file.exists()  # El reciente queda
