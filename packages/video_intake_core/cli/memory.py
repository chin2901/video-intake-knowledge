"""
Memory command for video-intake-knowledge.

Manages the memory bank for extracted knowledge.
"""

from __future__ import annotations

import argparse
import logging

from video_intake_core.memory import MemoryQuery, create_memory_provider

logger = logging.getLogger(__name__)


def show_memory(args: argparse.Namespace) -> int:
    """Execute the memory command."""
    provider = create_memory_provider("local", db_path=args.db_path)

    if getattr(args, "list", False):
        entries = provider.list_entries(limit=args.limit, offset=args.offset)
        if not entries:
            print("No se encontraron entradas de memoria.")
            return 0

        print(f"Entradas de memoria ({len(entries)}):")
        for entry in entries:
            title = entry.source_title or getattr(entry.metadata, "video_title", "") or "Sin título"
            summary_preview = (entry.summary or entry.content or "")[:80]
            eid = entry.id[:8] if entry.id else "unknown"
            print(f"  [{eid}] {entry.content_type} — {title}: {summary_preview}...")
        return 0

    if getattr(args, "search", None):
        query = MemoryQuery(text=args.search, limit=args.limit)
        entries = provider.search_entries(query)
        if not entries:
            print(f"No se encontraron resultados para: '{args.search}'")
            return 0

        print(f"Resultados de búsqueda para '{args.search}' ({len(entries)}):")
        for entry in entries:
            title = entry.source_title or getattr(entry.metadata, "video_title", "") or "Sin título"
            summary_preview = (entry.summary or entry.content or "")[:80]
            eid = entry.id[:8] if entry.id else "unknown"
            print(f"  [{eid}] {entry.content_type} — {title}: {summary_preview}...")
        return 0

    if getattr(args, "clear", False):
        if not getattr(args, "yes", False):
            print("Usa --yes para confirmar la eliminación de toda la memoria.")
            return 1
        entries = provider.list_entries(limit=10000)
        count = 0
        for entry in entries:
            if entry.id and provider.delete_entry(entry.id):
                count += 1
        print(f"Se eliminaron {count} entradas de memoria.")
        return 0

    # Default o --stats: show stats
    stats = provider.get_stats()
    print("=== Estadísticas de Memoria ===")
    print(f"  Total entradas: {stats.total_entries}")
    print(f"  Por tipo: {stats.content_types}")
    print(f"  Base de datos: {stats.db_path}")
    return 0


def memory_command(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser = subparsers.add_parser("memory", help="Manage memory bank")
    parser.add_argument(
        "--db-path",
        default=None,
        help="Database path (default: ~/.video-intake/memory.db)",
    )
    parser.add_argument("--list", action="store_true", help="List all entries")
    parser.add_argument("--search", help="Search entries by text")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--clear", action="store_true", help="Clear all entries")
    parser.add_argument("--limit", type=int, default=20, help="Limit results")
    parser.add_argument("--offset", type=int, default=0, help="Offset for pagination")
    parser.add_argument("--yes", action="store_true", help="Confirm destructive operations")
    parser.set_defaults(func=show_memory)
    return parser
