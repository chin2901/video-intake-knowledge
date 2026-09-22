"""Inspect command for video-intake-knowledge."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass

from video_intake_core.inspection import inspect_video as _inspect_video


def run_inspect(args: argparse.Namespace) -> int:
    """Muestra metadatos de una fuente de vídeo."""
    source = args.source
    try:
        raw_info = _inspect_video(source)
    except Exception as e:
        print(f"Error inspeccionando {source}: {e}", file=sys.stderr)
        return 1

    info = (
        asdict(raw_info)
        if is_dataclass(raw_info)
        else (raw_info.to_dict() if hasattr(raw_info, "to_dict") else raw_info if isinstance(raw_info, dict) else vars(raw_info))
    )

    if getattr(args, "json", False):
        print(json.dumps(info, indent=2, ensure_ascii=False))
    else:
        print(f"Título: {info.get('title') or 'N/A'}")
        print(f"Plataforma: {info.get('extractor') or info.get('platform') or 'local'}")
        dur = info.get("duration") or info.get("duration_secs")
        if dur is not None:
            print(f"Duración: {float(dur):.1f}s ({info.get('duration_string') or 'N/A'})")
        if info.get("width") and info.get("height"):
            print(f"Resolución: {info['width']}x{info['height']}")
        if info.get("fps"):
            print(f"FPS: {info['fps']}")
        if info.get("video_codec"):
            print(f"Codec video: {info['video_codec']}")
        if info.get("audio_codec"):
            print(f"Codec audio: {info['audio_codec']}")
        if info.get("audio_channels"):
            print(f"Canales audio: {info['audio_channels']}")
        streams = info.get("streams") or info.get("formats") or []
        print(f"Streams: {len(streams)}")
        print(f"URL: {info.get('url') or source}")
        captions = info.get("captions") or info.get("subtitles") or []
        if captions:
            if isinstance(captions, dict):
                print(f"Subtítulos: {len(captions)} idioma(s): {', '.join(captions.keys())}")
            elif isinstance(captions, list):
                print(f"Subtítulos: {len(captions)}")
                for c in captions:
                    print(f"  - {c.get('lang', '?')} ({c.get('name', '?')})")
    return 0

def inspect_command(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser = subparsers.add_parser("inspect", help="Muestra metadatos de una fuente.")
    parser.add_argument("source", help="URL o ruta del vídeo.")
    parser.set_defaults(func=run_inspect)
    return parser
