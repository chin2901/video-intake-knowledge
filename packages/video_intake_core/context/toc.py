"""
Interactive Table of Contents (TOC) generator with formatted timestamps.

Produces structured chronological chapters and Markdown navigation tables
with formatted timestamps (e.g. 00:01:23) linking sections, summaries,
and visual keyframes.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def format_timestamp(seconds: float, include_hours: bool = True) -> str:
    """Format seconds into HH:MM:SS or MM:SS timestamp string.

    Args:
        seconds: Float seconds (>= 0).
        include_hours: If True, always format as HH:MM:SS (e.g. 00:01:23).

    Returns:
        Formatted timestamp string.
    """
    total_secs = max(0, int(round(seconds)))
    hours = total_secs // 3600
    minutes = (total_secs % 3600) // 60
    secs = total_secs % 60

    if include_hours or hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def parse_seconds(val: Any) -> float:
    """Safely parse seconds from float, int, or string (including HH:MM:SS format)."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return max(0.0, float(val))
    val_str = str(val).strip()
    if not val_str:
        return 0.0
    if ":" in val_str:
        parts = val_str.split(":")
        try:
            if len(parts) == 3:
                return max(0.0, int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2]))
            if len(parts) == 2:
                return max(0.0, int(parts[0]) * 60 + float(parts[1]))
        except ValueError:
            return 0.0
    try:
        return max(0.0, float(val_str))
    except ValueError:
        return 0.0


def _extract_seg_times(seg: dict[str, Any]) -> tuple[float, float]:
    """Extract (start_seconds, end_seconds) from segment dict supporting multiple key formats."""
    raw_start = (
        seg.get("start_seconds") if seg.get("start_seconds") is not None else seg.get("start")
    )
    raw_end = seg.get("end_seconds") if seg.get("end_seconds") is not None else seg.get("end")
    start = parse_seconds(raw_start)
    end = parse_seconds(raw_end)
    if end < start:
        end = start
    return start, end


def _clean_text_snippet(text: str, max_chars: int = 250) -> str:
    """Clean and truncate text for chapter summaries."""
    cleaned = " ".join(text.split()).strip()
    if len(cleaned) > max_chars:
        return cleaned[: max_chars - 3].rstrip() + "..."
    return cleaned


def _derive_chapter_title(text: str, fallback_idx: int) -> str:
    """Derive a concise, meaningful title from segment text."""
    lines = [s.strip() for s in re.split(r"[.?!¡¿\n]", text) if s.strip()]
    candidate = lines[0] if lines else ""

    # Remove conversational filler words
    candidate = re.sub(
        r"^(bueno|hola|bienvenidos|vamos a ver|en este video|hoy vamos a|entonces|ahora bien)\s*,?\s*",
        "",
        candidate,
        flags=re.IGNORECASE,
    ).strip()

    if candidate and len(candidate) >= 8:
        # Capitalize and cap length
        title = candidate[0].upper() + candidate[1:]
        if len(title) > 65:
            title = title[:62].rstrip() + "..."
        return title

    return f"Capítulo {fallback_idx}"


def generate_table_of_contents(
    segments: list[dict[str, Any]] | None = None,
    video_duration: float | None = None,
    full_text: str = "",
    keyframes: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Generate structured Table of Contents chapters from transcript and keyframes.

    Args:
        segments: List of transcript segment dicts with 'start'/'start_seconds', 'end'/'end_seconds', and 'text'.
        video_duration: Total video length in seconds (optional).
        full_text: Complete text when segments are unavailable.
        keyframes: List of extracted keyframe dicts with 'timestamp' and 'frame_path'.

    Returns:
        List of chapter dicts with chapter_number, start_time (00:01:23), end_time,
        title, summary, key_points, and matched_keyframe.
    """
    valid_segments = [s for s in (segments or []) if s.get("text")]

    # Calculate actual duration
    duration = video_duration or 0.0
    if valid_segments:
        max_seg_end = max(_extract_seg_times(s)[1] for s in valid_segments)
        duration = max(duration, max_seg_end)
    if duration <= 0.0:
        duration = 60.0

    chapters: list[dict[str, Any]] = []

    # If we have structured segments, group them into coherent chapters
    if valid_segments:
        # Target 4 to 10 chapters depending on length
        num_target = min(max(3, int(duration // 90) + 1), 10)
        chunk_len = duration / num_target

        for i in range(num_target):
            c_start = i * chunk_len
            c_end = min((i + 1) * chunk_len, duration)

            # Gather segments falling into this time range
            c_segs = [
                s
                for s in valid_segments
                if _extract_seg_times(s)[0] < c_end and _extract_seg_times(s)[1] >= c_start
            ]
            c_text = " ".join(s.get("text", "") for s in c_segs).strip()

            if not c_text and valid_segments:
                continue

            title = _derive_chapter_title(c_text, i + 1)
            summary = _clean_text_snippet(c_text, 220)

            # Extract 2-3 key takeaway bullet points
            sentences = [s.strip() for s in re.split(r"[.?!¡¿\n]", c_text) if len(s.strip()) > 15]
            key_points = sentences[:3] if sentences else ([summary] if summary else [])

            # Match closest keyframe if available
            matched_frame = None
            if keyframes:
                for kf in keyframes:
                    kf_time = float(kf.get("timestamp", 0.0) or 0.0)
                    if c_start <= kf_time <= c_end:
                        matched_frame = kf.get("frame_path")
                        break

            chapters.append(
                {
                    "chapter_number": i + 1,
                    "start_seconds": round(c_start, 2),
                    "end_seconds": round(c_end, 2),
                    "start_time": format_timestamp(c_start),
                    "end_time": format_timestamp(c_end),
                    "duration_seconds": round(c_end - c_start, 2),
                    "title": title,
                    "summary": summary,
                    "key_points": key_points,
                    "matched_keyframe": matched_frame,
                }
            )

    # Fallback when no segments exist but text or duration is provided
    if not chapters:
        text_clean = _clean_text_snippet(full_text or "Contenido procesado", 300)
        chapters.append(
            {
                "chapter_number": 1,
                "start_seconds": 0.0,
                "end_seconds": round(duration, 2),
                "start_time": format_timestamp(0.0),
                "end_time": format_timestamp(duration),
                "duration_seconds": round(duration, 2),
                "title": "Visión General y Contenido Principal",
                "summary": text_clean,
                "key_points": [text_clean],
                "matched_keyframe": keyframes[0].get("frame_path") if keyframes else None,
            }
        )

    return chapters


def format_toc_markdown(
    chapters: list[dict[str, Any]],
    title: str = "Tabla de Contenidos",
) -> str:
    """Format TOC chapters into an interactive, beautifully structured Markdown document.

    Args:
        chapters: List of chapter dicts from generate_table_of_contents().
        title: Document header title.

    Returns:
        Interactive Markdown string.
    """
    lines: list[str] = [
        f"# {title}",
        "",
        "> Navegación cronológica interactiva con marcas temporales y puntos clave.",
        "",
        "| Timestamp | Capítulo | Duración | Resumen / Puntos Clave |",
        "| :--- | :--- | :--- | :--- |",
    ]

    for ch in chapters:
        num = ch.get("chapter_number", 1)
        st = ch.get("start_time", "00:00:00")
        dur = format_timestamp(ch.get("duration_seconds", 0.0), include_hours=False)
        ch_title = ch.get("title", f"Capítulo {num}")
        short_summary = ch.get("summary", "")[:90].replace("|", "\\|")
        if len(ch.get("summary", "")) > 90:
            short_summary += "..."

        lines.append(f"| **`{st}`** | [{ch_title}](#capitulo-{num}) | {dur} | {short_summary} |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Detalle de Capítulos y Secciones")
    lines.append("")

    for ch in chapters:
        num = ch.get("chapter_number", 1)
        st = ch.get("start_time", "00:00:00")
        et = ch.get("end_time", "00:00:00")
        ch_title = ch.get("title", f"Capítulo {num}")
        lines.append(f'### <a id="capitulo-{num}"></a>[{st} → {et}] {num}. {ch_title}')
        lines.append("")
        if ch.get("summary"):
            lines.append(f"**Resumen:** {ch['summary']}")
            lines.append("")

        points = ch.get("key_points", [])
        if points:
            lines.append("**Puntos clave:**")
            for pt in points:
                lines.append(f"- {pt}")
            lines.append("")

        frame = ch.get("matched_keyframe")
        if frame:
            lines.append(f"*Fotograma clave de referencia:* `{frame}`")
            lines.append("")

    return "\n".join(lines).strip() + "\n"
