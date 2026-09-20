"""
Memory module.

Provides the memory provider interface and local SQLite-based implementation.
Enables storing and retrieving extracted knowledge in the session context.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """A single entry in the memory bank."""

    id: Optional[str] = None
    source_url: str = ""
    source_title: str = ""
    extracted_at: str = ""
    content_type: str = ""
    content: str = ""
    summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class MemoryProvider(ABC):
    """Abstract interface for memory storage providers."""

    @abstractmethod
    def store(
        self,
        source_url: str,
        source_title: str,
        content_type: str,
        content: str,
        summary: str = "",
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """Store a new memory entry.

        Args:
            source_url: URL or path of the source video.
            source_title: Title of the source video.
            content_type: Type of content (transcript, context, knowledge, etc.)
            content: The full content to store.
            summary: Optional summary of the content.
            metadata: Optional additional metadata.

        Returns:
            The ID of the stored entry.
        """
        ...

    @abstractmethod
    def retrieve(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory entry by ID."""
        ...

    @abstractmethod
    def list(
        self,
        content_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[MemoryEntry]:
        """List memory entries with optional filtering."""
        ...

    @abstractmethod
    def search(
        self,
        query: str,
        content_type: Optional[str] = None,
        limit: int = 20,
    ) -> list[MemoryEntry]:
        """Search memory entries by text query."""
        ...

    @abstractmethod
    def delete(self, entry_id: str) -> bool:
        """Delete a memory entry by ID."""
        ...

    @abstractmethod
    def clear(self) -> int:
        """Clear all memory entries. Returns count of deleted entries."""
        ...

    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        ...


class LocalSQLiteMemoryProvider(MemoryProvider):
    """Local SQLite-based memory provider.

    Stores extracted knowledge in a local SQLite database.
    Provides full CRUD operations and text search.
    """

    def __init__(self, db_path: str | Path = "./video_intake_memory.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the SQLite database schema."""
        import sqlite3

        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_entries (
                    id TEXT PRIMARY KEY,
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
    def _serialize_metadata(metadata: dict[str, Any]) -> str:
        import json
        return json.dumps(metadata, ensure_ascii=False)

    @staticmethod
    def _deserialize_metadata(raw: str) -> dict[str, Any]:
        import json
        if not raw:
            return {}
        return json.loads(raw)

    # ------------------------------------------------------------------
    # Store
    # ------------------------------------------------------------------

    def store(
        self,
        source_url: str,
        source_title: str,
        content_type: str,
        content: str,
        summary: str = "",
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """Store a memory entry."""
        import sqlite3
        import uuid

        entry_id = f"mem_{uuid.uuid4().hex[:16]}"
        now = self._now()
        meta_json = self._serialize_metadata(metadata or {})

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT INTO memory_entries
                (id, source_url, source_title, extracted_at, content_type,
                 content, summary, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry_id,
                source_url,
                source_title,
                now,
                content_type,
                content,
                summary,
                meta_json,
                now,
                now,
            ))
            conn.commit()

        logger.info(f"Stored memory entry {entry_id} ({content_type})")
        return entry_id

    # ------------------------------------------------------------------
    # Retrieve
    # ------------------------------------------------------------------

    def retrieve(self, entry_id: str) -> Optional[MemoryEntry]:
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

        return MemoryEntry(
            id=row["id"],
            source_url=row["source_url"],
            source_title=row["source_title"],
            extracted_at=row["extracted_at"],
            content_type=row["content_type"],
            content=row["content"],
            summary=row["summary"] or "",
            metadata=self._deserialize_metadata(row["metadata"]),
        )

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------

    def list(
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
            entries.append(MemoryEntry(
                id=row["id"],
                source_url=row["source_url"],
                source_title=row["source_title"],
                extracted_at=row["extracted_at"],
                content_type=row["content_type"],
                content=row["content"],
                summary=row["summary"] or "",
                metadata=self._deserialize_metadata(row["metadata"]),
            ))

        return entries

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        content_type: Optional[str] = None,
        limit: int = 20,
    ) -> list[MemoryEntry]:
        """Search memory entries by text content."""
        import sqlite3

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            if content_type:
                rows = conn.execute(
                    """SELECT * FROM memory_entries
                       WHERE content_type = ?
                         AND (content LIKE ? OR summary LIKE ?)
                       ORDER BY extracted_at DESC
                       LIMIT ?""",
                    (
                        content_type,
                        f"%{query}%",
                        f"%{query}%",
                        limit,
                    ),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM memory_entries
                       WHERE content LIKE ? OR summary LIKE ?
                       ORDER BY extracted_at DESC
                       LIMIT ?""",
                    (f"%{query}%", f"%{query}%", limit),
                ).fetchall()

        entries = []
        for row in rows:
            entries.append(MemoryEntry(
                id=row["id"],
                source_url=row["source_url"],
                source_title=row["source_title"],
                extracted_at=row["extracted_at"],
                content_type=row["content_type"],
                content=row["content"],
                summary=row["summary"] or "",
                metadata=self._deserialize_metadata(row["metadata"]),
            ))

        return entries

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete(self, entry_id: str) -> bool:
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
    # Clear
    # ------------------------------------------------------------------

    def clear(self) -> int:
        """Clear all memory entries."""
        import sqlite3

        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("DELETE FROM memory_entries")
            conn.commit()
            count = cursor.rowcount

        logger.info(f"Cleared {count} memory entries")
        return count

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        import sqlite3

        with sqlite3.connect(str(self.db_path)) as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM memory_entries"
            ).fetchone()[0]

            by_type = conn.execute(
                """SELECT content_type, COUNT(*) as count
                   FROM memory_entries
                   GROUP BY content_type
                   ORDER BY count DESC"""
            ).fetchall()

            stats = {
                "total_entries": total,
                "by_type": {r["content_type"]: r["count"] for r in by_type},
                "db_path": str(self.db_path),
            }

        return stats


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
