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
from typing import Any, Optional

from ..schemas.job import Job, JobStatus, JobState


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
        source: dict[str, Any] | None = None,
        operations: list[str] | None = None,
        job_id: str | None = None,
        video_path: str | None = None,
        source_type: str | None = None,
        selected_operations: list[str] | None = None,
    ) -> Job:
        """Create a new processing job.

        Supports both new API (source, operations) and legacy API
        (video_path, source_type, selected_operations).

        Args:
            source: Source dictionary (URL, file path, metadata).
            operations: List of operation names to perform.
            job_id: Optional explicit job ID. Auto-generated if not provided.
            video_path: Video URL or path (legacy).
            source_type: Source type string (legacy).
            selected_operations: List of operations (legacy).

        Returns:
            The created Job object.

        Raises:
            JobAlreadyExistsError: If the job_id already exists.
        """
        # Handle legacy API
        if video_path is not None and source is None:
            source = {
                "url": video_path,
                "type": source_type or "local",
            }
        if selected_operations is not None and operations is None:
            operations = selected_operations
        if operations is None:
            operations = ["transcript"]
        if source is None:
            source = {"url": "", "type": "local"}
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
        current_operation: str | float,
        percent: int | str | None = None,
        message: str | None = None,
    ) -> None:
        """Update job progress.

        Supports both:
        - Modern API: update_progress(job_id, "transcript", 50)
        - Legacy API: update_progress(job_id, 50.0, current_phase="downloading")
        """
        job = self.get_job(job_id)
        if job is None:
            raise JobDoesNotExistError(f"Job not found: {job_id}")

        # Detect legacy API: first arg is float progress, second is current_phase kwarg
        if isinstance(current_operation, (int, float)) and percent is None:
            # Legacy API: update_progress(job_id, progress: float, current_phase: str | None = None)
            progress_value = float(current_operation)
            current_phase = percent  # percent is actually current_phase in legacy call
            message = current_phase

            # Update job's internal progress
            job.progress = progress_value
            if current_phase:
                job.current_phase = current_phase

            progress_dict = {
                "current_operation": current_phase,
                "total_operations": len(job.operations) if job.operations else 0,
                "completed_operations": int((progress_value / 100) * len(job.operations)) if job.operations else 0,
                "percent": min(max(progress_value, 0), 100),
            }
            if current_phase:
                progress_dict["message"] = current_phase

        else:
            # Modern API: update_progress(job_id, current_operation, percent)
            operation_name = str(current_operation)
            progress_value = int(percent) if percent is not None else 0

            total_ops = len(job.operations)
            completed_ops = int((progress_value / 100) * total_ops)

            progress_dict = {
                "current_operation": operation_name,
                "total_operations": total_ops,
                "completed_operations": min(completed_ops, total_ops),
                "percent": min(progress_value, 100),
            }

            if message:
                progress_dict["message"] = message

            # Update job's internal progress dict
            if hasattr(job, '_progress') and isinstance(job._progress, dict):
                job._progress.update(progress_dict)
            else:
                job._progress = progress_dict

        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                conn.execute(
                    """
                    UPDATE jobs
                    SET progress_json = ?, status = ?
                    WHERE job_id = ?
                    """,
                    (json.dumps(progress_dict), "running", job_id),
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

        # Handle both dict and float progress
        if isinstance(job.progress, dict):
            progress = job.progress.copy()
        else:
            progress = {
                "current_operation": getattr(job, 'current_phase', None),
                "total_operations": len(job.operations) if job.operations else 0,
                "completed_operations": 0,
                "percent": float(job.progress) if job.progress else 0.0,
            }
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

                query += " ORDER BY created_at_utc ASC LIMIT ? OFFSET ?"
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
    # Legacy API methods (for test compatibility)
    # ------------------------------------------------------------------

    def update_progress(self, job_id: str, progress: float, current_phase: str | None = None) -> None:
        """Update job progress (legacy API).

        Args:
            job_id: The job to update.
            progress: Progress percentage (0-100).
            current_phase: Optional current phase name.
        """
        job = self.get_job(job_id)
        if job is None:
            raise JobDoesNotExistError(f"Job not found: {job_id}")

        # Update job's internal progress
        job.progress = progress
        if current_phase:
            job.current_phase = current_phase

        # Persist to database
        progress_dict = {
            "current_operation": current_phase,
            "total_operations": len(job.operations) if job.operations else 0,
            "completed_operations": int((progress / 100) * len(job.operations)) if job.operations else 0,
            "percent": min(max(float(progress), 0), 100),
        }
        if current_phase:
            progress_dict["message"] = current_phase

        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                conn.execute(
                    """
                    UPDATE jobs
                    SET progress_json = ?, status = ?
                    WHERE job_id = ?
                    """,
                    (json.dumps(progress_dict), "running", job_id),
                )
                conn.commit()
            finally:
                conn.close()

    def update_status(self, job_id: str, state: str, completed_at: str | None = None) -> None:
        """Update job status (legacy API).

        Args:
            job_id: The job to update.
            state: New state (waiting, running, completed, failed, cancelled).
            completed_at: Optional completion timestamp (ISO format).
        """
        job = self.get_job(job_id)
        if job is None:
            raise JobDoesNotExistError(f"Job not found: {job_id}")

        # Map legacy state to internal status
        state_map = {
            "waiting": "pending",
            "running": "running",
            "completed": "completed",
            "failed": "failed",
            "cancelled": "cancelled",
        }
        internal_status = state_map.get(state, state)

        # Convert datetime to ISO string if it's a datetime object (to avoid deprecation warning)
        if completed_at is not None and hasattr(completed_at, 'isoformat'):
            completed_at = completed_at.isoformat()

        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                if completed_at:
                    conn.execute(
                        """
                        UPDATE jobs
                        SET status = ?, completed_at_utc = ?
                        WHERE job_id = ?
                        """,
                        (internal_status, completed_at, job_id),
                    )
                else:
                    conn.execute(
                        """
                        UPDATE jobs
                        SET status = ?
                        WHERE job_id = ?
                        """,
                        (internal_status, job_id),
                    )
                conn.commit()
            finally:
                conn.close()

    def remove_job(self, job_id: str) -> None:
        """Remove a job from the database (legacy API alias)."""
        self.delete_job(job_id)

    def cleanup_completed(self, max_age_days: int = 30) -> int:
        """Clean up completed jobs older than max_age_days.

        Args:
            max_age_days: Maximum age in days for completed jobs to keep.

        Returns:
            Number of jobs removed.
        """
        from datetime import datetime, timedelta

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        cutoff_iso = cutoff_date.isoformat()

        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                # First, get the job IDs to be deleted
                cursor = conn.execute(
                    """
                    SELECT job_id FROM jobs
                    WHERE status = 'completed' AND completed_at_utc < ?
                    """,
                    (cutoff_iso,),
                )
                job_ids = [row[0] for row in cursor.fetchall()]

                if job_ids:
                    placeholders = ",".join("?" * len(job_ids))
                    conn.execute(
                        f"DELETE FROM jobs WHERE job_id IN ({placeholders})",
                        job_ids,
                    )
                    conn.commit()

                return len(job_ids)
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


# ----------------------------------------------------------------------
# Convenience functions using default manager
# ----------------------------------------------------------------------


def create_job(
    video_path: str | None = None,
    source_type: str | None = None,
    selected_operations: list[str] | None = None,
    source: dict[str, Any] | None = None,
    operations: list[str] | None = None,
    db_path: str | Path = "jobs.db",
    **kwargs: Any,
) -> Job:
    """Create a new job with the default manager.

    Supports both legacy API (video_path, source_type, selected_operations)
    and new API (source, operations).

    Args:
        video_path: Video URL or path (legacy).
        source_type: Source type string (legacy).
        selected_operations: List of operations (legacy).
        source: Source dictionary (new API).
        operations: List of operations (new API).
        db_path: Path to the SQLite database.
        **kwargs: Additional arguments passed to JobManager.create_job.

    Returns:
        The created Job instance.
    """
    # Handle legacy API
    if video_path is not None and source is None:
        source = {
            "url": video_path,
            "type": source_type or "local",
        }
    if selected_operations is not None and operations is None:
        operations = selected_operations
    if operations is None:
        operations = ["transcript"]
    if source is None:
        source = {"url": "", "type": "local"}

    manager = get_default_manager(db_path)
    return manager.create_job(source=source, operations=operations, **kwargs)


def start_job(job_id: str, db_path: str | Path = "jobs.db") -> Job:
    """Start a job by ID using the default manager.

    Args:
        job_id: The job ID to start.
        db_path: Path to the SQLite database.

    Returns:
        The started Job instance.
    """
    manager = get_default_manager(db_path)
    return manager.start_job(job_id)


def cancel_job(job_id: str, db_path: str | Path = "jobs.db", cancelled_by: str = "system") -> Job:
    """Cancel a job by ID using the default manager.

    Args:
        job_id: The job ID to cancel.
        db_path: Path to the SQLite database.
        cancelled_by: Who cancelled the job.

    Returns:
        The cancelled Job instance.
    """
    manager = get_default_manager(db_path)
    return manager.cancel_job(job_id, cancelled_by=cancelled_by)


def get_job(job_id: str) -> Job:
    """Get a job by ID using the default manager.

    Args:
        job_id: The job ID to get.

    Returns:
        The Job instance.
    """
    manager = get_default_manager(_DEFAULT_DB_PATH)
    return manager.get_job(job_id)


# ----------------------------------------------------------------------
# Contract API functions (expected public API)
# ----------------------------------------------------------------------


# Module-level default database path
_DEFAULT_DB_PATH = "jobs.db"


def create_job(source_url: str, title: str, source_type: str = "youtube") -> Job:
    """Create a new job with the expected contract API.

    Args:
        source_url: The video source URL.
        title: Title of the video.
        source_type: Type of source (youtube, facebook, instagram, tiktok, local).

    Returns:
        The created Job instance.
    """
    source = {"url": source_url, "type": source_type}
    operations = ["transcript"]
    manager = get_default_manager(_DEFAULT_DB_PATH)
    return manager.create_job(source=source, operations=operations)


def start_job(job: Job, selections: list[str] | None = None) -> Job:
    """Start a job with the expected contract API.

    Args:
        job: The Job instance to start.
        selections: Optional list of operations to run.

    Returns:
        The started Job instance.
    """
    manager = get_default_manager(_DEFAULT_DB_PATH)
    if selections:
        # Update job operations if provided
        pass
    manager.start_job(job.job_id)
    return manager.get_job(job.job_id)


def cancel_job(job_id: str) -> bool:
    """Cancel a job by ID with the expected contract API.

    Args:
        job_id: The job ID to cancel.

    Returns:
        True if cancelled, False if not found.
    """
    manager = get_default_manager(_DEFAULT_DB_PATH)
    try:
        manager.cancel_job(job_id)
        return True
    except Exception:
        return False


def list_jobs(status: str | None = None) -> list[Job]:
    """List jobs with optional status filter.

    Args:
        status: Optional status filter.

    Returns:
        List of Job instances.
    """
    manager = get_default_manager(_DEFAULT_DB_PATH)
    return manager.list_jobs(status=status)


__all__ = [
    "Job",
    "JobStatus",
    "JobState",
    "JobDoesNotExistError",
    "JobAlreadyExistsError",
    "JobManager",
    "get_default_manager",
    "create_job",
    "start_job",
    "cancel_job",
    "get_job",
    "list_jobs",
]
