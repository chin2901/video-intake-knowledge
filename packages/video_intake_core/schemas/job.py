"""
Job data model for video_intake_knowledge.

Defines the Job class used by the job management system.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class JobStatus(str, Enum):
    """Job status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Import Source from the source module
from .source import Source, SourceType


class Job:
    """Video processing job definition.

    Attributes:
        job_id: Unique job identifier in format vitk_<hash>_<uuid>.
        source: The video source to process.
        operations: Requested operations for this job.
        status: Current job status (pending, running, completed, failed, cancelled).
        progress: Progress tracking information.
        created_at_utc: When the job was created (ISO 8601 UTC).
        started_at_utc: When the job started processing (ISO 8601 UTC).
        completed_at_utc: When the job completed (ISO 8601 UTC).
        result_path: Path to artifacts directory.
        error_message: Error message if the job failed.
        cancelled_by: User or system that cancelled the job.
    """

    def __init__(
        self,
        job_id: Optional[str] = None,
        source: Optional[Source] = None,
        operations: Optional[list[str]] = None,
        status: JobStatus = JobStatus.PENDING,
        progress: Optional[dict[str, Any]] = None,
        created_at_utc: Optional[str] = None,
        started_at_utc: Optional[str] = None,
        completed_at_utc: Optional[str] = None,
        result_path: Optional[str] = None,
        error_message: Optional[str] = None,
        cancelled_by: Optional[str] = None,
    ) -> None:
        """Initialize a new Job.

        Args:
            job_id: Unique job identifier. Auto-generated if not provided.
            source: The video source to process.
            operations: Requested operations (e.g., ["transcript", "audio-context"]).
            status: Initial job status (default: pending).
            progress: Initial progress tracking (optional).
            created_at_utc: Creation timestamp (auto-generated if not provided).
            started_at_utc: Start timestamp (set when job starts).
            completed_at_utc: Completion timestamp (set when job completes).
            result_path: Path to artifacts directory.
            error_message: Error message if the job failed.
            cancelled_by: User or system that cancelled the job.
        """
        self.job_id = job_id or self._generate_job_id(source)
        self.source = source
        self.operations = operations or []
        self.status = status
        self.progress = progress or {
            "current_operation": None,
            "total_operations": len(self.operations) if self.operations else 0,
            "completed_operations": 0,
            "percent": 0,
        }
        self.created_at_utc = created_at_utc or datetime.now(timezone.utc).isoformat()
        self.started_at_utc = started_at_utc
        self.completed_at_utc = completed_at_utc
        self.result_path = result_path
        self.error_message = error_message
        self.cancelled_by = cancelled_by

    @staticmethod
    def _generate_job_id(source: Optional[Source] = None) -> str:
        """Generate a unique job ID based on source URL hash and UUID."""
        if source and source.url:
            source_hash = hashlib.sha256(source.url.encode()).hexdigest()[:12]
        else:
            source_hash = hashlib.sha256(b"unknown").hexdigest()[:12]
        return f"vitk_{source_hash}_{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict[str, Any]:
        """Convert job to dictionary (for serialization/storage)."""
        return {
            "job_id": self.job_id,
            "source": {
                "source_type": self.source.source_type.value if self.source else None,
                "url": self.source.url if self.source else None,
                "raw_url": self.source.raw_url if self.source else None,
                "platform": self.source.platform if self.source else None,
                "title": self.source.title if self.source else None,
                "author": self.source.author if self.source else None,
                "duration_seconds": self.source.duration_seconds if self.source else None,
                "thumbnail_url": self.source.thumbnail_url if self.source else None,
                "metadata": self.source.metadata if self.source else None,
            } if self.source else None,
            "operations": self.operations,
            "status": self.status.value if isinstance(self.status, JobStatus) else self.status,
            "progress": self.progress,
            "created_at_utc": self.created_at_utc,
            "started_at_utc": self.started_at_utc,
            "completed_at_utc": self.completed_at_utc,
            "result_path": self.result_path,
            "error_message": self.error_message,
            "cancelled_by": self.cancelled_by,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Job":
        """Create a Job from a dictionary."""
        source_data = data.get("source")
        source = None
        if source_data:
            source = Source(
                source_type=SourceType(source_data.get("source_type", "local_file")),
                url=source_data.get("url", ""),
                raw_url=source_data.get("raw_url"),
                platform=source_data.get("platform", ""),
                title=source_data.get("title"),
                author=source_data.get("author"),
                duration_seconds=source_data.get("duration_seconds"),
                thumbnail_url=source_data.get("thumbnail_url"),
                metadata=source_data.get("metadata"),
            )

        status = data.get("status", "pending")
        if isinstance(status, str):
            status = JobStatus(status)

        return cls(
            job_id=data.get("job_id"),
            source=source,
            operations=data.get("operations", []),
            status=status,
            progress=data.get("progress"),
            created_at_utc=data.get("created_at_utc"),
            started_at_utc=data.get("started_at_utc"),
            completed_at_utc=data.get("completed_at_utc"),
            result_path=data.get("result_path"),
            error_message=data.get("error_message"),
            cancelled_by=data.get("cancelled_by"),
        )

    def __repr__(self) -> str:
        return f"Job(job_id={self.job_id!r}, status={self.status.value})"

    def __str__(self) -> str:
        return f"Job {self.job_id} ({self.status.value})"


__all__ = ["Job", "JobStatus"]
