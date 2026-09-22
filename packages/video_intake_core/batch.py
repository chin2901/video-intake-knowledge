"""
video_intake_core.batch — Concurrent batch processing engine.

Provides multi-worker concurrent execution for processing manifests of video sources
(URLs and local files) with SQLite job tracking, progress emission, and error handling.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import logging
import sys
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from video_intake_core.acquisition import detect_source
from video_intake_core.jobs import JobManager, JobState

logger = logging.getLogger(__name__)


@dataclass
class BatchResult:
    """Result of a batch processing run."""

    total: int = 0
    successful: int = 0
    failed: int = 0
    jobs: list[dict[str, Any]] = field(default_factory=list)
    manifest_path: str = ""
    output_dir: str = ""
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary representation."""
        return asdict(self)


class BatchRunner:
    """Manages concurrent batch execution across worker threads."""

    def __init__(
        self,
        max_workers: int = 4,
        output_dir: Path | str = "./artifacts",
        db_path: Path | str | None = None,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.max_workers = max(1, int(max_workers))
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if db_path is None:
            self.db_path = Path.home() / ".video-intake" / "jobs.db"
        else:
            self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.job_manager = JobManager(db_path=self.db_path)
        self.progress_callback = progress_callback

    def _process_entry(
        self,
        entry: dict[str, Any],
        index: int,
        total: int,
    ) -> dict[str, Any]:
        """Process a single video entry in a worker thread."""
        target = entry.get("url") or entry.get("file") or entry.get("path") or ""
        if not target:
            return {
                "index": index,
                "status": "failed",
                "error": "Missing URL or file in entry",
            }

        title = entry.get("title") or Path(target.replace("file://", "")).stem or f"batch_video_{index}"
        from video_intake_core.orchestrator import check_and_extract, parse_extraction_choices
        select_raw = entry.get("select") or entry.get("operations") or "6"
        operations = parse_extraction_choices(str(select_raw))

        # Detect source
        source_obj = detect_source(target)
        is_local = target.startswith("file://") or Path(target).exists()
        source_dict = {
            "url": target,
            "resolved_url": source_obj.url if source_obj else target,
            "platform": source_obj.platform if source_obj else ("local" if is_local else "remote"),
            "title": title,
            "is_local": is_local or (source_obj.source_type.value == "local_file" if source_obj else False),
        }

        # Create job in JobManager
        created_job = self.job_manager.create_job(
            source=source_dict,
            operations=[str(op) for op in operations],
        )
        job_id = created_job.job_id
        self.job_manager.update_status(job_id, JobState.RUNNING)

        if self.progress_callback:
            self.progress_callback({
                "job_id": job_id,
                "index": index,
                "total": total,
                "title": title,
                "status": "running",
            })

        try:
            artifacts = check_and_extract(
                sources=[source_dict],
                operations=operations,
                output_dir=self.output_dir,
                db_path=self.db_path,
                job_id=job_id,
            )
            self.job_manager.update_progress(job_id, 100.0, current_phase="completed")
            self.job_manager.update_status(job_id, JobState.COMPLETED)

            if self.progress_callback:
                self.progress_callback({
                    "job_id": job_id,
                    "index": index,
                    "total": total,
                    "title": title,
                    "status": "completed",
                })

            return {
                "job_id": job_id,
                "index": index,
                "status": "completed",
                "title": title,
                "target": target,
                "artifacts": artifacts,
            }
        except Exception as exc:
            logger.error("Error processing entry %s: %s", target, exc)
            self.job_manager.update_status(job_id, JobState.FAILED)
            if self.progress_callback:
                self.progress_callback({
                    "job_id": job_id,
                    "index": index,
                    "total": total,
                    "title": title,
                    "status": "failed",
                    "error": str(exc),
                })
            return {
                "job_id": job_id,
                "index": index,
                "status": "failed",
                "title": title,
                "target": target,
                "error": str(exc),
            }


def run_batch(
    manifest_path: Path | str,
    max_workers: int = 4,
    output_dir: Path | str = "./artifacts",
    db_path: Path | str | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> BatchResult:
    """Execute concurrent batch processing for a given manifest file.

    Args:
        manifest_path: Path to YAML or JSON manifest file.
        max_workers: Maximum parallel worker threads.
        output_dir: Base directory for storing extracted artifacts.
        db_path: Path to SQLite jobs database (defaults to ~/.video-intake/jobs.db).
        progress_callback: Optional callback receiving progress events.

    Returns:
        BatchResult summarizing overall execution and job statuses.
    """
    m_path = Path(manifest_path).resolve()
    if not m_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    start_time = time.perf_counter()

    # Parse manifest
    if m_path.suffix.lower() in (".yaml", ".yml"):
        import yaml
        with open(m_path, encoding="utf-8") as f:
            manifest_data = yaml.safe_load(f)
    else:
        with open(m_path, encoding="utf-8") as f:
            manifest_data = json.load(f)

    if isinstance(manifest_data, dict):
        entries = manifest_data.get("videos") or manifest_data.get("entries") or manifest_data.get("items") or []
    elif isinstance(manifest_data, list):
        entries = manifest_data
    else:
        entries = []

    # Normalize entries
    normalized_entries: list[dict[str, Any]] = []
    for raw_e in entries:
        if isinstance(raw_e, str):
            normalized_entries.append({"url": raw_e, "select": "6"})
        elif isinstance(raw_e, dict):
            normalized_entries.append(raw_e)

    total_entries = len(normalized_entries)
    if total_entries == 0:
        return BatchResult(
            total=0,
            successful=0,
            failed=0,
            jobs=[],
            manifest_path=str(m_path),
            output_dir=str(Path(output_dir).resolve()),
            duration_seconds=0.0,
        )

    runner = BatchRunner(
        max_workers=max_workers,
        output_dir=output_dir,
        db_path=db_path,
        progress_callback=progress_callback,
    )

    jobs_results: list[dict[str, Any]] = []
    successful = 0
    failed = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=runner.max_workers) as executor:
        future_to_entry = {
            executor.submit(runner._process_entry, entry, idx, total_entries): idx
            for idx, entry in enumerate(normalized_entries, 1)
        }
        for future in concurrent.futures.as_completed(future_to_entry):
            try:
                res = future.result()
                jobs_results.append(res)
                if res.get("status") == "completed":
                    successful += 1
                else:
                    failed += 1
            except Exception as exc:
                idx = future_to_entry[future]
                failed += 1
                jobs_results.append({
                    "index": idx,
                    "status": "failed",
                    "error": str(exc),
                })

    jobs_results.sort(key=lambda x: x.get("index", 0))
    duration = time.perf_counter() - start_time

    return BatchResult(
        total=total_entries,
        successful=successful,
        failed=failed,
        jobs=jobs_results,
        manifest_path=str(m_path),
        output_dir=str(runner.output_dir),
        duration_seconds=round(duration, 3),
    )


def cmd_batch(args: argparse.Namespace) -> int:
    """CLI subcommand entrypoint for running batch manifests."""
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"Manifiesto no encontrado: {manifest_path}", file=sys.stderr)
        return 1

    max_workers = getattr(args, "parallel", None) or getattr(args, "max_parallel_jobs", None) or 4
    output_dir = getattr(args, "output", None) or "./artifacts"

    def _cli_progress(event: dict[str, Any]) -> None:
        if not getattr(args, "json", False):
            print(f"  [{event.get('index')}/{event.get('total')}] {event.get('title')} -> {event.get('status').upper()}")

    if not getattr(args, "json", False):
        print(f"Iniciando procesamiento por lotes ({max_workers} hilos)...")

    result = run_batch(
        manifest_path=manifest_path,
        max_workers=max_workers,
        output_dir=output_dir,
        progress_callback=_cli_progress,
    )

    if getattr(args, "json", False):
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(f"\nLote completado en {result.duration_seconds:.2f}s: {result.successful}/{result.total} procesados con éxito.")
        if result.failed > 0:
            print(f"  ✗ {result.failed} fallo(s) detectado(s).", file=sys.stderr)

    return 0 if result.failed == 0 else 1
