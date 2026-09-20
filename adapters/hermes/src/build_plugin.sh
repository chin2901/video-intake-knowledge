#!/usr/bin/env bash
# =============================================================================
# src/build_plugin.sh — Script de construcción del plugin Hermes
# =============================================================================
#
# Compila y empaqueta el plugin de Hermes para video-intake-knowledge.
#
# Uso: bash adapters/hermes/src/build_plugin.sh [--output-dir <dir>]
#
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
OUTPUT_DIR="${OUTPUT_DIR:-$PROJECT_DIR/output/plugin}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

usage() {
    cat <<EOF
Construir y empaquetar el plugin Hermes.

Usage: $(basename "$0") [OPTIONS]

Options:
  --output-dir <dir>   Directorio de salida para el plugin empaquetado
                       (por defecto: output/plugin)
  --help               Muestra esta ayuda

EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) log_error "Opción desconocida: $1"; exit 1 ;;
    esac
done

log_info "Construyendo plugin Hermes para video-intake-knowledge..."
log_info "Output dir: $OUTPUT_DIR"

mkdir -p "$OUTPUT_DIR"

# Copiar archivos del plugin
log_info "Copiando archivos del plugin..."

cp "$PROJECT_DIR/adapters/hermes/plugin.yaml" "$OUTPUT_DIR/"
cp "$PROJECT_DIR/adapters/hermes/README.md" "$OUTPUT_DIR/"
cp "$PROJECT_DIR/adapters/hermes/config.example.yaml" "$OUTPUT_DIR/"
cp "$PROJECT_DIR/adapters/hermes/install.sh" "$OUTPUT_DIR/"
cp "$PROJECT_DIR/adapters/hermes/uninstall.sh" "$OUTPUT_DIR/"

# Copiar skill
if [ -d "$PROJECT_DIR/adapters/hermes/skill" ]; then
    cp -r "$PROJECT_DIR/adapters/hermes/skill" "$OUTPUT_DIR/"
fi

# Empaquetar
PLUGIN_NAME="video-intake-knowledge-hermes-plugin"
PLUGIN_TAR="$OUTPUT_DIR/${PLUGIN_NAME}.tar.gz"

cd "$OUTPUT_DIR"
tar -czf "$PLUGIN_TAR" \
    plugin.yaml \
    README.md \
    config.example.yaml \
    install.sh \
    uninstall.sh \
    skill/ 2>/dev/null || true

cd - > /dev/null

log_info "Plugin empaquetado: $PLUGIN_TAR"
log_info "Tamaño: $(du -h "$PLUGIN_TAR" | cut -f1)"

log_info ""
log_info "Para instalar:"
log_info "  bash adapters/hermes/install.sh"
log_info ""
log_info "Para desinstalar:"
log_info "  bash adapters/hermes/uninstall.sh"
