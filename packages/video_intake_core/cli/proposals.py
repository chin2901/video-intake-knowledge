"""
Proposals command for video-intake-knowledge.

Manages and displays build proposals.
"""

from __future__ import annotations

import argparse
import logging

logger = logging.getLogger(__name__)


def show_proposals(args: argparse.Namespace) -> int:
    """Execute the proposals command."""
    print("Build proposals feature not yet implemented.")
    print("Use 'video-intake extract' to process videos and generate proposals.")
    return 0


def proposals_command(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """Add the proposals subcommand to the parser."""
    parser = subparsers.add_parser("proposals", help="Show build proposals")
    parser.add_argument("--job-id", help="Job ID to show proposals for")
    parser.set_defaults(func=show_proposals)
    return parser
