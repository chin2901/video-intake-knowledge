"""
Memory module.

Provides the memory provider interface and local SQLite-based implementation.
Enables storing and retrieving extracted knowledge in the session context.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _default_memory_path() -> Path:
    """Return the default memory DB path outside the repository."""
    env_path = os.environ.get("VITK_MEMORY_DB")
    if env_path:
        return Path(os.path.expanduser(env_path))
    default_dir = Path.home() / ".video-intake"
    default_dir.mkdir(parents=True, exist_ok=True)
    return default_dir / "memory.db"


@dataclass
class MemoryEntryMetadata:
    """Metadata for a memory entry."""

    video_title: str = ""
    language: str = "es"
    created_at: str = ""
    tags: list[str] = field(default_factory=list)
    related_entries: list[str] = field(default_factory=list)


@dataclass
class MemoryEntry:
    """A single entry in the memory bank."""

    id: Optional[str] = None
    job_id: str = ""
    source_url: str = ""
    source_title: str = ""
    extracted_at: str = ""
    content_type: str = ""
    content: str = ""
    summary: str = ""
    metadata: MemoryEntryMetadata | dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryQuery:
    """Query parameters for memory search."""

    text: str = ""
    content_type: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    job_id: str = ""
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    limit: int = 20
    offset: int = 0


@dataclass
class MemoryBankInfo:
    """Information about the memory bank."""

    total_entries: int = 0
    total_size_bytes: int = 0
    by_content_type: dict[str, int] = field(default_factory=dict)
    db_path: str = ""
    provider_type: str = "local_sqlite"
    database_path: str = ""
    is_available: bool = True


@dataclass
class MemoryStats:
    """Memory statistics."""

    total_entries: int = 0
    content_types: dict[str, int] = field(default_factory=dict)
    db_path: str = ""


@dataclass
class HealthCheckResult:
    """Health check result."""

    status: str = "healthy"
    error: str | None = None
    db_path: str = ""
    db_exists: bool = True


class MemoryProvider(ABC):
    """Abstract interface for memory storage providers."""

    @abstractmethod
    def store_entry(self, entry: MemoryEntry) -> str:
        """Store a new memory entry.

        Args:
            entry: The memory entry to store.

        Returns:
            The ID of the stored entry.
        """
        ...

    @abstractmethod
    def get_entry(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory entry by ID."""
        ...

    @abstractmethod
    def list_entries(
        self,
        content_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[MemoryEntry]:
        """List memory entries with optional filtering."""
        ...

    @abstractmethod
    def search_entries(self, query: MemoryQuery) -> list[MemoryEntry]:
        """Search memory entries by query."""
        ...

    @abstractmethod
    def delete_entry(self, entry_id: str) -> bool:
        """Delete a memory entry by ID."""
        ...

    @abstractmethod
    def get_stats(self) -> MemoryStats:
        """Get memory statistics."""
        ...

    @abstractmethod
    def get_bank_info(self) -> MemoryBankInfo:
        """Get memory bank information."""
        ...

    @abstractmethod
    def health_check(self) -> HealthCheckResult:
        """Check provider health."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Close the provider and release resources."""
        ...


class LocalSQLiteMemoryProvider(MemoryProvider):
    """Local SQLite-based memory provider.

    Stores extracted knowledge in a local SQLite database.
    Provides full CRUD operations and text search.
    """

    def __init__(self, db_path: str | Path | None = None):
        if db_path is None:
            self.db_path = _default_memory_path()
        else:
            self.db_path = Path(os.path.expanduser(str(db_path)))
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the SQLite database schema."""
        import sqlite3

        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_entries (
                    id TEXT PRIMARY KEY,
                    job_id TEXT DEFAULT '',
                    source_url TEXT NOT NULL,
                    source_title TEXT NOT NULL,
                    extracted_at TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    summary TEXT,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_content_type
                ON memory_entries(content_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_source_url
                ON memory_entries(source_url)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_extracted_at
                ON memory_entries(extracted_at)
            """)
            conn.commit()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _generate_id() -> str:
        import uuid
        return f"mem_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def _serialize_metadata(metadata: MemoryEntryMetadata | dict[str, Any]) -> str:
        import json
        if isinstance(metadata, MemoryEntryMetadata):
            return json.dumps({
                "video_title": metadata.video_title,
                "language": metadata.language,
                "created_at": metadata.created_at,
                "tags": metadata.tags,
                "related_entries": metadata.related_entries,
            }, ensure_ascii=False)
        return json.dumps(metadata, ensure_ascii=False)

    @staticmethod
    def _deserialize_metadata(raw: str) -> MemoryEntryMetadata:
        import json
        if not raw:
            return MemoryEntryMetadata()
        data = json.loads(raw)
        return MemoryEntryMetadata(
            video_title=data.get("video_title", ""),
            language=data.get("language", "es"),
            created_at=data.get("created_at", ""),
            tags=data.get("tags", []),
            related_entries=data.get("related_entries", []),
        )

    # ------------------------------------------------------------------
    # Store
    # ------------------------------------------------------------------

    def store_entry(self, entry: MemoryEntry) -> str:
        """Store a new memory entry."""
        import sqlite3
        import uuid

        entry_id = entry.id or f"mem_{uuid.uuid4().hex[:16]}"
        now = self._now()
        extracted_at = entry.extracted_at or now

        if isinstance(entry.metadata, MemoryEntryMetadata):
            meta_json = self._serialize_metadata(entry.metadata)
        else:
            meta_json = json.dumps(entry.metadata, ensure_ascii=False) if entry.metadata else "{}"

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT INTO memory_entries
                (id, job_id, source_url, source_title, extracted_at, content_type,
                 content, summary, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry_id,
                entry.job_id,
                entry.source_url,
                entry.source_title,
                extracted_at,
                entry.content_type,
                entry.content,
                entry.summary,
                meta_json,
                now,
                now,
            ))
            conn.commit()

        logger.info(f"Stored memory entry {entry_id} ({entry.content_type})")
        return entry_id

    # ------------------------------------------------------------------
    # Retrieve
    # ------------------------------------------------------------------

    def get_entry(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory entry by ID."""
        import sqlite3

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM memory_entries WHERE id = ?",
                (entry_id,),
            ).fetchone()

        if not row:
            return None

        metadata = self._deserialize_metadata(row["metadata"])

        return MemoryEntry(
            id=row["id"],
            job_id=row["job_id"] or "",
            source_url=row["source_url"],
            source_title=row["source_title"],
            extracted_at=row["extracted_at"],
            content_type=row["content_type"],
            content=row["content"],
            summary=row["summary"] or "",
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------

    def list_entries(
        self,
        content_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[MemoryEntry]:
        """List memory entries."""
        import sqlite3

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            if content_type:
                rows = conn.execute(
                    """SELECT * FROM memory_entries
                       WHERE content_type = ?
                       ORDER BY extracted_at DESC
                       LIMIT ? OFFSET ?""",
                    (content_type, limit, offset),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM memory_entries
                       ORDER BY extracted_at DESC
                       LIMIT ? OFFSET ?""",
                    (limit, offset),
                ).fetchall()

        entries = []
        for row in rows:
            metadata = self._deserialize_metadata(row["metadata"])
            entries.append(MemoryEntry(
                id=row["id"],
                job_id=row["job_id"] or "",
                source_url=row["source_url"],
                source_title=row["source_title"],
                extracted_at=row["extracted_at"],
                content_type=row["content_type"],
                content=row["content"],
                summary=row["summary"] or "",
                metadata=metadata,
            ))

        return entries

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search_entries(self, query: MemoryQuery) -> list[MemoryEntry]:
        """Search memory entries by query."""
        import sqlite3

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            sql = """SELECT * FROM memory_entries
               WHERE (content LIKE ? OR summary LIKE ?)"""
            params = [f"%{query.text}%", f"%{query.text}%"]

            if query.content_type:
                sql += " AND content_type = ?"
                params.append(query.content_type)

            if query.job_id:
                sql += " AND job_id = ?"
                params.append(query.job_id)

            if query.tags:
                # Search in metadata tags
                tag_conditions = " OR ".join(["metadata LIKE ?"] * len(query.tags))
                sql += f" AND ({tag_conditions})"
                for tag in query.tags:
                    params.append(f"%{tag}%")

            sql += " ORDER BY extracted_at DESC LIMIT ? OFFSET ?"
            params.extend([query.limit, query.offset])

            rows = conn.execute(sql, params).fetchall()

        entries = []
        for row in rows:
            metadata = self._deserialize_metadata(row["metadata"])
            entries.append(MemoryEntry(
                id=row["id"],
                job_id=row["job_id"] or "",
                source_url=row["source_url"],
                source_title=row["source_title"],
                extracted_at=row["extracted_at"],
                content_type=row["content_type"],
                content=row["content"],
                summary=row["summary"] or "",
                metadata=metadata,
            ))

        return entries

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete_entry(self, entry_id: str) -> bool:
        """Delete a memory entry by ID."""
        import sqlite3

        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                "DELETE FROM memory_entries WHERE id = ?",
                (entry_id,),
            )
            conn.commit()
            deleted = cursor.rowcount > 0

        if deleted:
            logger.info(f"Deleted memory entry {entry_id}")

        return deleted

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> MemoryStats:
        """Get memory statistics."""
        import sqlite3

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            total = conn.execute(
                "SELECT COUNT(*) FROM memory_entries"
            ).fetchone()[0]

            by_type = conn.execute(
                """SELECT content_type, COUNT(*) as count
                   FROM memory_entries
                   GROUP BY content_type
                   ORDER BY count DESC"""
            ).fetchall()

            content_types = {r["content_type"]: r["count"] for r in by_type}

            return MemoryStats(
                total_entries=total,
                content_types=content_types,
                db_path=str(self.db_path),
            )

    def get_bank_info(self) -> MemoryBankInfo:
        """Get memory bank information."""
        stats = self.get_stats()

        import os
        db_size = os.path.getsize(self.db_path) if self.db_path.exists() else 0

        return MemoryBankInfo(
            total_entries=stats.total_entries,
            total_size_bytes=db_size,
            by_content_type=stats.content_types,
            db_path=str(self.db_path),
            database_path=str(self.db_path),
            is_available=True,
        )

    def health_check(self) -> HealthCheckResult:
        """Check provider health."""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute("SELECT 1")
            return HealthCheckResult(
                status="healthy",
                error=None,
                db_path=str(self.db_path),
                db_exists=self.db_path.exists(),
            )
        except Exception as e:
            return HealthCheckResult(
                status="unhealthy",
                error=str(e),
            )

    def close(self) -> None:
        """Close the provider and release resources."""
        # SQLite connections are closed automatically after each operation
        pass


# ------------------------------------------------------------------
# Factory
# ------------------------------------------------------------------


def create_memory_provider(
    provider_type: str = "local",
    **kwargs: Any,
) -> MemoryProvider:
    """Create a memory provider by type.

    Args:
        provider_type: Provider type ('local' or a custom class path).
        **kwargs: Provider-specific configuration.

    Returns:
        A MemoryProvider instance.
    """
    if provider_type == "local":
        db_path = kwargs.get("db_path", "./video_intake_memory.db")
        return LocalSQLiteMemoryProvider(db_path=db_path)

    raise ValueError(f"Unknown memory provider: {provider_type}")


# Alias for backward compatibility
LocalMemoryProvider = LocalSQLiteMemoryProvider
