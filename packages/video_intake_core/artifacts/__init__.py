
"""
Artifacts module.

Manages the creation, storage, and metadata of extracted artifacts:
transcripts, audio, frames, OCR results, context documents, knowledge
extractions, MDX exports, etc.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from video_intake_core.storage import StorageManager
from video_intake_core.utils import compute_sha256

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ArtifactManager:
    """Manages creation and registration of extraction artifacts.

    Coordinates with StorageManager for persistence and
    provides high-level APIs for creating, retrieving, and
    listing artifacts.
    """

    def __init__(
        self,
        storage_root: str | Path | None = None,
        job_db: str | Path | None = None,
        storage: Optional[StorageManager] = None,
    ):
        if storage is not None:
            self._storage = storage
        elif storage_root is not None:
            self._storage = StorageManager(
                storage_root=storage_root,
                retention_days=30,
                max_storage_gb=10.0,
            )
        else:
            self._storage = StorageManager()

    @property
    def storage(self) -> StorageManager:
        """Get the underlying storage manager."""
        return self._storage

    # ------------------------------------------------------------------
    # Transcript artifacts
    # ------------------------------------------------------------------

    def register_transcript(
        self,
        job_id: str,
        source_url: str,
        source_title: str,
        transcript_text: str,
        language: str = "es",
        confidence: Optional[float] = None,
        method: Optional[str] = None,
        segments: Optional[list[dict[str, Any]]] = None,
    ) -> str:
        """Register a transcript artifact."""
        artifact_id = f"transcript_{compute_sha256(transcript_text[:64])[:16]}"

        path = self._storage.save_artifact(
            job_id,
            "transcript",
            transcript_text,
            filename=f"{source_url.replace('/', '_')[:80]}_transcript",
        )

        self._storage.register_artifact(
            artifact_id=artifact_id,
            job_id=job_id,
            source_url=source_url,
            source_title=source_title,
            storage_path=str(path),
            artifact_type="transcript",
            content_type="text/plain",
            size_bytes=len(transcript_text.encode("utf-8")),
            sha256=compute_sha256(transcript_text),
            metadata={
                "language": language,
                "confidence": confidence,
                "method": method,
                "segments_count": len(segments) if segments else 0,
            },
        )

        logger.info(
            f"Registered transcript artifact {artifact_id}"
            f"({len(transcript_text)} chars, lang={language})"
        )
        return artifact_id

    # ------------------------------------------------------------------
    # Audio artifacts
    # ------------------------------------------------------------------

    def register_audio(
        self,
        job_id: str,
        source_url: str,
        source_title: str,
        audio_path: Path,
        duration_seconds: Optional[float] = None,
        codec: Optional[str] = None,
        sample_rate: Optional[int] = None,
    ) -> str:
        """Register an audio extraction artifact."""
        artifact_id = f"audio_{compute_sha256(audio_path.name)[:16]}"

        metadata: dict[str, Any] = {}
        if duration_seconds is not None:
            metadata["duration_seconds"] = duration_seconds
        if codec:
            metadata["codec"] = codec
        if sample_rate:
            metadata["sample_rate"] = sample_rate

        self._storage.register_artifact(
            artifact_id=artifact_id,
            job_id=job_id,
            source_url=source_url,
            source_title=source_title,
            storage_path=str(audio_path),
            artifact_type="audio",
            content_type="audio/wav",
            size_bytes=audio_path.stat().st_size,
            sha256=compute_sha256(audio_path.read_bytes()),
            metadata=metadata,
        )

        logger.info(
            f"Registered audio artifact {artifact_id}"
            f"({audio_path.stat().st_size} bytes)"
        )
        return artifact_id

    # ------------------------------------------------------------------
    # Frame artifacts
    # ------------------------------------------------------------------

    def register_frames(
        self,
        job_id: str,
        source_url: str,
        source_title: str,
        frame_paths: list[Path],
        method: str = "scene_based",
    ) -> list[str]:
        """Register extracted frame images as artifacts."""
        artifact_ids: list[str] = []

        for idx, frame_path in enumerate(frame_paths):
            artifact_id = (
                f"frame_{compute_sha256(frame_path.name)[:16]}"
            )

            self._storage.register_artifact(
                artifact_id=artifact_id,
                job_id=job_id,
                source_url=source_url,
                source_title=source_title,
                storage_path=str(frame_path),
                artifact_type="frame",
                content_type="image/jpeg",
                size_bytes=frame_path.stat().st_size,
                sha256=compute_sha256(frame_path.read_bytes()),
                metadata={"index": idx, "method": method},
            )
            artifact_ids.append(artifact_id)

        logger.info(
            f"Registered {len(artifact_ids)} frame artifacts for job {job_id}"
        )
        return artifact_ids

    # ------------------------------------------------------------------
    # OCR artifacts
    # ------------------------------------------------------------------

    def register_ocr(
        self,
        job_id: str,
        source_url: str,
        source_title: str,
        ocr_results: list[dict[str, Any]],
        frame_path: Optional[Path] = None,
    ) -> str:
        """Register OCR results as an artifact."""
        content = json.dumps(ocr_results, ensure_ascii=False, indent=2)
        artifact_id = f"ocr_{compute_sha256(content)[:16]}"

        path = self._storage.save_artifact(
            job_id,
            "ocr",
            content,
            filename=f"{source_url.replace('/', '_')[:60]}_ocr",
        )

        all_text: list[str] = []
        total_blocks = 0
        total_confidence = 0.0

        for result in ocr_results:
            blocks = result.get("blocks", [])
            total_blocks += len(blocks)
            for block in blocks:
                total_confidence += block.get("confidence", 0)
                if block.get("text"):
                    all_text.append(block["text"])

        avg_confidence = (
            total_confidence / total_blocks if total_blocks > 0 else 0.0
        )

        self._storage.register_artifact(
            artifact_id=artifact_id,
            job_id=job_id,
            source_url=source_url,
            source_title=source_title,
            storage_path=str(path),
            artifact_type="ocr",
            content_type="application/json",
            size_bytes=len(content.encode("utf-8")),
            sha256=compute_sha256(content),
            metadata={
                "blocks_count": total_blocks,
                "avg_confidence": round(avg_confidence, 2),
                "extracted_text_length": len(" ".join(all_text)),
                "source_frame": str(frame_path) if frame_path else None,
            },
        )

        logger.info(
            f"Registered OCR artifact {artifact_id}"
            f"({total_blocks} blocks, avg conf={avg_confidence:.2f})"
        )
        return artifact_id

    # ------------------------------------------------------------------
    # Context artifacts
    # ------------------------------------------------------------------

    def register_context(
        self,
        job_id: str,
        source_url: str,
        source_title: str,
        context_type: str,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """Register a context document artifact.

        Args:
            context_type: One of 'audio_context', 'visual_context',
                'knowledge_extraction', 'mdx_audio', 'mdx_visual',
                'mdx_knowledge'.
        """
        filename_map = {
            "audio_context": "audio_context",
            "visual_context": "visual_context",
            "knowledge_extraction": "extracted_knowledge",
            "mdx_audio": "audio_context.mdx",
            "mdx_visual": "visual_context.mdx",
            "mdx_knowledge": "extracted_knowledge.mdx",
        }

        safe_type = filename_map.get(context_type, context_type)
        path = self._storage.save_artifact(
            job_id,
            context_type,
            content,
            filename=safe_type,
        )

        artifact_id = (
            f"context_{compute_sha256(content[:64])[:16]}"
        )

        self._storage.register_artifact(
            artifact_id=artifact_id,
            job_id=job_id,
            source_url=source_url,
            source_title=source_title,
            storage_path=str(path),
            artifact_type=context_type,
            content_type="text/markdown",
            size_bytes=len(content.encode("utf-8")),
            sha256=compute_sha256(content),
            metadata=metadata or {},
        )

        logger.info(
            f"Registered context artifact {artifact_id}"
            f"type={context_type} ({len(content)} chars)"
        )
        return artifact_id

    # ------------------------------------------------------------------
    # Video download artifact
    # ------------------------------------------------------------------

    def register_video_download(
        self,
        job_id: str,
        source_url: str,
        source_title: str,
        video_path: Path,
        duration_seconds: Optional[float] = None,
        resolution: Optional[str] = None,
        fmt: Optional[str] = None,
    ) -> str:
        """Register a downloaded video file as an artifact."""
        import mimetypes

        artifact_id = f"video_{compute_sha256(video_path.name)[:16]}"

        mime, _ = mimetypes.guess_type(str(video_path))

        metadata: dict[str, Any] = {
            "content_type": mime or "video/mp4",
            "size_bytes": video_path.stat().st_size,
        }
        if duration_seconds is not None:
            metadata["duration_seconds"] = duration_seconds
        if resolution:
            metadata["resolution"] = resolution
        if fmt:
            metadata["format"] = fmt

        self._storage.register_artifact(
            artifact_id=artifact_id,
            job_id=job_id,
            source_url=source_url,
            source_title=source_title,
            storage_path=str(video_path),
            artifact_type="video",
            content_type=metadata["content_type"],
            size_bytes=metadata["size_bytes"],
            sha256=compute_sha256(video_path.read_bytes()),
            metadata=metadata,
        )

        logger.info(
            f"Registered video artifact {artifact_id}"
            f"({video_path.stat().st_size} bytes)"
        )
        return artifact_id

    # ------------------------------------------------------------------
    # Batch artifact retrieval
    # ------------------------------------------------------------------

    def get_artifacts_for_job(self, job_id: str) -> list[dict[str, Any]]:
        """Get all artifacts for a job."""
        return self._storage.list_artifacts(job_id)

    def cleanup_old_artifacts(
        self,
        max_age_days: int = 90,
        dry_run: bool = False,
    ) -> list[dict[str, Any]]:
        """Clean up old artifacts."""
        return self._storage.cleanup(max_age_days=max_age_days, dry_run=dry_run)


def list_artifacts(job_id: str) -> list[dict[str, Any]]:
    """List all artifacts for a job."""
    from video_intake_core.storage import StorageManager
    mgr = StorageManager()
    artifacts = mgr.list_artifacts(job_id)
    return [
        {
            "path": a.path,
            "size_mb": a.size_bytes / (1024 * 1024),
            "created_at": a.created_at,
            "description": a.description,
        }
        for a in artifacts
    ]


__all__ = ["ArtifactManager", "list_artifacts"]
