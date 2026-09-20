#!/usr/bin/env bash
# =============================================================================
# scripts/generate-knowledge-packs.sh — Generar paquetes de conocimiento
# estructurados por tema a partir de los extractos existentes.
# =============================================================================
#
# Agrupa el conocimiento extraído por temas y genera paquetes reutilizables
# para agentes de IA.
#
# Uso:
#   ./generate-knowledge-packs.sh [--input-dir <dir>] [--output-dir <dir>]
#
# =============================================================================

set -e

VIDEO_INTAKE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INPUT_DIR="${INPUT_DIR:-$VIDEO_INTAKE_DIR/data/jobs}"
OUTPUT_DIR="${OUTPUT_DIR:-$VIDEO_INTAKE_DIR/output/knowledge-packs}"
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
Generar paquetes de conocimiento por temas.

Usage: $(basename "$0") [OPTIONS]

Options:
  --input-dir <dir>    Directorio de entrada con jobs extraídos
  --output-dir <dir>   Directorio de salida para paquetes
  --verbose            Mostrar información detallada
  --help               Muestra esta ayuda

Genera paquetes JSON con:
  - Metadatos del paquete (título, tema, fecha, fuentes)
  - Contenido extraído relevante al tema
  - Referencias a los vídeos fuente

EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --input-dir) INPUT_DIR="$2"; shift 2 ;;
        --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
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
        exit 1
    }
    log_info "Requisitos OK"
}

generate_packs() {
    log_info "Generando paquetes de conocimiento desde: $INPUT_DIR"

    mkdir -p "$OUTPUT_DIR"

    python3 - <<PYEOF
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

input_dir = Path("$INPUT_DIR")
output_dir = Path("$OUTPUT_DIR")
verbose = "$VERBOSE" == "true"

# Recopilar todos los temas de todos los jobs
all_topics = defaultdict(list)  # tema -> [(job_id, contexto)]

for job_dir in sorted(input_dir.iterdir()):
    if not job_dir.is_dir():
        continue
    
    job_id = job_dir.name
    ctx_dir = job_dir / "context"
    if not ctx_dir.exists():
        continue
    
    # Buscar audio_context.json
    audio_file = ctx_dir / "audio_context.json"
    if not audio_file.exists():
        continue
    
    try:
        with open(audio_file, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        if verbose:
            print(f"  ⚠ Error procesando {job_id}: {e}")
        continue
    
    topics = data.get("topics", {}).get("topics", [])
    if not topics:
        continue
    
    # Extraer información relevante para cada tema
    for topic in topics:
        topic_lower = topic.lower()
        
        entry = {
            "job_id": job_id,
            "summary": data.get("summary", {}).get("text", ""),
            "timeline": data.get("timeline", {}),
            "entities": data.get("entities", {}).get("entities", []),
            "quotes": data.get("quotes", {}).get("quotes", [])[:5],
        }
        
        all_topics[topic_lower].append(entry)
    
    if verbose:
        print(f"  ✓ {job_id}: {len(topics)} temas encontrados")

# Generar paquete por tema
for topic, entries in sorted(all_topics.items()):
    if len(entries) < 1:
        continue
    
    # Normalizar nombre del tema para nombre de archivo
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in topic)
    safe_name = safe_name.strip("_")[:50] or "general"
    
    pack = {
        "topic": topic,
        "topic_normalized": safe_name,
        "generated_at": datetime.now().isoformat(),
        "total_entries": len(entries),
        "entries": entries,
        "summary": f"Paquete de conocimiento sobre '{topic}' con {len(entries)} fuentes.",
    }
    
    pack_file = output_dir / f"{safe_name}.json"
    with open(pack_file, "w", encoding="utf-8") as f:
        json.dump(pack, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Generado: {pack_file.name} ({len(entries)} entradas)")

print(f"\n✓ {len(all_topics)} paquetes generados en {output_dir}")
PYEOF
}

main() {
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║  Generador de paquetes de conocimiento — video-intake-knowledge  ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo ""

    check_requirements
    generate_packs

    echo ""
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║  Paquetes generados en: $OUTPUT_DIR                       ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
}

main "$@"
