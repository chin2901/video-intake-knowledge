"""
Comprehensive Knowledge Report generator.

Generates complete, cohesive Markdown reports integrating structured executive summaries,
interactive TOCs with timestamps, selected visual keyframes, extracted code blocks,
and the full transcript.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .executive_summary import (
    format_executive_summary_markdown,
    generate_structured_executive_summary,
)
from .toc import (
    format_toc_markdown,
    generate_table_of_contents,
)

logger = logging.getLogger(__name__)


def generate_comprehensive_markdown_report(
    title: str,
    source_info: dict[str, Any] | None = None,
    toc_data: list[dict[str, Any]] | str | None = None,
    executive_summary_data: dict[str, Any] | str | None = None,
    transcript_text: str = "",
    keyframes: list[dict[str, Any]] | None = None,
    ocr_results: list[dict[str, Any]] | None = None,
    audio_context: dict[str, Any] | None = None,
    visual_context: dict[str, Any] | None = None,
) -> str:
    """Generate a comprehensive Markdown report combining all knowledge assets.

    Args:
        title: Title of the video or intake artifact.
        source_info: Source metadata (url, duration, platform, etc.).
        toc_data: Structured TOC list or formatted markdown string.
        executive_summary_data: Structured summary dict or formatted markdown string.
        transcript_text: Full clean transcript string.
        keyframes: List of extracted keyframes metadata.
        ocr_results: OCR results from frames (including code detections).
        audio_context: Audio context dict (if already computed).
        visual_context: Visual context dict (if already computed).

    Returns:
        Complete Markdown document content string.
    """
    source_info = source_info or {}
    url = source_info.get("resolved_url") or source_info.get("url", "N/A")
    duration = source_info.get("duration") or source_info.get("duration_seconds")
    now_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines: list[str] = [
        f"# Reporte Integral de Conocimiento: {title}",
        "",
        "> Documento consolidado generado automáticamente por video-intake-knowledge.",
        f"> **Fecha:** {now_str} | **Fuente:** {url}",
        "",
        "---",
        "",
    ]

    # 1. Metadatos Generales
    lines.append("## Metadatos del Contenido Audiovisual")
    lines.append("")
    lines.append(f"- **Título:** {title}")
    lines.append(f"- **URL / Origen:** `{url}`")
    if duration:
        lines.append(f"- **Duración estimada:** {duration}s")
    if source_info.get("platform"):
        lines.append(f"- **Plataforma:** {source_info['platform']}")
    if keyframes:
        lines.append(f"- **Fotogramas clave retenidos:** {len(keyframes)}")
    if transcript_text:
        lines.append(f"- **Longitud de transcripción:** {len(transcript_text)} caracteres")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 2. Resumen Ejecutivo Estructurado
    lines.append("## Resumen Ejecutivo y Síntesis de Alto Nivel")
    lines.append("")
    if isinstance(executive_summary_data, str) and executive_summary_data.strip():
        lines.append(executive_summary_data.strip())
    elif isinstance(executive_summary_data, dict):
        lines.append(format_executive_summary_markdown(executive_summary_data, title=title).strip())
    elif transcript_text:
        summary_dict = generate_structured_executive_summary(
            transcript_text, source_info=source_info
        )
        lines.append(format_executive_summary_markdown(summary_dict, title=title).strip())
    else:
        lines.append("Resumen no disponible: contenido textual ausente.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 3. Tabla de Contenidos Interactiva (TOC)
    lines.append("## Tabla de Contenidos y Navegación Cronológica")
    lines.append("")
    if isinstance(toc_data, str) and toc_data.strip():
        lines.append(toc_data.strip())
    elif isinstance(toc_data, list) and toc_data:
        lines.append(format_toc_markdown(toc_data, title="Índice de Capítulos").strip())
    else:
        toc_gen = generate_table_of_contents(
            video_duration=float(duration) if duration else None,
            full_text=transcript_text,
            keyframes=keyframes,
        )
        lines.append(format_toc_markdown(toc_gen, title="Índice de Capítulos").strip())
    lines.append("")
    lines.append("---")
    lines.append("")

    # 4. Inteligencia Visual y Fotogramas Clave
    lines.append("## Inteligencia Visual y Momentos Clave")
    lines.append("")
    if keyframes or ocr_results:
        lines.append(
            "Selección de fotogramas analizados tras aplicar filtros de nitidez "
            "(Laplacian Variance) y deduplicación de diapositivas (SSIM/MSE):"
        )
        lines.append("")

        # Create quick map of ocr results by frame path stem
        ocr_by_frame: dict[str, dict[str, Any]] = {}
        if ocr_results:
            for item in ocr_results:
                f_path = str(item.get("frame_path", ""))
                stem = Path(f_path).stem
                ocr_by_frame[stem] = item

        for idx, kf in enumerate((keyframes or [])[:12], 1):
            f_path_str = str(kf.get("frame_path", ""))
            f_name = Path(f_path_str).name
            ts_str = kf.get("timestamp_str") or "00:00:00"
            rel_path = f"frames/{f_name}" if "frames" not in f_path_str else f_path_str

            lines.append(f"### Fotograma #{idx} [{ts_str}] — `{f_name}`")
            lines.append("")
            lines.append(f"![Fotograma {ts_str}]({rel_path})")
            lines.append("")

            # Match OCR or code content
            stem = Path(f_path_str).stem
            matched_ocr = ocr_by_frame.get(stem)
            if matched_ocr:
                if matched_ocr.get("is_code") and matched_ocr.get("formatted_markdown"):
                    lang = matched_ocr.get("code_language", "text")
                    lines.append(f"**Código fuente detectado ({lang}):**")
                    lines.append(matched_ocr["formatted_markdown"])
                elif matched_ocr.get("text"):
                    lines.append(f"**Texto detectado en pantalla:**\n> {matched_ocr['text']}")
                lines.append("")
    else:
        lines.append("No se procesaron fotogramas visuales para este registro.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 5. Transcripción Completa
    lines.append("## Transcripción Completa del Contenido")
    lines.append("")
    if transcript_text:
        lines.append(transcript_text.strip())
    else:
        lines.append("Transcripción no disponible.")
    lines.append("")

    return "\n".join(lines).strip() + "\n"


def export_knowledge_report(
    job_dir: Path | str,
    report_content: str,
    filename: str = "knowledge_report.md",
) -> Path:
    """Save knowledge report Markdown content into job artifacts directory.

    Args:
        job_dir: Job artifacts directory path.
        report_content: Complete report markdown content string.
        filename: Target filename (default: 'knowledge_report.md').

    Returns:
        Path to the saved report file.
    """
    target_dir = Path(job_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    report_path = target_dir / filename
    report_path.write_text(report_content, encoding="utf-8")
    logger.info("Knowledge report exported to %s", report_path)
    return report_path
