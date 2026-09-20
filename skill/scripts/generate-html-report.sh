#!/usr/bin/env bash
# =============================================================================
# scripts/generate-html-report.sh — Generar informe HTML a partir de
# extractos existentes en data/jobs/<job_id>/context/
# =============================================================================
#
# Lee los archivos JSON de contexto y genera un informe HTML autónomo
# con resumen, temas, entidades, citas y elementos visuales.
#
# Uso:
#   ./generate-html-report.sh [--input-dir <dir>] [--output <file.html>]
#
# =============================================================================

set -e

VIDEO_INTAKE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INPUT_DIR="${INPUT_DIR:-$VIDEO_INTAKE_DIR/data/jobs}"
OUTPUT="${OUTPUT:-$VIDEO_INTAKE_DIR/output/report.html}"
VERBOSE="${VERBOSE:-false}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

usage() {
    cat <<EOF
Generar informe HTML a partir de extractos de vídeos procesados.

Usage: $(basename "$0") [OPTIONS]

Options:
  --input-dir <dir>   Directorio de entrada con jobs
                      (por defecto: ../data/jobs)
  --output <file>     Archivo HTML de salida
                      (por defecto: ../output/report.html)
  --verbose           Mostrar información detallada
  --help              Mostar esta ayuda

EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --input-dir) INPUT_DIR="$2"; shift 2 ;;
        --output) OUTPUT="$2"; shift 2 ;;
        --verbose) VERBOSE=true; shift ;;
        --help) usage; exit 0 ;;
        *) log_error "Opción desconocida: $1"; exit 1 ;;
    esac
done

check_requirements() {
    log_info "Verificando requisitos..."
    command -v python3 &>/dev/null || { log_error "Python 3 requerido"; exit 1; }
    python3 -c "import video_intake_core" 2>/dev/null || {
        log_error "video_intake_core no instalado"
        log_info "Instalálo con: pip install -e ."
        exit 1
    }
    log_info "Requisitos OK"
}

generate_html() {
    log_info "Generando informe HTML desde: $INPUT_DIR"

    python3 - <<PYEOF
import json
import os
from pathlib import Path
from datetime import datetime
from html import escape

input_dir = Path("$INPUT_DIR")
output_file = Path("$OUTPUT")
output_file.parent.mkdir(parents=True, exist_ok=True)

jobs = sorted([d for d in input_dir.iterdir() if d.is_dir()])

if not jobs:
    print("⚠ No se encontraron jobs en $INPUT_DIR")
    print("   Ejecutá video-intake-knowledge primero para extraer contenido.")
    exit(0)

docs = []

for job_dir in jobs:
    job_id = job_dir.name
    ctx_dir = job_dir / "context"
    if not ctx_dir.exists():
        continue

    # Cargar contextos
    audio_ctx = {}
    visual_ctx = {}
    knowledge_ctx = {}

    for f in ctx_dir.glob("*.json"):
        name = f.stem
        try:
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)
            if name == "audio_context":
                audio_ctx = data
            elif name == "visual_context":
                visual_ctx = data
            elif name == "knowledge_extraction":
                knowledge_ctx = data
        except Exception as e:
            if "$VERBOSE" == "true":
                print(f"  ⚠ Error leyendo {f.name}: {e}")

    # Construir secciones
    sections = []

    # Resumen
    if "summary" in audio_ctx:
        summary_text = audio_ctx["summary"].get("text", "")
        if summary_text:
            sections.append(("Resumen ejecutivo", summary_text))

    # Timeline
    if "timeline" in audio_ctx:
        timeline = audio_ctx["timeline"].get("segments", [])
        if timeline:
            items = []
            for seg in timeline[:20]:
                start = seg.get("start", "?")
                end = seg.get("end", "?")
                title = seg.get("title", "Sin título")
                items.append(f"<li><strong>[{start}s - {end}s]</strong> {escape(str(title))}</li>")
            sections.append(("Índice temporal", f"<ul>{''.join(items)}</ul>"))

    # Temas
    if "topics" in audio_ctx:
        topics = audio_ctx["topics"].get("topics", [])
        if topics:
            items = "".join(f"<li>{escape(str(t))}</li>" for t in topics[:20])
            sections.append(("Temas principales", f"<ul>{items}</ul>"))

    # Entidades
    if "entities" in audio_ctx:
        entities = audio_ctx["entities"].get("entities", [])
        if entities:
            items = "".join(f"<li><strong>{escape(str(e.get('name', '')))}</strong> — {escape(str(e.get('type', '')))}</li>" for e in entities[:30])
            sections.append(("Entidades", f"<ul>{items}</ul>"))

    # Citas
    if "quotes" in audio_ctx:
        quotes = audio_ctx["quotes"].get("quotes", [])
        if quotes:
            items = "".join(f"<blockquote class='quote'>{escape(str(q.get('text', '')))}<br><small>— {escape(str(q.get('speaker', 'Sin atribución')))}</small></blockquote>" for q in quotes[:10])
            sections.append(("Citas destacadas", f"<div class='quotes'>{items}</div>"))

    # Elementos visuales
    if visual_ctx:
        viz_sections = []
        if visual_ctx.get("diagrams"):
            d_items = "".join(f"<li><strong>{escape(str(d.get('description', '')))}</strong> — Confianza: {d.get('confidence', '?')}%</li>" for d in visual_ctx["diagrams"][:10])
            viz_sections.append(("Diagramas detectados", f"<ul>{d_items}</ul>"))
        if visual_ctx.get("screenshots"):
            s_items = "".join(f"<li>{escape(str(s.get('description', '')))}</li>" for s in visual_ctx["screenshots"][:10])
            viz_sections.append(("Capturas de pantalla", f"<ul>{s_items}</ul>"))
        if viz_sections:
            sections.append(("Contenido visual", "".join(viz_sections)))

    # Construir documento HTML
    html_parts = [
        "<!DOCTYPE html>",
        "<html lang='es'>",
        "<head>",
        "<meta charset='UTF-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1.0'>",
        f"<title>Informe de conocimiento — {escape(job_id)}</title>",
        "<style>",
        "body { font-family: system-ui, sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; line-height: 1.6; }",
        "h1 { color: #1a1a2e; border-bottom: 2px solid #4361ee; padding-bottom: 0.5rem; }",
        "h2 { color: #4361ee; margin-top: 2rem; }",
        "blockquote.quote { border-left: 4px solid #f72585; margin: 1rem 0; padding: 0.5rem 1rem; background: #fff5f7; font-style: italic; }",
        "ul { padding-left: 1.5rem; }",
        ".meta { color: #6c757d; font-size: 0.9rem; margin-bottom: 2rem; }",
        ".section { margin-bottom: 2rem; }",
        "</style>",
        "</head>",
        "<body>",
        f"<h1>🎬 Informe de conocimiento: {escape(job_id)}</h1>",
        f"<p class='meta'>Generated: {datetime.now().isoformat()}</p>",
    ]

    for title, content in sections:
        html_parts.append(f"<div class='section'><h2>{title}</h2>{content}</div>")

    html_parts.extend([
        "</body>",
        "</html>",
    ])

    html_content = "\n".join(html_parts)

    with open(output_file, "w", encoding="utf-8") as out:
        out.write(html_content)

    print(f"✓ Informe HTML generado: {output_file}")
PYEOF
}

main() {
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║  Generador de informes HTML — video-intake-knowledge             ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo ""

    check_requirements
    generate_html

    echo ""
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║  Informe generado: $OUTPUT                                ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
}

main "$@"
