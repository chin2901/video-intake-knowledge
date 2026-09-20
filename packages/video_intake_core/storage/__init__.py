"""
Storage management for video_intake_knowledge.

Manages artifact storage with SHA-256 deduplication, job directory
structure, and cleanup policies.
"""

from __future__ import annotations

import hashlib
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..utils import compute_sha256, sizeof_fmt, sanitize_filename

logger = logging.getLogger(__name__)

ARTIFACT_TYPES = frozenset({
    "manifest.json",
    "source.json",
    "provenance.md",
    "transcript_raw",
    "transcript_timestamped.md",
    "audio_context.md",
    "visual_context.md",
    "extracted_knowledge.md",
    "ocr.json",
    "metadata.json",
    "export.md",
    "export.json",
    "export.html",
})


class StorageManager:
    """Manages artifact storage with deduplication and cleanup.

    Directory structure:
        <storage_root>/
        ├── cache/                  # Downloaded/cached media
        │   ├── <hash_prefix>/
        │   │   └── <hash>.<ext>
        │   └── ...
        ├── jobs/                   # Job artifacts
        │   ├── <job_id>/
        │   │   ├── manifest.json
        │   │   ├── source.json
        │   │   ├── transcript_timestamped.md
        │   │   ├── audio_context.md
        │   │   ├── visual_context.md
        │   │   ├── extracted_knowledge.md
        │   │   ├── transcript_raw/
        │   │   ├── video/
        │   │   ├── audio/
        │   │   ├── frames/
        │   │   ├── ocr.json
        │   │   ├── logs/
        │   │   ├── exports/
        │   │   └── metadata/
        │   └── ...
        └── metadata/               # Global metadata
            └── index.json
    """

    def __init__(
        self,
        storage_root: str | Path,
        retention_days: int = 30,
        max_storage_gb: float = 10.0,
    ) -> None:
        """Initialize the storage manager.

        Args:
            storage_root: Root directory for all artifacts.
            retention_days: Days to keep job artifacts before cleanup.
            max_storage_gb: Maximum total storage in GB.
        """
        self._root = Path(storage_root).resolve()
        self._retention_days = retention_days
        self._max_storage_bytes = int(max_storage_gb * 1024**3)
        self._cache_dir = self._root / "cache"
        self._jobs_dir = self._root / "jobs"
        self._metadata_dir = self._root / "metadata"
        self._metadata_dir.mkdir(parents=True, exist_ok=True)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._jobs_dir.mkdir(parents=True, exist_ok=True)

        # Deduplication index: hash -> canonical path
        self._dedup_index: dict[str, Path] = {}
        self._load_dedup_index()

    def _load_dedup_index(self) -> None:
        """Load the deduplication index from disk if it exists."""
        index_path = self._metadata_dir / "dedup_index.json"
        if index_path.exists():
            import json
            with open(index_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
                self._dedup_index = {
                    k: Path(v) for k, v in raw.items()
                }

    def _save_dedup_index(self) -> None:
        """Persist the deduplication index to disk."""
        import json
        index_path = self._metadata_dir / "dedup_index.json"
        data = {k: str(v) for k, v in self._dedup_index.items()}
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def get_job_dir(self, job_id: str) -> Path:
        """Get the artifact directory for a job.

        Args:
            job_id: The job identifier.

        Returns:
            Path to the job's artifact directory (created if needed).
        """
        job_dir = self._jobs_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir

    def save_artifact(
        self,
        job_id: str,
        artifact_type: str,
        content: bytes | str | Path,
        filename: str | None = None,
    ) -> Path:
        """Save an artifact for a job.

        Args:
            job_id: The job ID.
            artifact_type: Type of artifact (e.g., 'transcript_timestamped.md').
            content: Content to save (bytes, string, or existing file path).
            filename: Optional custom filename. Auto-generated if not provided.

        Returns:
            Path to the saved artifact.

        Raises:
            ValueError: If artifact_type is not recognized.
        """
        if artifact_type not in ARTIFACT_TYPES and not artifact_type.endswith(
            ("md", "json", "html", "txt", "srt", "vtt", "png", "jpg", "jpeg", "webp")
        ):
            logger.warning(
                f"Unknown artifact type: {artifact_type}. Saving anyway."
            )

        job_dir = self.get_job_dir(job_id)

        if filename is None:
            filename = artifact_type

        # Ensure subdirectory for grouped artifacts
        if "/" in artifact_type or artifact_type in {
            "transcript_raw", "video", "audio", "frames",
            "logs", "exports", "metadata",
        }:
            sub_dir = job_dir / artifact_type
            sub_dir.mkdir(parents=True, exist_ok=True)
            dest = sub_dir / (filename or "index")
        else:
            dest = job_dir / filename

        # Write content
        dest.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            dest.write_bytes(content)
        elif isinstance(content, str):
            dest.write_text(content, encoding="utf-8")
        elif isinstance(content, Path):
            shutil.copy2(content, dest)
        else:
            raise TypeError(f"Unsupported content type: {type(content)}")

        logger.info(f"Saved artifact: {dest.relative_to(self._root)}")
        return dest

    def list_artifacts(self, job_id: str) -> list[dict[str, Any]]:
        """List all artifacts for a job.

        Args:
            job_id: The job ID.

        Returns:
            List of dicts with keys: path, type, size_bytes, size_human, relative_path.
        """
        job_dir = self.get_job_dir(job_id)
        if not job_dir.exists():
            return []

        artifacts: list[dict[str, Any]] = []
        for item in sorted(job_dir.rglob("*")):
            if item.is_file() and item != job_dir:
                rel = item.relative_to(job_dir)
                size = item.stat().st_size
                artifacts.append({
                    "path": str(item),
                    "relative_path": str(rel),
                    "type": item.suffix.lstrip(".") or "directory",
                    "size_bytes": size,
                    "size_human": sizeof_fmt(size),
                    "modified": datetime.fromtimestamp(
                        item.stat().st_mtime, tz=timezone.utc
                    ).isoformat(),
                })
        return artifacts

    def get_total_size(self, job_id: str) -> int:
        """Get total size of all artifacts for a job in bytes.

        Args:
            job_id: The job ID.

        Returns:
            Total size in bytes.
        """
        job_dir = self.get_job_dir(job_id)
        if not job_dir.exists():
            return 0
        total = 0
        for item in job_dir.rglob("*"):
            if item.is_file():
                total += item.stat().st_size
        return total

    def get_job_size(self, job_id: str) -> dict[str, Any]:
        """Get detailed size breakdown for a job.

        Args:
            job_id: The job ID.

        Returns:
            Dict with total_bytes, total_human, artifact_count, and per_type breakdown.
        """
        artifacts = self.list_artifacts(job_id)
        total = sum(a["size_bytes"] for a in artifacts)
        by_type: dict[str, int] = {}
        for a in artifacts:
            t = a["type"]
            by_type[t] = by_type.get(t, 0) + a["size_bytes"]

        return {
            "job_id": job_id,
            "total_bytes": total,
            "total_human": sizeof_fmt(total),
            "artifact_count": len(artifacts),
            "by_type": {
                t: {"bytes": b, "human": sizeof_fmt(b)}
                for t, b in sorted(by_type.items())
            },
        }

    def save_with_dedup(
        self,
        content: bytes | Path,
        extension: str = "mp4",
    ) -> Path:
        """Save a file with SHA-256 deduplication.

        If the file content (by hash) already exists in cache, return
        the existing path without copying. Otherwise, copy to cache
        under a hash-based name.

        Args:
            content: Bytes content or path to existing file.
            extension: File extension for the cached file.

        Returns:
            Path to the cached file (existing or new).
        """
        if isinstance(content, Path):
            file_hash = compute_sha256(content)
        elif isinstance(content, bytes):
            file_hash = hashlib.sha256(content).hexdigest()
        else:
            raise TypeError(f"Expected bytes or Path, got {type(content)}")

        if file_hash in self._dedup_index:
            cached_path = self._dedup_index[file_hash]
            if cached_path.exists():
                logger.info(f"Cache hit: {file_hash[:12]}... -> {cached_path.name}")
                return cached_path

        # New content — save to cache
        hash_prefix = file_hash[:3]
        cache_subdir = self._cache_dir / hash_prefix
        cache_subdir.mkdir(parents=True, exist_ok=True)
        cached_path = cache_subdir / f"{file_hash}.{extension}"

        if isinstance(content, Path):
            shutil.copy2(content, cached_path)
        else:
            cached_path.write_bytes(content)

        self._dedup_index[file_hash] = cached_path
        self._save_dedup_index()
        logger.info(f"Cached new file: {file_hash[:12]}... -> {cached_path.name}")
        return cached_path

    def get_storage_usage(self) -> dict[str, Any]:
        """Get overall storage usage statistics.

        Returns:
            Dict with total_bytes, total_human, jobs_count, cache_size,
            jobs_size, and breakdown by job.
        """
        total_bytes = 0
        jobs_info: list[dict[str, Any]] = []
        cache_size = 0

        # Cache size
        if self._cache_dir.exists():
            for item in self._cache_dir.rglob("*"):
                if item.is_file():
                    cache_size += item.stat().st_size

        # Job sizes
        if self._jobs_dir.exists():
            for job_dir in sorted(self._jobs_dir.iterdir()):
                if job_dir.is_dir():
                    job_size = 0
                    for item in job_dir.rglob("*"):
                        if item.is_file():
                            job_size += item.stat().st_size
                    total_bytes += job_size
                    jobs_info.append({
                        "job_id": job_dir.name,
                        "size_bytes": job_size,
                        "size_human": sizeof_fmt(job_size),
                    })

        total_bytes += cache_size
        jobs_info.sort(key=lambda x: x["size_bytes"], reverse=True)

        return {
            "total_bytes": total_bytes,
            "total_human": sizeof_fmt(total_bytes),
            "cache_size_bytes": cache_size,
            "cache_size_human": sizeof_fmt(cache_size),
            "jobs_size_bytes": total_bytes - cache_size,
            "jobs_size_human": sizeof_fmt(total_bytes - cache_size),
            "jobs_count": len(jobs_info),
            "jobs": jobs_info[:20],  # Top 20 largest
            "within_limit": total_bytes <= self._max_storage_bytes,
            "limit_bytes": self._max_storage_bytes,
            "limit_human": sizeof_fmt(self._max_storage_bytes),
            "used_percent": round(
                (total_bytes / self._max_storage_bytes * 100) if self._max_storage_bytes else 0,
                1,
            ),
        }

    def cleanup(
        self,
        max_age_days: int | None = None,
        max_gb: float | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Clean up old or excess artifacts.

        Removes job directories older than max_age_days or when total
        storage exceeds max_gb.

        Args:
            max_age_days: Max age in days (default: self._retention_days).
            max_gb: Max total storage in GB (default: self._max_storage_gb).
            dry_run: If True, only report what would be removed.

        Returns:
            Dict with cleanup stats: removed_jobs, freed_bytes, remaining_jobs.
        """
        max_age = max_age_days if max_age_days is not None else self._retention_days
        max_bytes = int((max_gb if max_gb is not None else self._max_storage_gb) * 1024**3)

        cutoff = datetime.now(timezone.utc).timestamp() - (max_age * 86400)

        to_remove: list[Path] = []
        for job_dir in self._jobs_dir.iterdir():
            if not job_dir.is_dir():
                continue
            mtime = job_dir.stat().st_mtime
            if mtime < cutoff:
                to_remove.append(job_dir)

        # If over storage limit, remove oldest jobs first
        current_usage = self.get_storage_usage()
        if current_usage["total_bytes"] > max_bytes and not dry_run:
            # Sort by mtime, oldest first
            sorted_jobs = sorted(
                [d for d in self._jobs_dir.iterdir() if d.is_dir()],
                key=lambda d: d.stat().st_mtime,
            )
            freed = 0
            for job_dir in sorted_jobs:
                if current_usage["total_bytes"] - freed <= max_bytes:
                    break
                job_size = self.get_total_size(job_dir.name)
                to_remove.append(job_dir)
                freed += job_size

        removed_jobs = []
        freed_bytes = 0

        for job_dir in to_remove:
            if dry_run:
                size = self.get_total_size(job_dir.name)
                removed_jobs.append({
                    "job_id": job_dir.name,
                    "size_bytes": size,
                    "size_human": sizeof_fmt(size),
                    "age_days": round(
                        (datetime.now(timezone.utc).timestamp() - job_dir.stat().st_mtime)
                        / 86400,
                        1,
                    ),
                })
                continue

            size = self.get_total_size(job_dir.name)
            shutil.rmtree(job_dir, ignore_errors=True)
            removed_jobs.append(job_dir.name)
            freed_bytes += size
            logger.info(f"Cleaned up job {job_dir.name}: {sizeof_fmt(size)}")

        remaining = [
            d.name for d in self._jobs_dir.iterdir() if d.is_dir()
        ]

        return {
            "removed_count": len(removed_jobs),
            "removed_jobs": removed_jobs,
            "freed_bytes": freed_bytes,
            "freed_human": sizeof_fmt(freed_bytes),
            "remaining_jobs": remaining,
            "dry_run": dry_run,
            "was_over_limit": current_usage["total_bytes"] > max_bytes,
            "current_usage": current_usage,
        }

    def clear_all(self, confirm: bool = False) -> dict[str, Any]:
        """Clear all stored artifacts. Requires explicit confirmation.

        Args:
            confirm: Must be True to proceed.

        Returns:
            Dict with cleanup stats.
        """
        if not confirm:
            raise ValueError(
                "clear_all requires confirm=True. This will delete all artifacts."
            )

        cache_size = 0
        jobs_size = 0
        jobs_count = 0

        if self._cache_dir.exists():
            for item in self._cache_dir.rglob("*"):
                if item.is_file():
                    cache_size += item.stat().st_size
            shutil.rmtree(self._cache_dir)
            self._cache_dir.mkdir(parents=True)

        if self._jobs_dir.exists():
            for job_dir in self._jobs_dir.iterdir():
                if job_dir.is_dir():
                    jobs_count += 1
                    for item in job_dir.rglob("*"):
                        if item.is_file():
                            jobs_size += item.stat().st_size
                    shutil.rmtree(job_dir, ignore_errors=True)
            self._jobs_dir.mkdir(parents=True)

        self._dedup_index.clear()
        self._save_dedup_index()

        return {
            "cache_cleared_bytes": cache_size,
            "cache_cleared_human": sizeof_fmt(cache_size),
            "jobs_cleared": jobs_count,
            "jobs_cleared_bytes": jobs_size,
            "jobs_cleared_human": sizeof_fmt(jobs_size),
            "total_freed": cache_size + jobs_size,
            "total_freed_human": sizeof_fmt(cache_size + jobs_size),
        }
