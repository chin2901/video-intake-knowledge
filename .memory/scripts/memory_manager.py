#!/usr/bin/env python3
"""
Memory Bank Initializer for video-intake-knowledge.

This script initializes and manages the dedicated memory bank for the
video-intake-knowledge project, ensuring independence from AibOS/AiboT.
"""

from typing import Any

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone


MEMORY_DIR = Path(__file__).resolve().parent.parent
BANK_DIR = MEMORY_DIR / "bank"
SCRIPTS_DIR = MEMORY_DIR / "scripts"


def initialize_memory_bank() -> dict[str, Any]:
    """Initialize the memory bank with default structure."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    BANK_DIR.mkdir(parents=True, exist_ok=True)
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

    # Create metadata file
    metadata = {
        "project": "video-intake-knowledge",
        "version": "0.1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "independence": {
            "from_aibos": True,
            "from_agy": True,
            "from_opencode": True,
        },
        "memory_type": "dedicated",
        "description": "Independent memory bank for video-intake-knowledge project",
    }

    metadata_path = MEMORY_DIR / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    # Create empty context files
    context_files = [
        "project_context.json",
        "architecture_decisions.json",
        "integration_notes.json",
        "known_issues.json",
    ]

    for filename in context_files:
        filepath = BANK_DIR / filename
        if not filepath.exists():
            with open(filepath, "w") as f:
                json.dump({}, f, indent=2)

    return metadata


def get_memory_status() -> dict[str, Any]:
    """Get current memory bank status."""
    metadata_path = MEMORY_DIR / "metadata.json"

    if not metadata_path.exists():
        return {
            "status": "not_initialized",
            "message": "Memory bank not yet initialized",
        }

    with open(metadata_path) as f:
        metadata = json.load(f)

    bank_files = list(BANK_DIR.glob("*.json")) if BANK_DIR.exists() else []

    return {
        "status": "active",
        "metadata": metadata,
        "bank_files": [f.name for f in bank_files],
        "total_files": len(bank_files),
    }


def main() -> int:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Video Intake Knowledge Memory Bank Manager"
    )
    parser.add_argument(
        "action",
        choices=["init", "status", "update"],
        help="Action to perform",
    )

    args = parser.parse_args()

    if args.action == "init":
        print("Initializing memory bank...")
        metadata = initialize_memory_bank()
        print(f"Memory bank initialized for {metadata['project']}")
        print(f"Location: {MEMORY_DIR}")
        return 0

    elif args.action == "status":
        status = get_memory_status()
        print(json.dumps(status, indent=2))
        return 0

    elif args.action == "update":
        # Update last_updated timestamp
        metadata_path = MEMORY_DIR / "metadata.json"
        if metadata_path.exists():
            with open(metadata_path) as f:
                metadata = json.load(f)
            metadata["last_updated"] = datetime.now(timezone.utc).isoformat()
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
            print("Memory bank updated")
        else:
            print("Memory bank not initialized. Run 'init' first.")
            return 1
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
