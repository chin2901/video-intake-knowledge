"""Export command for video-intake-knowledge."""

from __future__ import annotations

import argparse
import html as html_lib
import json
import logging
import sys
from pathlib import Path
from typing import Any

from video_intake_core.jobs import get_job

logger = logging.getLogger("video_intake.export")


def _find_job_directory(job_id: str) -> Path | None:
    """Busca el directorio en disco de un job en ubicaciones estándar."""
    candidates = [
        Path("artifacts") / job_id,
        Path.cwd() / "artifacts" / job_id,
        Path.home() / ".video-intake" / "artifacts" / job_id,
    ]
    for p in candidates:
        if p.exists() and p.is_dir():
            return p
    return None


def _load_job_artifacts(job_dir: Path | None) -> dict[str, str]:
    """Carga los contenidos de los artefactos de texto del job si existen."""
    artifacts: dict[str, str] = {}
    if not job_dir or not job_dir.exists():
        return artifacts

    text_files = {
        "knowledge_report": "knowledge_report.md",
        "executive_summary": "executive_summary.md",
        "toc": "toc.md",
        "transcript": "transcript.md",
        "audio_context": "audio_context.md",
        "visual_context": "visual_context.md",
    }
    for key, filename in text_files.items():
        file_path = job_dir / filename
        if file_path.exists():
            try:
                artifacts[key] = file_path.read_text(encoding="utf-8")
            except Exception as e:
                logger.debug("No se pudo leer %s: %s", file_path, e)
    return artifacts


def _generate_obsidian_markdown(
    job_id: str,
    title: str,
    status_val: str,
    source_url: str,
    artifacts: dict[str, str],
    manifest: dict[str, Any] | None,
) -> str:
    """Genera una nota compatible con Obsidian con Frontmatter YAML y callouts."""
    safe_title = title.replace('"', '\\"')
    frontmatter = [
        "---",
        f'title: "{safe_title}"',
        f'job_id: "{job_id}"',
        f'status: "{status_val}"',
        f'source: "{source_url}"',
        "tags:",
        "  - video",
        "  - knowledge",
        "  - intake",
        "---",
        "",
    ]

    parts = ["\n".join(frontmatter)]

    if "knowledge_report" in artifacts:
        parts.append(artifacts["knowledge_report"])
    else:
        parts.append(f"# {title}\n")
        parts.append(
            f"> [!INFO] Metadatos del Vídeo\n> **Job ID**: `{job_id}`  \n> **Fuente**: {source_url}  \n> **Estado**: {status_val}\n"
        )

        if "executive_summary" in artifacts:
            parts.append(
                "> [!SUMMARY] Dossier Ejecutivo\n>\n"
                + "\n".join(f"> {line}" for line in artifacts["executive_summary"].splitlines())
                + "\n"
            )

        if "toc" in artifacts:
            parts.append(f"## 📑 Tabla de Contenidos\n\n{artifacts['toc']}\n")

        if "transcript" in artifacts:
            parts.append(f"## 📝 Transcripción Completa\n\n{artifacts['transcript']}\n")

        if "visual_context" in artifacts:
            parts.append(f"## 👁️ Contexto Visual y OCR\n\n{artifacts['visual_context']}\n")

    return "\n\n".join(parts).strip() + "\n"


def _generate_standalone_html(
    job_id: str,
    title: str,
    status_val: str,
    source_url: str,
    artifacts: dict[str, str],
) -> str:
    """Genera un reporte HTML autocontenido elegante y responsive con modo oscuro."""
    escaped_title = html_lib.escape(title)
    escaped_job_id = html_lib.escape(job_id)
    escaped_source = html_lib.escape(source_url)
    escaped_status = html_lib.escape(status_val)

    sections_html = []
    if "knowledge_report" in artifacts:
        content = html_lib.escape(artifacts["knowledge_report"])
        sections_html.append(
            f'<div class="card"><h2>Reporte Integral</h2><pre><code>{content}</code></pre></div>'
        )
    else:
        if "executive_summary" in artifacts:
            content = html_lib.escape(artifacts["executive_summary"])
            sections_html.append(
                f'<div class="card"><h2>Dossier Ejecutivo</h2><pre><code>{content}</code></pre></div>'
            )
        if "toc" in artifacts:
            content = html_lib.escape(artifacts["toc"])
            sections_html.append(
                f'<div class="card"><h2>Tabla de Contenidos</h2><pre><code>{content}</code></pre></div>'
            )
        if "transcript" in artifacts:
            content = html_lib.escape(artifacts["transcript"])
            sections_html.append(
                f'<div class="card"><h2>Transcripción</h2><pre><code>{content}</code></pre></div>'
            )
        if "visual_context" in artifacts:
            content = html_lib.escape(artifacts["visual_context"])
            sections_html.append(
                f'<div class="card"><h2>Visión y OCR</h2><pre><code>{content}</code></pre></div>'
            )

    body_content = "\n".join(sections_html)

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escaped_title} — AibOS Video Knowledge</title>
  <style>
    :root {{
      --bg: #0d1117;
      --card-bg: #161b22;
      --text: #c9d1d9;
      --heading: #58a6ff;
      --border: #30363d;
      --accent: #238636;
      --muted: #8b949e;
    }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.6;
      margin: 0;
      padding: 2rem 1rem;
    }}
    .container {{
      max-width: 900px;
      margin: 0 auto;
    }}
    header {{
      border-bottom: 1px solid var(--border);
      padding-bottom: 1.5rem;
      margin-bottom: 2rem;
    }}
    h1 {{
      color: #f0f6fc;
      margin-top: 0;
    }}
    .badge {{
      display: inline-block;
      padding: 0.25rem 0.6rem;
      font-size: 0.85rem;
      font-weight: 600;
      border-radius: 20px;
      background-color: var(--accent);
      color: #ffffff;
      margin-right: 0.5rem;
    }}
    .meta {{
      color: var(--muted);
      font-size: 0.9rem;
      margin-top: 0.5rem;
    }}
    .card {{
      background-color: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1.5rem;
      margin-bottom: 1.5rem;
    }}
    h2 {{
      color: var(--heading);
      margin-top: 0;
      border-bottom: 1px solid var(--border);
      padding-bottom: 0.5rem;
    }}
    pre {{
      white-space: pre-wrap;
      word-break: break-word;
      font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
      font-size: 0.9rem;
      background: #090d13;
      padding: 1rem;
      border-radius: 6px;
      border: 1px solid var(--border);
      overflow-x: auto;
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <span class="badge">{escaped_status.upper()}</span>
      <h1>{escaped_title}</h1>
      <div class="meta">
        <strong>Job ID:</strong> {escaped_job_id} &bull;
        <strong>Fuente:</strong> <a href="{escaped_source}" style="color: var(--heading);">{escaped_source}</a>
      </div>
    </header>
    <main>
      {body_content}
    </main>
  </div>
</body>
</html>"""


def run_export(args: argparse.Namespace) -> int:
    """Exporta los resultados de un job a Markdown, Obsidian, JSON o HTML."""
    job = get_job(args.job_id)
    job_dir = _find_job_directory(args.job_id)

    manifest_data: dict[str, Any] | None = None
    if job_dir:
        manifest_file = job_dir / "artifacts_manifest.json"
        if manifest_file.exists():
            try:
                manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.debug("Error leyendo manifest en %s: %s", manifest_file, e)

    if not job and not manifest_data and not job_dir:
        print(f"Job no encontrado: {args.job_id}", file=sys.stderr)
        return 1

    fmt = getattr(args, "format", "markdown") or "markdown"
    fmt = fmt.lower()
    export_dir = getattr(args, "output", None) or f"exports/{args.job_id}"
    out_dir_path = Path(export_dir)
    out_dir_path.mkdir(parents=True, exist_ok=True)

    # Cargar artefactos de texto si existen
    artifacts_content = _load_job_artifacts(job_dir)

    title = (
        job.source_title
        if job and job.source_title
        else (
            manifest_data.get("sources", [{}])[0].get("title")
            if manifest_data and manifest_data.get("sources")
            else "Video"
        )
    )
    source_url = (
        job.source_url
        if job and job.source_url
        else (
            manifest_data.get("sources", [{}])[0].get("original_input", "")
            if manifest_data and manifest_data.get("sources")
            else ""
        )
    )
    status_val = (
        (job.status.value if hasattr(job.status, "value") else str(job.status))
        if job
        else "completed"
    )

    if fmt == "json":
        data: dict[str, Any] = job.to_dict() if job else (manifest_data or {})
        data["exported_artifacts"] = dict(artifacts_content)
        out_file = out_dir_path / "export.json"
        out_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Exportado a {out_file}")

    elif fmt == "html":
        html_code = _generate_standalone_html(
            job_id=args.job_id,
            title=title,
            status_val=status_val,
            source_url=source_url,
            artifacts=artifacts_content,
        )
        out_file = out_dir_path / "export.html"
        out_file.write_text(html_code, encoding="utf-8")
        print(f"Exportado a {out_file}")

    elif fmt in ("obsidian", "vault"):
        md_code = _generate_obsidian_markdown(
            job_id=args.job_id,
            title=title,
            status_val=status_val,
            source_url=source_url,
            artifacts=artifacts_content,
            manifest=manifest_data,
        )
        out_file = out_dir_path / "export.md"
        out_file.write_text(md_code, encoding="utf-8")
        print(f"Exportado a {out_file}")

    else:
        # Markdown estándar (default)
        if "knowledge_report" in artifacts_content:
            md_text = artifacts_content["knowledge_report"]
        else:
            chunks = [
                f"# Export job {args.job_id}\n",
                "## Resumen\n",
                f"- **Job ID**: {args.job_id}",
                f"- **Estado**: {status_val}",
                f"- **Título**: {title}",
                f"- **Fuente**: {source_url}\n",
            ]
            if "executive_summary" in artifacts_content:
                chunks.append("## Dossier Ejecutivo\n\n" + artifacts_content["executive_summary"])
            if "toc" in artifacts_content:
                chunks.append("## Tabla de Contenidos\n\n" + artifacts_content["toc"])
            if "transcript" in artifacts_content:
                chunks.append("## Transcripción\n\n" + artifacts_content["transcript"])
            if "visual_context" in artifacts_content:
                chunks.append("## Contexto Visual\n\n" + artifacts_content["visual_context"])
            md_text = "\n\n".join(chunks).strip() + "\n"

        out_file = out_dir_path / "export.md"
        out_file.write_text(md_text, encoding="utf-8")
        print(f"Exportado a {out_file}")

    return 0


def export_command(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    export_p = subparsers.add_parser("export", help="Exporta resultados de un job.")
    export_p.add_argument("job_id", help="ID del job.")
    export_p.add_argument(
        "--format",
        "-f",
        choices=["markdown", "json", "html", "obsidian"],
        default="markdown",
        help="Formato de exportación: markdown, json, html, obsidian (default: markdown).",
    )
    export_p.add_argument("--output", "-o", type=str, default=None, help="Directorio de salida.")
    export_p.set_defaults(func=run_export)
    return export_p
