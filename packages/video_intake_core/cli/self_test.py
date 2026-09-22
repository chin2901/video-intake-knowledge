
"""Self-test command for video-intake-knowledge."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any


def run_self_test(args: argparse.Namespace) -> int:

    """Ejecuta pruebas de auto-diagnóstico."""
    import shutil

    from video_intake_core.acquisition import detect_video_sources

    print("=== video-intake self-test ===\n")
    tests: list[dict[str, Any]] = []

    # Test 1: detección de URL de YouTube
    try:
        sources = detect_video_sources(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        tests.append(
            {
                "name": "detect_youtube_url",
                "status": "pass",
                "detail": f"{len(sources)} fuente(s) detectada(s)",
            }
        )
    except Exception as e:
        tests.append(
            {
                "name": "detect_youtube_url",
                "status": "fail",
                "detail": str(e),
            }
        )

    # Test 2: detección de archivo local
    repo_root = Path(__file__).resolve().parent.parent.parent
    candidate_fixtures = [
        repo_root / "tests" / "fixtures" / "video" / "sample.mp4",
        repo_root / "tests" / "fixtures" / "sample.mp4",
        Path("tests/fixtures/video/sample.mp4").resolve(),
    ]
    test_file = next((f for f in candidate_fixtures if f.exists()), None)
    if test_file:
        try:
            sources = detect_video_sources(str(test_file))
            stype = (
                getattr(sources[0], "source_type", None)
                or (sources[0].get("type") if isinstance(sources[0], dict) else "local")
                if sources
                else "N/A"
            )
            tests.append(
                {
                    "name": "detect_local_file",
                    "status": "pass",
                    "detail": f"detectado: {stype}",
                }
            )
        except Exception as e:
            tests.append(
                {
                    "name": "detect_local_file",
                    "status": "fail",
                    "detail": str(e),
                }
            )
    else:
        tests.append(
            {
                "name": "detect_local_file",
                "status": "skip",
                "detail": "no hay fixture sample.mp4",
            }
        )

    # Test 3: herramientas del sistema
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    tesseract = shutil.which("tesseract")
    yt_dlp = shutil.which("yt-dlp")

    tests.append(
        {
            "name": "ffmpeg_available",
            "status": "pass" if ffmpeg else "fail",
            "detail": ffmpeg or "no encontrado",
        }
    )
    tests.append(
        {
            "name": "ffprobe_available",
            "status": "pass" if ffprobe else "fail",
            "detail": ffprobe or "no encontrado",
        }
    )
    tests.append(
        {
            "name": "tesseract_available",
            "status": "pass" if tesseract else "warn",
            "detail": tesseract or "no encontrado (OCR limitado)",
        }
    )
    tests.append(
        {
            "name": "yt_dlp_available",
            "status": "pass" if yt_dlp else "warn",
            "detail": yt_dlp or "no encontrado (solo local)",
        }
    )

    for t in tests:
        icon = {"pass": "✓", "fail": "✗", "warn": "⚠", "skip": "⊘"}.get(
            t["status"], "·"
        )
        print(f"  {icon} {t['name']}: {t['detail']}")

    fails = sum(1 for t in tests if t["status"] == "fail")
    print()
    if fails == 0:
        print("Self-test completado: ✓")
    else:
        print(f"Self-test completado: ✗ ({fails} fallo(s))")
    return 0 if fails == 0 else 1



def self_test_command(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser = subparsers.add_parser("self-test", help="Ejecuta pruebas de auto-diagnóstico.")
    parser.set_defaults(func=run_self_test)
    return parser
