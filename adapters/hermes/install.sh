#!/bin/bash
# =============================================================================
# install.sh — Instalación del plugin de Hermes para video-intake-knowledge
# =============================================================================
#
# Instala el plugin de Hermes en el directorio de plugins del usuario.
#
# Uso:
#   chmod +x install.sh
#   ./install.sh [--prefix DIR]
#
# Opciones:
#   --prefix DIR   Directorio de plugins de Hermes (por defecto: ~/.hermes)
#
# Requiere: bash 4+, cp, mkdir
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_NAME="video-intake-knowledge"
DEFAULT_PREFIX="$HOME/.hermes/plugins"

PREFIX="$DEFAULT_PREFIX"
SKIP_CONFIRM=false

usage() {
    echo "Uso: $(basename "$0") [--prefix DIR] [--yes]"
    echo ""
    echo "Instala el plugin de Hermes para video-intake-knowledge."
    echo ""
    echo "Opciones:"
    echo "  --prefix DIR    Directorio de plugins de Hermes"
    echo "                  (por defecto: $DEFAULT_PREFIX)"
    echo "  --yes, -y       No preguntar confirmación"
    echo "  --help, -h      Muestra esta ayuda"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --prefix)
            PREFIX="$2"
            shift 2
            ;;
        --yes|-y)
            SKIP_CONFIRM=true
            shift
            ;;
        --help|-h)
            usage
            ;;
        *)
            echo "Opción desconocida: $1" >&2
            usage
            ;;
    esac
done

log_info()  { echo "[install] $*"; }
log_ok()    { echo "[install] ✓ $*"; }
log_warn()  { echo "[install] ⚠ $*"; }
log_error() { echo "[install] ✗ $*" >&2; }

if [[ ! -f "$SCRIPT_DIR/plugin.yaml" ]]; then
    log_error "plugin.yaml no encontrado en $SCRIPT_DIR"
    exit 1
fi

TARGET_DIR="$PREFIX/$PLUGIN_NAME"

if [[ -d "$TARGET_DIR" ]]; then
    if [[ "$SKIP_CONFIRM" != "true" ]]; then
        read -p "El plugin ya está instalado en $TARGET_DIR. ¿Reemplazar? [y/N]: " confirm
        if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
            log_info "Instalación cancelada."
            exit 0
        fi
    fi
    log_info "Eliminando instalación anterior..."
    rm -rf "$TARGET_DIR"
fi

log_info "Instalando plugin en $TARGET_DIR..."

mkdir -p "$TARGET_DIR"

# Copiar archivos del plugin
cp "$SCRIPT_DIR/plugin.yaml" "$TARGET_DIR/"
cp -r "$SCRIPT_DIR/hooks" "$TARGET_DIR/" 2>/dev/null || true
cp -r "$SCRIPT_DIR/tools" "$TARGET_DIR/" 2>/dev/null || true
cp -r "$SCRIPT_DIR/skill" "$TARGET_DIR/" 2>/dev/null || true

# Copiar scripts necesarios
if [[ -f "$SCRIPT_DIR/../scripts/standalone_hermes.sh" ]]; then
    cp "$SCRIPT_DIR/../scripts/standalone_hermes.sh" "$TARGET_DIR/"
    chmod +x "$TARGET_DIR/standalone_hermes.sh" 2>/dev/null || true
fi

log_ok "Plugin instalado en $TARGET_DIR"

# Verificación
if [[ -f "$TARGET_DIR/plugin.yaml" ]]; then
    log_ok "plugin.yaml presente"
else
    log_error "plugin.yaml no se copió correctamente"
    exit 1
fi

# Instrucciones para el usuario
log_info ""
log_info "Instalación completada."
log_info ""
log_info "Para activar el plugin, añade esto a tu ~/.hermes/config.yaml:"
log_info ""
log_info "  plugins:"
log_info "    - video-intake-knowledge"
log_info ""
log_info "O reinicia Hermes para que detecte el plugin automáticamente."
log_info ""
log_info "Para verificar la instalación:"
log_info "  video-intake doctor"
log_info ""
log_info "Para desinstalar:"
log_info "  $TARGET_DIR/uninstall.sh"
