"""
Tests de integración para memoria.

Verifica que el sistema de memoria funciona correctamente
con los datos extraídos reales del proyecto.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from video_intake_core.memory import (
    MemoryProvider,
    LocalMemoryProvider,
    MemoryEntry,
    MemoryEntryMetadata,
    MemoryQuery,
    MemoryBankInfo,
)


class TestMemoryProvider:
    """Pruebas para MemoryProvider (interfaz abstracta)."""

    def test_abstract_methods(self):
        """La interfaz abstracta define los métodos esperados."""
        assert hasattr(MemoryProvider, "store_entry")
        assert hasattr(MemoryProvider, "get_entry")
        assert hasattr(MemoryProvider, "list_entries")
        assert hasattr(MemoryProvider, "search_entries")
        assert hasattr(MemoryProvider, "delete_entry")
        assert hasattr(MemoryProvider, "get_stats")
        assert hasattr(MemoryProvider, "get_bank_info")
        assert hasattr(MemoryProvider, "health_check")
        assert hasattr(MemoryProvider, "close")


class TestLocalMemoryProvider:
    """Pruebas para la implementación local de memoria (SQLite)."""

    def test_store_and_retrieve_entry(self, tmp_path: Path):
        """Almacenar y recuperar una entrada de memoria."""
        db_path = tmp_path / "test_memory.db"
        provider = LocalMemoryProvider(str(db_path))

        entry = MemoryEntry(
            id="test-001",
            job_id="job-001",
            source_url="https://example.com/video.mp4",
            content_type="knowledge",
            content="Este es un contenido de prueba.",
            summary="Resumen de prueba.",
            metadata=MemoryEntryMetadata(
                video_title="Vídeo de prueba",
                language="es",
                created_at="2024-01-01T00:00:00Z",
                tags=["prueba", "test"],
                related_entries=[],
            ),
        )

        stored_id = provider.store_entry(entry)
        assert stored_id == "test-001"

        retrieved = provider.get_entry("test-001")
        assert retrieved is not None
        assert retrieved.id == "test-001"
        assert retrieved.content == "Este es un contenido de prueba."

    def test_list_all_entries(self, tmp_path: Path):
        """Listar todas las entradas de memoria."""
        db_path = tmp_path / "test_memory_list.db"
        provider = LocalMemoryProvider(str(db_path))

        # Crear múltiples entradas
        for i in range(3):
            entry = MemoryEntry(
                id=f"test-{i:03d}",
                job_id=f"job-{i:03d}",
                source_url=f"https://example.com/video{i}.mp4",
                content_type="knowledge",
                content=f"Contenido de prueba {i}.",
                summary=f"Resumen {i}.",
                metadata=MemoryEntryMetadata(
                    video_title=f"Vídeo {i}",
                    language="es",
                    created_at="2024-01-01T00:00:00Z",
                    tags=[f"tag{i}"],
                    related_entries=[],
                ),
            )
            provider.store_entry(entry)

        entries = provider.list_entries()
        assert len(entries) == 3

        # Orden por created_at descendente (más reciente primero)
        assert entries[0].id == "test-002"
        assert entries[1].id == "test-001"
        assert entries[2].id == "test-000"

    def test_search_by_text(self, tmp_path: Path):
        """Buscar entradas por texto."""
        db_path = tmp_path / "test_memory_search.db"
        provider = LocalMemoryProvider(str(db_path))

        entry1 = MemoryEntry(
            id="test-001",
            job_id="job-001",
            source_url="https://example.com/video1.mp4",
            content_type="knowledge",
            content="Python es un lenguaje de programación versátil.",
            summary="Resumen de Python.",
            metadata=MemoryEntryMetadata(
                video_title="Vídeo sobre Python",
                language="es",
                created_at="2024-01-01T00:00:00Z",
                tags=["python", "programming"],
                related_entries=[],
            ),
        )
        provider.store_entry(entry1)

        entry2 = MemoryEntry(
            id="test-002",
            job_id="job-002",
            source_url="https://example.com/video2.mp4",
            content_type="knowledge",
            content="JavaScript es usado para desarrollo web.",
            summary="Resumen de JavaScript.",
            metadata=MemoryEntryMetadata(
                video_title="Vídeo sobre JavaScript",
                language="es",
                created_at="2024-01-01T00:00:00Z",
                tags=["javascript", "web"],
                related_entries=[],
            ),
        )
        provider.store_entry(entry2)

        # Buscar por "Python"
        results = provider.search_entries(MemoryQuery(text="Python", limit=10))
        assert len(results) >= 1
        assert any("Python" in e.content for e in results)

        # Buscar por "web"
        results = provider.search_entries(MemoryQuery(text="web", limit=10))
        assert len(results) >= 1
        assert any("web" in e.content.lower() or "web" in [t.lower() for t in e.metadata.tags] for e in results)

    def test_search_by_tags(self, tmp_path: Path):
        """Buscar entradas por etiquetas."""
        db_path = tmp_path / "test_memory_tags.db"
        provider = LocalMemoryProvider(str(db_path))

        entry = MemoryEntry(
            id="test-001",
            job_id="job-001",
            source_url="https://example.com/video.mp4",
            content_type="knowledge",
            content="Contenido sobre machine learning.",
            summary="Resumen de ML.",
            metadata=MemoryEntryMetadata(
                video_title="Vídeo sobre ML",
                language="es",
                created_at="2024-01-01T00:00:00Z",
                tags=["machine-learning", "python", "ai"],
                related_entries=[],
            ),
        )
        provider.store_entry(entry)

        results = provider.search_entries(MemoryQuery(tags=["python"]))
        assert len(results) >= 1
        assert any("python" in [t.lower() for t in e.metadata.tags] for e in results)

    def test_delete_entry(self, tmp_path: Path):
        """Eliminar una entrada de memoria."""
        db_path = tmp_path / "test_memory_delete.db"
        provider = LocalMemoryProvider(str(db_path))

        entry = MemoryEntry(
            id="test-001",
            job_id="job-001",
            source_url="https://example.com/video.mp4",
            content_type="knowledge",
            content="Contenido a eliminar.",
            summary="Resumen.",
            metadata=MemoryEntryMetadata(
                video_title="Vídeo",
                language="es",
                created_at="2024-01-01T00:00:00Z",
                tags=["delete"],
                related_entries=[],
            ),
        )
        provider.store_entry(entry)

        assert provider.get_entry("test-001") is not None
        provider.delete_entry("test-001")
        assert provider.get_entry("test-001") is None

    def test_get_stats(self, tmp_path: Path):
        """Obtener estadísticas de la memoria."""
        db_path = tmp_path / "test_memory_stats.db"
        provider = LocalMemoryProvider(str(db_path))

        initial_stats = provider.get_stats()
        assert initial_stats.total_entries == 0

        # Agregar entradas
        for i in range(5):
            entry = MemoryEntry(
                id=f"test-{i:03d}",
                job_id=f"job-{i:03d}",
                source_url=f"https://example.com/video{i}.mp4",
                content_type="knowledge" if i % 2 == 0 else "transcript",
                content=f"Contenido {i}.",
                summary=f"Resumen {i}.",
                metadata=MemoryEntryMetadata(
                    video_title=f"Vídeo {i}",
                    language="es",
                    created_at="2024-01-01T00:00:00Z",
                    tags=[],
                    related_entries=[],
                ),
            )
            provider.store_entry(entry)

        stats = provider.get_stats()
        assert stats.total_entries == 5
        assert stats.content_types.get("knowledge", 0) == 3
        assert stats.content_types.get("transcript", 0) == 2

    def test_get_bank_info(self, tmp_path: Path):
        """Obtener información del banco de memoria."""
        db_path = tmp_path / "test_memory_bank.db"
        provider = LocalMemoryProvider(str(db_path))

        info = provider.get_bank_info()
        assert info.provider_type == "local_sqlite"
        assert info.database_path == str(db_path)
        assert info.is_available is True

    def test_health_check(self, tmp_path: Path):
        """Verificar que el proveedor está sano."""
        db_path = tmp_path / "test_memory_health.db"
        provider = LocalMemoryProvider(str(db_path))

        health = provider.health_check()
        assert health.status == "healthy"
        assert health.error is None

    def test_nonexistent_entry(self, tmp_path: Path):
        """Obtener una entrada inexistente devuelve None."""
        db_path = tmp_path / "test_memory_nonexistent.db"
        provider = LocalMemoryProvider(str(db_path))

        entry = provider.get_entry("nonexistent-id")
        assert entry is None

    def test_close(self, tmp_path: Path):
        """Cerrar la conexión a la base de datos."""
        db_path = tmp_path / "test_memory_close.db"
        provider = LocalMemoryProvider(str(db_path))

        provider.store_entry(MemoryEntry(
            id="test-001",
            job_id="job-001",
            source_url="https://example.com/video.mp4",
            content_type="knowledge",
            content="Test.",
            summary="Test.",
            metadata=MemoryEntryMetadata(
                video_title="Vídeo",
                language="es",
                created_at="2024-01-01T00:00:00Z",
                tags=[],
                related_entries=[],
            ),
        ))

        provider.close()
        # Después de cerrar, la operación debe fallar o ser ignorada
        # Dependiendo de la implementación, puede lanzar error o simplemente no hacer nada
        # No assertions, solo verificar que no crash
        provider.health_check()


class TestMemoryQueries:
    """Pruebas para consultas de memoria."""

    def test_query_empty_text(self, tmp_path: Path):
        """Consulta con texto vacío devuelve todas las entradas."""
        db_path = tmp_path / "test_query_empty.db"
        provider = LocalMemoryProvider(str(db_path))

        for i in range(3):
            entry = MemoryEntry(
                id=f"test-{i:03d}",
                job_id=f"job-{i:03d}",
                source_url=f"https://example.com/video{i}.mp4",
                content_type="knowledge",
                content=f"Contenido {i}.",
                summary=f"Resumen {i}.",
                metadata=MemoryEntryMetadata(
                    video_title=f"Vídeo {i}",
                    language="es",
                    created_at="2024-01-01T00:00:00Z",
                    tags=[],
                    related_entries=[],
                ),
            )
            provider.store_entry(entry)

        # Sin filtros, debería devolver todas
        results = provider.search_entries(MemoryQuery(text=""))
        assert len(results) == 3

    def test_query_limit(self, tmp_path: Path):
        """El límite de consulta se respeta."""
        db_path = tmp_path / "test_query_limit.db"
        provider = LocalMemoryProvider(str(db_path))

        for i in range(10):
            entry = MemoryEntry(
                id=f"test-{i:03d}",
                job_id=f"job-{i:03d}",
                source_url=f"https://example.com/video{i}.mp4",
                content_type="knowledge",
                content=f"Contenido {i}.",
                summary=f"Resumen {i}.",
                metadata=MemoryEntryMetadata(
                    video_title=f"Vídeo {i}",
                    language="es",
                    created_at="2024-01-01T00:00:00Z",
                    tags=[],
                    related_entries=[],
                ),
            )
            provider.store_entry(entry)

        results = provider.search_entries(MemoryQuery(text="", limit=3))
        assert len(results) <= 3

    def test_query_by_job_id(self, tmp_path: Path):
        """Filtrar por job_id."""
        db_path = tmp_path / "test_query_job.db"
        provider = LocalMemoryProvider(str(db_path))

        for job_id in ["job-001", "job-002", "job-003"]:
            entry = MemoryEntry(
                id=f"{job_id}-entry",
                job_id=job_id,
                source_url="https://example.com/video.mp4",
                content_type="knowledge",
                content=f"Contenido de {job_id}.",
                summary=f"Resumen de {job_id}.",
                metadata=MemoryEntryMetadata(
                    video_title="Vídeo",
                    language="es",
                    created_at="2024-01-01T00:00:00Z",
                    tags=[],
                    related_entries=[],
                ),
            )
            provider.store_entry(entry)

        results = provider.search_entries(MemoryQuery(job_id="job-002"))
        assert len(results) == 1
        assert results[0].job_id == "job-002"
