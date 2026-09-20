# =============================================================================
# uninstall.sh — Desinstalación del plugin de Hermes
# =============================================================================
#
# Elimina el plugin de video-intake-knowledge del directorio de plugins
# de Hermes.
#
# Uso:
#   chmod +x uninstall.sh
#   ./uninstall.sh [--prefix DIR] [--yes]
#
# Opciones:
#   --prefix DIR   Directorio de plugins de Hermes (por defecto: ~/.hermes)
#   --yes, -y      No preguntar confirmación
#
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
    echo "Desinstala el plugin de Hermes para video-intake-knowledge."
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

TARGET_DIR="$PREFIX/$PLUGIN_NAME"

if [[ ! -d "$TARGET_DIR" ]]; then
    echo "[uninstall] El plugin no está instalado en $TARGET_DIR"
    exit 0
fi

if [[ "$SKIP_CONFIRM" != "true" ]]; then
    read -p "¿Eliminar el plugin de $TARGET_DIR? [y/N]: " confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        echo "[uninstall] Desinstalación cancelada."
        exit 0
    fi
fi

log_info "Eliminando plugin de $TARGET_DIR..."
rm -rf "$TARGET_DIR"
log_ok "Plugin eliminado."

log_info ""
log_info "También debes eliminar la referencia en tu config.yaml de Hermes:"
log_info ""
log_info "  plugins:"
log_info "    - video-intake-knowledge  # <-- eliminar esta línea"
log_info ""
log_info "Reinicia Hermes para aplicar los cambios."
