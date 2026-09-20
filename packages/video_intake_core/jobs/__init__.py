"""
Job management for video_intake_knowledge.

Manages job lifecycle: creation, status tracking, progress updates,
cancellation, and persistence via SQLite.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..schemas.job import Job


class JobDoesNotExistError(ValueError):
    """Raised when a requested job ID does not exist."""


class JobAlreadyExistsError(ValueError):
    """Raised when attempting to create a job with an existing ID."""


class JobManager:
    """Manages video processing jobs with SQLite persistence.

    Jobs are stored in a SQLite database and can be queried by ID,
    status, or creation time. Thread-safe via threading lock.

    Usage:
        manager = JobManager(db_path="jobs.db")
        job = manager.create_job(source, operations=["transcript", "audio-context"])
        manager.update_progress(job.job_id, "transcript", 50)
        manager.complete_job(job.job_id)
        manager.cancel_job(another_job_id)
        jobs = manager.list_jobs(status="running")
    """

    def __init__(self, db_path: str | Path = "jobs.db") -> None:
        """Initialize the job manager with a SQLite database.

        Args:
            db_path: Path to the SQLite database file.
        """
        self._db_path = Path(db_path)
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        """Create the jobs table if it doesn't exist."""
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS jobs (
                        job_id TEXT PRIMARY KEY,
                        source_json TEXT NOT NULL,
                        operations TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'pending',
                        progress_json TEXT NOT NULL DEFAULT '{}',
                        created_at_utc TEXT NOT NULL,
                        started_at_utc TEXT,
                        completed_at_utc TEXT,
                        result_path TEXT,
                        error_message TEXT,
                        cancelled_by TEXT,
                        FOREIGN KEY (source_json) REFERENCES sources(job_id)
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_jobs_status
                    ON jobs(status)
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_jobs_created
                    ON jobs(created_at_utc)
                    """
                )
                conn.commit()
            finally:
                conn.close()

    def create_job(
        self,
        source: dict[str, Any],
        operations: list[str],
        job_id: str | None = None,
    ) -> Job:
        """Create a new processing job.

        Args:
            source: Source dictionary (URL, file path, metadata).
            operations: List of operation names to perform.
            job_id: Optional explicit job ID. Auto-generated if not provided.

        Returns:
            The created Job object.

        Raises:
            JobAlreadyExistsError: If the job_id already exists.
        """
        if job_id is None:
            import uuid
            job_id = f"vitk_{uuid.uuid4().hex[:12]}_{int(time.time())}"

        now_utc = datetime.now(timezone.utc).isoformat()

        job_dict = {
            "job_id": job_id,
            "source": source,
            "operations": operations,
            "status": "pending",
            "progress": {
                "current_operation": None,
                "total_operations": len(operations),
                "completed_operations": 0,
                "percent": 0,
            },
            "created_at_utc": now_utc,
            "started_at_utc": None,
            "completed_at_utc": None,
            "result_path": None,
            "error_message": None,
            "cancelled_by": None,
        }

        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                # Check if job exists
                existing = conn.execute(
                    "SELECT 1 FROM jobs WHERE job_id = ?", (job_id,)
                ).fetchone()
                if existing:
                    raise JobAlreadyExistsError(f"Job already exists: {job_id}")

                conn.execute(
                    """
                    INSERT INTO jobs
                    (job_id, source_json, operations, status, progress_json,
                     created_at_utc, started_at_utc, completed_at_utc,
                     result_path, error_message, cancelled_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        job_id,
                        json.dumps(source, ensure_ascii=False),
                        json.dumps(operations),
                        "pending",
                        json.dumps(job_dict["progress"]),
                        now_utc,
                        None,
                        None,
                        None,
                        None,
                        None,
                    ),
                )
                conn.commit()
            finally:
                conn.close()

        job_dict["status"] = "pending"
        return self._dict_to_job(job_dict)

    def get_job(self, job_id: str) -> Job | None:
        """Get a job by ID.

        Args:
            job_id: The job ID to look up.

        Returns:
            Job object or None if not found.
        """
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                row = conn.execute(
                    """
                    SELECT job_id, source_json, operations, status, progress_json,
                           created_at_utc, started_at_utc, completed_at_utc,
                           result_path, error_message, cancelled_by
                    FROM jobs WHERE job_id = ?
                    """,
                    (job_id,),
                ).fetchone()
            finally:
                conn.close()

        if row is None:
            return None

        return self._row_to_job(row)

    def update_progress(
        self,
        job_id: str,
        current_operation: str,
        percent: int,
        message: str | None = None,
    ) -> None:
        """Update job progress.

        Args:
            job_id: The job to update.
            current_operation: Name of the current operation.
            percent: Progress percentage (0-100).
            message: Optional status message.
        """
        job = self.get_job(job_id)
        if job is None:
            raise JobDoesNotExistError(f"Job not found: {job_id}")

        total_ops = len(job.operations)
        completed_ops = int((percent / 100) * total_ops)

        progress = {
            "current_operation": current_operation,
            "total_operations": total_ops,
            "completed_operations": min(completed_ops, total_ops),
            "percent": min(percent, 100),
        }

        if message:
            progress["message"] = message

        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                conn.execute(
                    """
                    UPDATE jobs
                    SET progress_json = ?, status = ?
                    WHERE job_id = ?
                    """,
                    (json.dumps(progress), "running", job_id),
                )
                conn.commit()
            finally:
                conn.close()

    def start_job(self, job_id: str) -> None:
        """Mark a job as started (running)."""
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                conn.execute(
                    """
                    UPDATE jobs
                    SET status = 'running',
                        started_at_utc = ?
                    WHERE job_id = ?
                    """,
                    (datetime.now(timezone.utc).isoformat(), job_id),
                )
                conn.commit()
            finally:
                conn.close()

    def complete_job(
        self,
        job_id: str,
        result_path: str | Path | None = None,
        warnings: list[str] | None = None,
    ) -> None:
        """Mark a job as completed.

        Args:
            job_id: The job to complete.
            result_path: Optional path to the artifacts directory.
            warnings: Optional list of warning messages.
        """
        job = self.get_job(job_id)
        if job is None:
            raise JobDoesNotExistError(f"Job not found: {job_id}")

        completed_at = datetime.now(timezone.utc).isoformat()

        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                conn.execute(
                    """
                    UPDATE jobs
                    SET status = 'completed',
                        completed_at_utc = ?,
                        result_path = ?,
                        progress_json = ?
                    WHERE job_id = ?
                    """,
                    (
                        completed_at,
                        str(result_path) if result_path else None,
                        json.dumps({
                            "percent": 100,
                            "completed_operations": len(job.operations),
                            "current_operation": "complete",
                            "total_operations": len(job.operations),
                            "message": "; ".join(warnings) if warnings else "Completed successfully",
                        }),
                        job_id,
                    ),
                )
                conn.commit()
            finally:
                conn.close()

    def fail_job(
        self,
        job_id: str,
        error_message: str,
        operation: str | None = None,
    ) -> None:
        """Mark a job as failed.

        Args:
            job_id: The job to mark as failed.
            error_message: Description of the error.
            operation: Optional operation that failed.
        """
        job = self.get_job(job_id)
        if job is None:
            raise JobDoesNotExistError(f"Job not found: {job_id}")

        progress = job.progress.copy()
        progress["message"] = error_message
        progress["current_operation"] = operation or progress.get("current_operation")

        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                conn.execute(
                    """
                    UPDATE jobs
                    SET status = 'failed',
                        error_message = ?,
                        progress_json = ?
                    WHERE job_id = ?
                    """,
                    (error_message, json.dumps(progress), job_id),
                )
                conn.commit()
            finally:
                conn.close()

    def cancel_job(self, job_id: str, cancelled_by: str = "user") -> None:
        """Cancel a running job.

        Args:
            job_id: The job to cancel.
            cancelled_by: Who or what cancelled the job.
        """
        job = self.get_job(job_id)
        if job is None:
            raise JobDoesNotExistError(f"Job not found: {job_id}")

        if job.status == "cancelled":
            return

        progress = job.progress.copy()
        progress["message"] = f"Cancelled by {cancelled_by}"

        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                conn.execute(
                    """
                    UPDATE jobs
                    SET status = 'cancelled',
                        cancelled_by = ?,
                        progress_json = ?
                    WHERE job_id = ?
                    """,
                    (cancelled_by, json.dumps(progress), job_id),
                )
                conn.commit()
            finally:
                conn.close()

    def list_jobs(
        self,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Job]:
        """List jobs with optional filtering.

        Args:
            status: Filter by status (pending, running, completed, failed, cancelled).
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of Job objects.
        """
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                query = "SELECT * FROM jobs"
                params: list[Any] = []

                if status:
                    query += " WHERE status = ?"
                    params.append(status)

                query += f" ORDER BY created_at_utc DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])

                rows = conn.execute(query, params).fetchall()
            finally:
                conn.close()

        return [self._row_to_job(row) for row in rows]

    def get_job_count(self, status: str | None = None) -> int:
        """Get the count of jobs, optionally filtered by status.

        Args:
            status: Optional status filter.

        Returns:
            Number of matching jobs.
        """
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                if status:
                    result = conn.execute(
                        "SELECT COUNT(*) FROM jobs WHERE status = ?", (status,)
                    ).fetchone()
                else:
                    result = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()
            finally:
                conn.close()

        return result[0] if result else 0

    def delete_job(self, job_id: str) -> None:
        """Delete a job from the database.

        Args:
            job_id: The job to delete.
        """
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                conn.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
                conn.commit()
            finally:
                conn.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_job(row: tuple) -> Job:
        """Convert a database row to a Job object."""
        (
            job_id,
            source_json,
            operations_json,
            status,
            progress_json,
            created_at,
            started_at,
            completed_at,
            result_path,
            error_message,
            cancelled_by,
        ) = row

        source = json.loads(source_json)
        operations = json.loads(operations_json)
        progress = json.loads(progress_json) if progress_json else {}

        return Job(
            job_id=job_id,
            source=source,
            operations=operations,
            status=status,
            progress=progress,
            created_at_utc=created_at,
            started_at_utc=started_at,
            completed_at_utc=completed_at,
            result_path=result_path,
            error_message=error_message,
            cancelled_by=cancelled_by,
        )

    @staticmethod
    def _dict_to_job(d: dict[str, Any]) -> Job:
        """Convert a dictionary to a Job object."""
        return Job(
            job_id=d["job_id"],
            source=d["source"],
            operations=d["operations"],
            status=d.get("status", "pending"),
            progress=d.get("progress", {}),
            created_at_utc=d["created_at_utc"],
            started_at_utc=d.get("started_at_utc"),
            completed_at_utc=d.get("completed_at_utc"),
            result_path=d.get("result_path"),
            error_message=d.get("error_message"),
            cancelled_by=d.get("cancelled_by"),
        )


# Module-level singleton for simple usage
_default_manager: JobManager | None = None
_default_lock = threading.Lock()


def get_default_manager(db_path: str | Path = "jobs.db") -> JobManager:
    """Get or create the default JobManager singleton.

    Args:
        db_path: Path to the SQLite database.

    Returns:
        The default JobManager instance.
    """
    global _default_manager
    if _default_manager is None:
        with _default_lock:
            if _default_manager is None:
                _default_manager = JobManager(db_path=db_path)
    return _default_manager
