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
        results.append({"check": "disk_space", "status": "warn", "detail": str(e)})

    # Escritura
    test_path = Path("./.vitk_test_write")
    try:
        test_path.write_text("test")
        test_path.unlink()
        results.append({"check": "write_permission", "status": "pass", "detail": "OK"})
    except Exception as e:
        results.append({"check": "write_permission", "status": "fail", "detail": str(e)})

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

    # Motor de Transcripción (faster-whisper / openai-whisper)
    has_faster = False
    try:
        import faster_whisper

        has_faster = True
        fw_ver = getattr(faster_whisper, "__version__", "instalado")
        results.append(
            {
                "check": "faster-whisper",
                "status": "pass",
                "detail": f"v{fw_ver} (CTranslate2 acelerado)",
            }
        )
    except ImportError:
        results.append(
            {
                "check": "faster-whisper",
                "status": "warn",
                "detail": "no instalado (usando openai-whisper como fallback)",
            }
        )

    try:
        import whisper

        whisper_ver = getattr(whisper, "__version__", "instalado")
        results.append(
            {
                "check": "openai-whisper",
                "status": "pass",
                "detail": f"v{whisper_ver}",
            }
        )
    except ImportError:
        results.append(
            {
                "check": "openai-whisper",
                "status": "pass" if has_faster else "warn",
                "detail": "no instalado"
                if not has_faster
                else "no instalado (cubierto por faster-whisper)",
            }
        )

    # Aceleración de Hardware (GPU / CUDA / MPS / CPU int8)
    hw_status = "info"
    hw_detail = "CPU (cuantización int8 habilitada)"
    try:
        import torch

        if torch.cuda.is_available():
            hw_status = "pass"
            hw_detail = f"NVIDIA CUDA ({torch.cuda.get_device_name(0)})"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            hw_status = "pass"
            hw_detail = "Apple Silicon Metal (MPS)"
    except Exception:
        pass
    results.append({"check": "hardware_acceleration", "status": hw_status, "detail": hw_detail})

    # Librerías de Visión Computacional (OpenCV / Pillow)
    vision_libs: list[str] = []
    try:
        import cv2

        vision_libs.append(f"OpenCV v{cv2.__version__}")
    except ImportError:
        pass
    try:
        import PIL

        vision_libs.append(f"Pillow v{getattr(PIL, '__version__', 'OK')}")
    except ImportError:
        pass
    if vision_libs:
        results.append(
            {
                "check": "vision_engine",
                "status": "pass",
                "detail": ", ".join(vision_libs),
            }
        )
    else:
        results.append(
            {
                "check": "vision_engine",
                "status": "warn",
                "detail": "OpenCV / Pillow no disponibles para análisis de fotogramas",
            }
        )

    # Estado de Autenticación y Cookies
    cookie_path = Path.home() / ".video-intake" / "cookies.txt"
    if cookie_path.exists() and cookie_path.stat().st_size > 0:
        results.append(
            {
                "check": "auth_cookies",
                "status": "pass",
                "detail": f"Activo ({cookie_path.stat().st_size} bytes en {cookie_path})",
            }
        )
    else:
        results.append(
            {
                "check": "auth_cookies",
                "status": "info",
                "detail": "No configuradas (usa 'video-intake auth detect')",
            }
        )

    all_ok = True
    for r in results:
        if r["status"] == "fail":
            all_ok = False

    if args.json:
        print(
            json.dumps(
                {"checks": results, "healthy": all_ok, "python": sys.version.split()[0]},
                ensure_ascii=False,
            )
        )
    else:
        print("=== video-intake doctor ===\n")
        for r in results:
            icon = {"pass": "✓", "fail": "✗", "warn": "⚠", "info": "·"}.get(r["status"], "·")
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
