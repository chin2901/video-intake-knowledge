"""
Status command for video-intake-knowledge.

Shows job status and progress.
"""

from __future__ import annotations

import argparse
import logging

from video_intake_core.jobs import JobStatus, get_job, list_jobs

logger = logging.getLogger(__name__)


def run_status(args: argparse.Namespace) -> int:
    """Execute the status command."""
    if args.job_id:
        job = get_job(args.job_id)
        if job is None:
            print(f"Job not found: {args.job_id}")
            return 1

        print(f"Job: {job.job_id}")
        print(f"  Status: {job.status.value}")
        print(f"  Created: {job.created_at_utc}")
        if job.started_at_utc:
            print(f"  Started: {job.started_at_utc}")
        if job.completed_at_utc:
            print(f"  Completed: {job.completed_at_utc}")
        print(f"  Operations: {', '.join(job.operations)}")

        if job.progress:
            prog = job.progress
            print(f"  Progress: {prog.get('percent', 0)}% ({prog.get('completed_operations', 0)}/{prog.get('total_operations', 0)})")
            if prog.get("current_operation"):
                print(f"  Current: {prog['current_operation']}")
            if prog.get("message"):
                print(f"  Message: {prog['message']}")

        if job.error_message:
            print(f"  Error: {job.error_message}")
        if job.result_path:
            print(f"  Result: {job.result_path}")

        return 0

    # List jobs
    jobs = list_jobs(status=args.status, limit=args.limit)
    if not jobs:
        print("No jobs found")
        return 0

    print(f"Jobs ({len(jobs)} found):")
    print()
    for job in jobs:
        status_str = job.status.value
        if job.progress:
            status_str += f" [{job.progress.get('percent', 0)}%]"
        print(f"  {job.job_id} - {status_str} - {', '.join(job.operations)}")

    return 0


def status_command(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """Add the status subcommand to the parser."""
    parser = subparsers.add_parser("status", help="Show job status")
    parser.add_argument("job_id", nargs="?", help="Job ID to show details for")
    parser.add_argument(
        "--status",
        choices=[s.value for s in JobStatus],
        help="Filter by status",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of jobs to show (default: 20)",
    )
    parser.set_defaults(func=run_status)
    return parser
