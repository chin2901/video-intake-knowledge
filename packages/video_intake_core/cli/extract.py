"""
Extract command for video-intake-knowledge.

Handles video extraction and processing operations.
"""

from __future__ import annotations

import argparse
import logging

from video_intake_core.acquisition import detect_video_sources
from video_intake_core.jobs import create_job, start_job

logger = logging.getLogger(__name__)


def run_extraction(args: argparse.Namespace) -> int:
    """Execute the extract command."""
    url = args.url
    operations = args.operations or ["transcript", "audio-context", "visual-context"]

    if not url:
        print("Error: URL is required")
        return 1

    print(f"Processing: {url}")
    print(f"Operations: {', '.join(operations)}")
    print()

    # Detect source type
    sources = detect_video_sources(url)
    if not sources:
        print(f"Error: Could not detect source type for URL: {url}")
        return 1

    source_type = sources[0]
    print(f"Detected source: {source_type.value}")

    # Create and start job
    source = {
        "url": url,
        "type": source_type.value,
    }
    job = create_job(source=source, operations=operations, output_dir=args.output)

    print(f"Created job: {job.job_id}")

    if not args.no_wait:
        print("Starting extraction...")
        start_job(job.job_id)
        print("Extraction started. Use 'video-intake status <job_id>' to check progress.")

    return 0


def extract_command(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """Add the extract subcommand to the parser."""
    parser = subparsers.add_parser("extract", help="Extract content from a video URL")
    parser.add_argument("url", help="Video URL to process")
    parser.add_argument(
        "-o", "--output",
        default="./artifacts",
        help="Output directory (default: ./artifacts)",
    )
    parser.add_argument(
        "--operations",
        nargs="+",
        choices=["transcript", "audio-context", "visual-context", "knowledge", "ocr"],
        default=["transcript", "audio-context", "visual-context"],
        help="Operations to perform (default: transcript audio-context visual-context)",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Don't wait for extraction to complete",
    )
    parser.set_defaults(func=run_extraction)
    return parser
