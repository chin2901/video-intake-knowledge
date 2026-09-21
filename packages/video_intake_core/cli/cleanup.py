"""
Cleanup command for video-intake-knowledge.

Manages storage cleanup operations.
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass
from pathlib import Path

from video_intake_core.storage import StorageManager

logger = logging.getLogger(__name__)


@dataclass
class StorageCleanupResult:
    """Result of a storage cleanup operation."""
    cache_cleared_bytes: int
    cache_cleared_human: str
    jobs_cleared: int
    jobs_cleared_human: str
    total_freed_bytes: int
    total_freed_human: str
    success: bool = True
    error: str | None = None


def run_storage_cleanup(args: argparse.Namespace) -> int:
    """Execute the cleanup command."""
    storage_root = Path(args.storage_root).resolve()
    retention_days = args.retention_days
    max_storage_gb = args.max_storage_gb
    confirm = args.yes

    if not storage_root.exists():
        print(f"Storage root does not exist: {storage_root}")
        return 1

    manager = StorageManager(
        storage_root=storage_root,
        retention_days=retention_days,
        max_storage_gb=max_storage_gb,
    )

    print(f"Cleaning up storage at: {storage_root}")
    print(f"  Retention: {retention_days} days")
    print(f"  Max storage: {max_storage_gb} GB")
    print()

    if not confirm:
        print("This will delete old artifacts. Use --yes to confirm.")
        return 1

    result = manager.clear_all(confirm=True)

    print("Cleanup complete:")
    print(f"  Cache cleared: {result['cache_cleared_human']} ({result['cache_cleared_bytes']} bytes)")
    print(f"  Jobs cleared: {result['jobs_cleared']} ({result['jobs_cleared_human']})")
    print(f"  Total freed: {result['total_freed_human']}")

    return 0


# ----------------------------------------------------------------------
# Contract API
# ----------------------------------------------------------------------


def cleanup_storage(
    storage_root: str | Path,
    retention_days: int = 30,
    max_storage_gb: float = 10.0,
) -> StorageCleanupResult:
    """Clean up old artifacts and cache (contract API).

    Args:
        storage_root: Root directory for artifact storage.
        retention_days: Days to keep artifacts before cleanup.
        max_storage_gb: Maximum storage in GB.

    Returns:
        StorageCleanupResult with cleanup statistics.
    """
    storage_root = Path(storage_root).resolve()
    if not storage_root.exists():
        return StorageCleanupResult(
            cache_cleared_bytes=0,
            cache_cleared_human="0 B",
            jobs_cleared=0,
            jobs_cleared_human="0 B",
            total_freed_bytes=0,
            total_freed_human="0 B",
            success=False,
            error=f"Storage root does not exist: {storage_root}",
        )

    manager = StorageManager(
        storage_root=storage_root,
        retention_days=retention_days,
        max_storage_gb=max_storage_gb,
    )

    result = manager.clear_all(confirm=True)

    return StorageCleanupResult(
        cache_cleared_bytes=result.get("cache_cleared_bytes", 0),
        cache_cleared_human=result.get("cache_cleared_human", "0 B"),
        jobs_cleared=result.get("jobs_cleared", 0),
        jobs_cleared_human=result.get("jobs_cleared_human", "0 B"),
        total_freed_bytes=result.get("total_freed_bytes", 0),
        total_freed_human=result.get("total_freed_human", "0 B"),
        success=True,
    )


def cleanup_command(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """Add the cleanup subcommand to the parser."""
    parser = subparsers.add_parser("cleanup", help="Clean up old artifacts and cache")
    parser.add_argument(
        "--storage-root",
        default="./artifacts",
        help="Root directory for artifact storage (default: ./artifacts)",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=30,
        help="Days to keep artifacts before cleanup (default: 30)",
    )
    parser.add_argument(
        "--max-storage-gb",
        type=float,
        default=10.0,
        help="Maximum storage in GB (default: 10.0)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm cleanup without prompting",
    )
    parser.set_defaults(func=run_storage_cleanup)
    return parser
