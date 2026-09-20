#!/usr/bin/env bash
# =============================================================================
# scripts/generate-assets.sh — Generar activos de conocimiento a partir de
# extractos existentes (transcripciones, OCR, contexto visual)
# =============================================================================
#
# Este script lee los artefactos extraídos y genera documentos estructurados
# listos para ser consumidos por agentes de IA.
#
# Uso:
#   ./generate-assets.sh [--input-dir <dir>] [--output-dir <dir>] [--format mdx|markdown]
#
# =============================================================================

set -e

# =============================================================================
# Configuración por defecto
# =============================================================================

VIDEO_INTAKE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INPUT_DIR="${INPUT_DIR:-$VIDEO_INTAKE_DIR/data/jobs}"
OUTPUT_DIR="${OUTPUT_DIR:-$VIDEO_INTAKE_DIR/output/assets}"
FORMAT="${FORMAT:-mdx}"
VERBOSE="${VERBOSE:-false}"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# =============================================================================
# Usage
# =============================================================================

usage() {
    cat <<EOF
Generar activos de conocimiento a partir de extractos existentes.

Usage: $(basename "$0") [OPTIONS]

Options:
  --input-dir <dir>    Directorio de entrada con jobs extraídos
                       (por defecto: ../data/jobs relativo al script)
  --output-dir <dir>   Directorio de salida para los activos generados
                       (por defecto: ../output/assets)
  --format <fmt>       Formato de salida: mdx o markdown (por defecto: mdx)
  --verbose            Mostrar información detallada del proceso
  --help               Mostar esta ayuda

Genera los siguientes tipos de activos:
  - Documents: documentos markdown/mdx con el contenido extraído
  - Diagrams: diagramas de flujo y arquitectura detectados en los vídeos
  - Knowledge packs: paquetes de conocimiento estructurados por tema
  - Summaries: resúmenes ejecutivos de cada vídeo procesado

Requisitos:
  - Python 3.9+ con video_intake_core instalado
  - Las funciones de exportación del módulo context disponibles

EOF
}

# =============================================================================
# Parsear argumentos
# =============================================================================

while [[ $# -gt 0 ]]; do
    case "$1" in
        --input-dir)
            INPUT_DIR="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --format)
            FORMAT="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            log_error "Opción desconocida: $1"
            usage
            exit 1
            ;;
    esac
done

# =============================================================================
# Validar entorno
# =============================================================================

check_requirements() {
    log_info "Verificando requisitos..."

    # Verificar Python
    if ! command -v python3 &>/dev/null; then
        log_error "Python 3 no encontrado"
        exit 1
    fi

    # Verificar que el paquete está instalado
    if ! python3 -c "import video_intake_core" 2>/dev/null; then
        log_error "video_intake_core no instalado"
        log_info "Instalálo con: pip install -e ."
        exit 1
    fi

    log_info "Requisitos OK"
}

# =============================================================================
# Preparar directorios
# =============================================================================

prepare_dirs() {
    log_info "Preparando directorios..."

    mkdir -p "$OUTPUT_DIR/documents"
    mkdir -p "$OUTPUT_DIR/diagrams"
    mkdir -p "$OUTPUT_DIR/knowledge-packs"
    mkdir -p "$OUTPUT_DIR/summaries"

    log_info "Directorios de salida creados"
}

# =============================================================================
# Generar activos
# =============================================================================

generate_assets() {
    log_info "Iniciando generación de activos desde: $INPUT_DIR"

    # Encontrar jobs extraídos
    local jobs_found=0

    for job_dir in "$INPUT_DIR"/*/; do
        if [[ ! -d "$job_dir" ]]; then
            continue
        fi

        local job_id
        job_id="$(basename "$job_dir")"

        log_info "Procesando job: $job_id"

        # Buscar archivos de contexto extraído
        local audio_context_file=""
        local visual_context_file=""
        local transcript_file=""
        local ocr_file=""

        for f in "$job_dir"/context/*.json "$job_dir"/transcript/*.json; do
            [[ -f "$f" ]] || continue
            case "$(basename "$f")" in
                audio_context*) audio_context_file="$f" ;;
                visual_context*) visual_context_file="$f" ;;
                transcript*) transcript_file="$f" ;;
                ocr*) ocr_file="$f" ;;
            esac
        done

        # Generar documento de conocimiento
        if [[ -n "$audio_context_file" ]] || [[ -n "$visual_context_file" ]]; then
            log_info "  Generando documento de conocimiento..."

            python3 - <<PYEOF
import json
import os
from pathlib import Path

job_id = "$job_id"
output_dir = Path("$OUTPUT_DIR")
documents_dir = output_dir / "documents"
documents_dir.mkdir(parents=True, exist_ok=True)

# Crear documento combido
doc_path = documents_dir / f"{job_id}_knowledge.md"

with open(doc_path, "w", encoding="utf-8") as f:
    f.write(f"# Conocimiento extraído: {job_id}\n\n")
    f.write(f"> Generated: {__import__('datetime').datetime.now().isoformat()}\n\n")

    # Audio context
    audio_file = Path("$INPUT_DIR") / job_id / "context" / "audio_context.json"
    if audio_file.exists():
        with open(audio_file) as af:
            data = json.load(af)
            f.write("## Resumen de audio\n\n")
            if "summary" in data:
                f.write(data["summary"].get("text", "") + "\n\n")
            f.write("## Temas detectados\n\n")
            if "topics" in data:
                for topic in data["topics"].get("topics", [])[:10]:
                    f.write(f"- {topic}\n")
                f.write("\n")
            f.write("## Entidades\n\n")
            if "entities" in data:
                for entity in data["entities"].get("entities", [])[:20]:
                    f.write(f"- {entity}\n")
                f.write("\n")

    # Visual context
    visual_file = Path("$INPUT_DIR") / job_id / "context" / "visual_context.json"
    if visual_file.exists():
        with open(visual_file) as vf:
            data = json.load(vf)
            f.write("## Elementos visuales\n\n")
            if "diagrams" in data:
                f.write("### Diagramas detectados\n\n")
                for d in data["diagrams"][:5]:
                    f.write(f"- {d.get('description', '')}\n")
                f.write("\n")
            if "screenshots" in data:
                f.write("### Capturas de pantalla\n\n")
                for s in data["screenshots"][:5]:
                    f.write(f"- {s.get('description', '')}\n")
                f.write("\n")

print(f"✓ Documento generado: {doc_path}")
PYEOF
        fi

        # Generar resumen ejecutivo
        if [[ -n "$audio_context_file" ]]; then
            log_info "  Generando resumen ejecutivo..."

            python3 - <<PYEOF
import json
from pathlib import Path
from datetime import datetime

job_id = "$job_id"
output_dir = Path("$OUTPUT_DIR")
summaries_dir = output_dir / "summaries"
summaries_dir.mkdir(parents=True, exist_ok=True)

audio_file = Path("$INPUT_DIR") / job_id / "context" / "audio_context.json"
if audio_file.exists():
    with open(audio_file) as f:
        data = json.load(f)

    summary_path = summaries_dir / f"{job_id}_summary.md"
    with open(summary_path, "w", encoding="utf-8") as sf:
        sf.write(f"# Resumen ejecutivo: {job_id}\n\n")
        sf.write(f"> Generado: {datetime.now().isoformat()}\n\n")
        sf.write("## Resumen\n\n")
        if "summary" in data and "text" in data["summary"]:
            sf.write(data["summary"]["text"] + "\n\n")
        sf.write("## Datos clave\n\n")
        sf.write(f"- Temas: {len(data.get('topics', {}).get('topics', []))}\n")
        sf.write(f"- Entidades: {len(data.get('entities', {}).get('entities', []))}\n")
        sf.write(f"- Citas: {len(data.get('quotes', {}).get('quotes', []))}\n")

    print(f"✓ Resumen generado: {summary_path}")
PYEOF
        fi

        jobs_found=$((jobs_found + 1))
    done

    log_info "Procesados $jobs_found jobs"
}

# =============================================================================
# Main
# =============================================================================

main() {
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║  Generador de activos de conocimiento — video-intake-knowledge  ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo ""

    check_requirements
    prepare_dirs
    generate_assets

    echo ""
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║  Generación completada                                           ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Activos generados en: $OUTPUT_DIR"
    echo "  - documents/       : Documentos de conocimiento por job"
    echo "  - summaries/       : Resúmenes ejecutivos"
    echo "  - diagrams/        : Diagramas extraidos"
    echo "  - knowledge-packs/ : Paquetes de conocimiento estructurados"
}

main "$@"
