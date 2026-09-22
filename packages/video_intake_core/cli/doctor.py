"""Doctor command for video-intake-knowledge."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from video_intake_core.cli import _resolve_config


def run_doctor(args: argparse.Namespace) -> int:
    """Comprueba la salud del entorno."""

    results: list[dict[str, Any]] = []

    # Python
    results.append(
        {
            "check": "python",
            "status": "pass",
            "detail": f"{sys.version.split()[0]}",
        }
    )

    # ffmpeg / ffprobe
    import shutil
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    results.append(
        {
            "check": "ffmpeg",
            "status": "pass" if ffmpeg else "fail",
            "detail": ffmpeg or "no encontrado",
        }
    )
    results.append(
        {
            "check": "ffprobe",
            "status": "pass" if ffprobe else "fail",
            "detail": ffprobe or "no encontrado",
        }
    )

    # yt-dlp
    yt_dlp = shutil.which("yt-dlp")
    results.append(
        {
            "check": "yt-dlp",
            "status": "pass" if yt_dlp else "warn",
            "detail": yt_dlp or "no encontrado (solo local)",
        }
    )

    # Tesseract
    tesseract = shutil.which("tesseract")
    results.append(
        {
            "check": "tesseract",
            "status": "pass" if tesseract else "warn",
            "detail": tesseract or "no encontrado (OCR deshabilitado)",
        }
    )

    # Espacio de disco
    try:
        import shutil
        total, used, free = shutil.disk_usage("/")
        free_gb = free / (1024**3)
        results.append(
            {
                "check": "disk_space",
                "status": "pass",
                "detail": f"{free_gb:.1f} GB libres en /",
            }
        )
    except Exception as e:
        results.append(
            {"check": "disk_space", "status": "warn", "detail": str(e)}
        )

    # Escritura
    test_path = Path("./.vitk_test_write")
    try:
        test_path.write_text("test")
        test_path.unlink()
        results.append(
            {"check": "write_permission", "status": "pass", "detail": "OK"}
        )
    except Exception as e:
        results.append(
            {"check": "write_permission", "status": "fail", "detail": str(e)}
        )

    # Config
    config = _resolve_config(args)
    results.append(
        {
            "check": "config",
            "status": "pass",
            "detail": f"Cargado: {getattr(args, 'config', None) or 'config/default.yaml'}",
        }
    )

    # Adaptador detectado
    host_type = config.get("host", {}).get("type", "generic")
    results.append(
        {
            "check": "host_adapter",
            "status": "info",
            "detail": f"tipo={host_type}",
        }
    )

    all_ok = True
    for r in results:
        if r["status"] == "fail":
            all_ok = False

    if args.json:
        print(json.dumps({"checks": results, "healthy": all_ok, "python": sys.version.split()[0]}, ensure_ascii=False))
    else:
        print("=== video-intake doctor ===\n")
        for r in results:
            icon = {"pass": "✓", "fail": "✗", "warn": "⚠", "info": "·"}.get(
                r["status"], "·"
            )
            print(f"  {icon} {r['check']}: {r['detail']}")
        print()
        if all_ok:
            print("Estado: ✓ Saludable")
        else:
            print("Estado: ✗ Con problemas")
    return 0 if all_ok else 1



def doctor_command(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    doctor_p = subparsers.add_parser("doctor", help="Comprueba la salud del entorno.")
    doctor_p.set_defaults(func=run_doctor)
    return doctor_p
