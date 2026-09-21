"""Entry point for running the CLI via python -m video_intake_core.cli."""

from __future__ import annotations

import sys

from video_intake_core.cli import main

if __name__ == "__main__":
    sys.exit(main())
