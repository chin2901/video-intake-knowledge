#!/usr/bin/env python3
"""
create_memory_db.py — Script para inicializar el banco de memoria independiente.

Este script crea la base de datos SQLite del banco de memoria en la ubicación
configurada (por defecto: /srv/video-intake-knowledge/memory/memory.db).

Se puede ejecutar de forma independiente para inicializar o reinicializar
el banco de memoria del proyecto.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path


DEFAULT_MEMORY_DIR = Path("/srv/video-intake-knowledge/memory")
DEFAULT_DB_PATH = DEFAULT_MEMORY_DIR / "memory.db"


def create_memory_db(db_path: Path, reset: bool = False) -> int:
    """
    Crear o reinicializar la base de datos del banco de memoria.

    Args:
        db_path: Ruta a la base de datos SQLite.
        reset: Si True, elimina la DB existente antes de crear.

    Returns:
        Número de entradas creadas (0 si es una DB nueva).
    """
    # Asegurar que el directorio existe
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Eliminar DB existente si se solicita reset
    if reset and db_path.exists():
        db_path.unlink()
        print(f"✓ DB existente eliminada: {db_path}")

    # Crear conexión
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    try:
        cursor = conn.cursor()

        # Tabla de entradas de memoria
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_entries (
                id TEXT PRIMARY KEY,
                source_url TEXT NOT NULL,
                source_title TEXT DEFAULT '',
                extracted_at TEXT NOT NULL,
                content_type TEXT NOT NULL,
                content TEXT NOT NULL,
                summary TEXT DEFAULT '',
                metadata TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabla de tags
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                FOREIGN KEY (entry_id) REFERENCES memory_entries(id) ON DELETE CASCADE,
                UNIQUE(entry_id, tag)
            )
        """)

        # Tabla de relaciones entre entradas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                FOREIGN KEY (source_id) REFERENCES memory_entries(id) ON DELETE CASCADE,
                FOREIGN KEY (target_id) REFERENCES memory_entries(id) ON DELETE CASCADE,
                UNIQUE(source_id, target_id, relation_type)
            )
        """)

        # Tabla de metadatos extendidos (JSON flexible)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_metadata (
                entry_id TEXT PRIMARY KEY,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                FOREIGN KEY (entry_id) REFERENCES memory_entries(id) ON DELETE CASCADE
            )
        """)

        # Índices para búsqueda eficiente
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_entries_source_url ON memory_entries(source_url)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_entries_content_type ON memory_entries(content_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_entries_extracted_at ON memory_entries(extracted_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_tags_tag ON memory_tags(tag)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_relations_source ON memory_relations(source_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_relations_target ON memory_relations(target_id)")

        # Vista para búsqueda de texto completo simple
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS memory_search_view AS
            SELECT
                m.id,
                m.source_url,
                m.source_title,
                m.extracted_at,
                m.content_type,
                m.content,
                m.summary,
                m.metadata,
                m.created_at,
                m.updated_at,
                GROUP_CONCAT(t.tag, ', ') as tags
            FROM memory_entries m
            LEFT JOIN memory_tags t ON m.id = t.entry_id
            GROUP BY m.id
        """)

        conn.commit()

        # Contar entradas existentes
        cursor.execute("SELECT COUNT(*) as count FROM memory_entries")
        count = cursor.fetchone()["count"]

        print(f"✓ Banco de memoria inicializado en: {db_path}")
        print(f"  Entradas existentes: {count}")
        print(f"  Esquema: memory_entries, memory_tags, memory_relations, memory_metadata")
        print(f"  Vista: memory_search_view")

        return count

    except Exception as e:
        print(f"✗ Error al crear la DB: {e}", file=sys.stderr)
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Inicializar el banco de memoria de video-intake-knowledge"
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Ruta a la base de datos (por defecto: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Eliminar la DB existente antes de crear",
    )
    parser.add_argument(
        "--memory-dir",
        type=Path,
        help="Directorio del banco de memoria (por defecto: /srv/video-intake-knowledge/memory)",
    )

    args = parser.parse_args()

    # Resolver paths
    if args.memory_dir:
        memory_dir = args.memory_dir
    else:
        memory_dir = Path(os.environ.get("VITK_MEMORY_DIR", str(DEFAULT_MEMORY_DIR)))

    if args.db_path:
        db_path = args.db_path
    else:
        db_path = memory_dir / "memory.db"

    print(f"Memory dir: {memory_dir}")
    print(f"DB path: {db_path}")

    create_memory_db(db_path, reset=args.reset)

    print("\n✓ Banco de memoria listo para usar.")
    print("  Para usar desde el sistema, configurar memory.db_path en el YAML:")
    print(f"    memory:\n      db_path: {db_path}")


if __name__ == "__main__":
    main()
