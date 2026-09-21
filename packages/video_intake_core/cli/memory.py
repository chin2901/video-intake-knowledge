"""
Memory command for video-intake-knowledge.

Manages the memory bank for extracted knowledge.
"""

from __future__ import annotations

import argparse
import logging

from video_intake_core.memory import create_memory_provider

logger = logging.getLogger(__name__)


def show_memory(args: argparse.Namespace) -> int:
    """Execute the memory command."""
    provider = create_memory_provider("local", db_path=args.db_path)

    if args.list:
        entries = provider.list(limit=args.limit, offset=args.offset)
        if not entries:
            print("No memory entries found.")
            return 0

        print(f"Memory entries ({len(entries)}):")
        for entry in entries:
            print(f"  {entry.id}: {entry.content_type} - {entry.summary[:80]}...")
        return 0

    if args.search:
        entries = provider.search(args.search, limit=args.limit)
        if not entries:
            print(f"No results for: {args.search}")
            return 0

        print(f"Search results for '{args.search}' ({len(entries)}):")
        for entry in entries:
            print(f"  {entry.id}: {entry.content_type} - {entry.summary[:80]}...")
        return 0

    if args.stats:
        stats = provider.get_stats()
        print("Memory Statistics:")
        print(f"  Total entries: {stats['total_entries']}")
        print(f"  By type: {stats['by_type']}")
        print(f"  DB path: {stats['db_path']}")
        return 0

    if args.clear:
        if not args.yes:
            print("Use --yes to confirm clearing all memory.")
            return 1
        count = provider.clear()
        print(f"Cleared {count} memory entries.")
        return 0

    # Default: show stats
    stats = provider.get_stats()
    print("Memory Statistics:")
    print(f"  Total entries: {stats['total_entries']}")
    print(f"  By type: {stats['by_type']}")
    print(f"  DB path: {stats['db_path']}")
    return 0


def memory_command(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """Add the memory subcommand to the parser."""
    parser = subparsers.add_parser("memory", help="Manage memory bank")
    parser.add_argument("--db-path", default="./video_intake_memory.db", help="Database path")
    parser.add_argument("--list", action="store_true", help="List all entries")
    parser.add_argument("--search", help="Search entries by text")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--clear", action="store_true", help="Clear all entries")
    parser.add_argument("--limit", type=int, default=20, help="Limit results")
    parser.add_argument("--offset", type=int, default=0, help="Offset for pagination")
    parser.add_argument("--yes", action="store_true", help="Confirm destructive operations")
    parser.set_defaults(func=show_memory)
    return parser
