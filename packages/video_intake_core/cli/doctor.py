"""
Doctor command for video-intake-knowledge.

Performs system health checks and diagnostics.
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Any

logger = logging.getLogger(__name__)


def doctor_checks() -> dict[str, Any]:
    """Run all doctor checks and return results."""
    results = {
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "platform": sys.platform,
        "checks": {},
    }

    # Check Python version
    results["checks"]["python_version"] = {
        "status": "ok" if sys.version_info >= (3, 10) else "warning",
        "message": f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }

    # Check for optional dependencies
    optional_deps = [
        ("yaml", "PyYAML"),
        ("sqlite3", "sqlite3 (stdlib)"),
        ("json", "json (stdlib)"),
        ("pathlib", "pathlib (stdlib)"),
        ("dataclasses", "dataclasses (stdlib)"),
    ]

    for module, name in optional_deps:
        try:
            __import__(module)
            results["checks"][f"dep_{module}"] = {"status": "ok", "message": f"{name} available"}
        except ImportError:
            results["checks"][f"dep_{module}"] = {"status": "error", "message": f"{name} NOT available"}

    # Check video_intake_core package
    try:
        import video_intake_core
        results["checks"]["package"] = {
            "status": "ok",
            "message": f"video-intake-knowledge v{getattr(video_intake_core, '__version__', 'unknown')}",
        }
    except ImportError as e:
        results["checks"]["package"] = {"status": "error", "message": str(e)}

    return results


def run_doctor(args: argparse.Namespace) -> int:
    """Execute the doctor command."""
    results = doctor_checks()

    print("=== video-intake-knowledge Doctor ===")
    print(f"Python: {results['python_version']}")
    print(f"Platform: {results['platform']}")
    print()

    all_ok = True
    for check_name, check_result in results["checks"].items():
        status = check_result["status"]
        message = check_result["message"]
        icon = "✓" if status == "ok" else "✗" if status == "error" else "⚠"
        print(f"  {icon} {check_name}: {message}")
        if status == "error":
            all_ok = False

    print()
    if all_ok:
        print("All checks passed!")
        return 0
    else:
        print("Some checks failed.")
        return 1


def detect_vulnerable_ffmpeg_or_tesseract() -> dict[str, Any]:
    """Detect vulnerable versions of ffmpeg or tesseract (contract API)."""
    import re
    import subprocess

    result = {
        "ffmpeg_version": None,
        "tesseract_version": None,
        "vulnerable_ffmpeg": False,
        "vulnerable_tesseract": False,
    }

    # Check ffmpeg
    try:
        out = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out.returncode == 0:
            match = re.search(r"ffmpeg version\s+(\S+)", out.stdout)
            if match:
                result["ffmpeg_version"] = match.group(1)
                # Check for known vulnerable versions (before 6.0)
                version_str = match.group(1)
                major = int(version_str.split(".")[0]) if version_str.split(".")[0].isdigit() else 0
                result["vulnerable_ffmpeg"] = major < 6
    except Exception:
        pass

    # Check tesseract
    try:
        out = subprocess.run(
            ["tesseract", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out.returncode == 0:
            match = re.search(r"tesseract\s+(\S+)", out.stdout)
            if match:
                result["tesseract_version"] = match.group(1)
                version_str = match.group(1)
                major = int(version_str.split(".")[0]) if version_str.split(".")[0].isdigit() else 0
                result["vulnerable_tesseract"] = major < 5
    except Exception:
        pass

    return result


def create_sample_video_ffmpeg(output_path: str, duration: int = 5) -> bool:
    """Create a sample video using ffmpeg for testing (contract API)."""
    import subprocess

    try:
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"testsrc=duration={duration}:size=640x480:rate=30",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        return result.returncode == 0
    except Exception:
        return False


def doctor_command(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """Add the doctor subcommand to the parser."""
    parser = subparsers.add_parser("doctor", help="Run system health checks")
    parser.set_defaults(func=run_doctor)
    return parser
