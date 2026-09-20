# =============================================================================
# install.sh — Instalador del plugin Hermes para video-intake-knowledge
# =============================================================================
#
# Uso: bash install.sh [--prefix ~/.hermes] [--dry-run]
#
# Instala el plugin en la configuración de Hermes Agent para que las
# herramientas de video-intake-knowledge estén disponibles desde el asistente.
#
# =============================================================================

set -e

PREFIX="${PREFIX:-$HOME/.hermes}"
DRY_RUN="${DRY_RUN:-}"

# =============================================================================
# Resolver la ubicación de la instalación del plugin
# =============================================================================

RESOLVED_PREFIX="$PREFIX"

if [[ -f "$PREFIX/plugin-data/video-intake-knowledge/adapters/hermes/install.sh" ]]; then
    # Desde un clon existente de video-intake-knowledge
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
    PLUGIN_DIR="$PROJECT_DIR/adapters/hermes"
elif [[ -f "$PREFIX/plugins/video-intake-knowledge/adapters/hermes/install.sh" ]]; then
    # Desde un clon dentro de plugins de Hermes
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
    PLUGIN_DIR="$PROJECT_DIR/adapters/hermes"
else
    # Instalación directa: usar el directorio de scripts
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PLUGIN_DIR="$SCRIPT_DIR"
fi

echo "Prefix: $RESOLVED_PREFIX"
echo "Plugin dir: $PLUGIN_DIR"
echo "Dry run: ${DRY_RUN:+yes}"

# =============================================================================
# Verificar dependencias
# =============================================================================

check_dependency() {
    local cmd="$1"
    local pkg="${2:-$cmd}"
    if ! command -v "$cmd" &>/dev/null; then
        echo "⚠ Dependencia no encontrada: $cmd (instalar: $pkg)"
        return 1
    fi
    echo "✓ $cmd encontrado"
    return 0
}

missing=0

# Verificar herramientas del sistema
if ! command -v python3 &>/dev/null; then
    echo "✗ python3 no encontrado — no se puede continuar"
    missing=1
fi

if ! command -v uv &>/dev/null; then
    echo "⚠ uv no encontrado — se recomienda instalar uv para gestión de dependencias"
fi

if [[ $missing -eq 1 ]]; then
    echo "✗ Dependencias faltantes — instalarlas e intentar de nuevo."
    exit 1
fi

# =============================================================================
# Instalar dependencias de Python si es necesario
# =============================================================================

install_python_deps() {
    echo ""
    echo "=== Instalando dependencias de Python ==="

    if [[ -f "$PLUGIN_DIR/requirements.txt" ]]; then
        # Usar requirements.txt si existe
        python3 -m pip install -r "$PLUGIN_DIR/requirements.txt" --quiet
    elif [[ -f "$PLUGIN_DIR/pyproject.toml" ]]; then
        # Usar pyproject.toml con uv si está disponible
        if command -v uv &>/dev/null; then
            uv pip install -e "$PLUGIN_DIR" --quiet
        else
            python3 -m pip install -e "$PLUGIN_DIR" --quiet
        fi
    else
        echo "⚠ No se encontró pyproject.toml ni requirements.txt — instalar manualmente"
        echo "  pip install video-intake-knowledge"
    fi

    echo "✓ Dependencias instaladas"
}

# =============================================================================
# Configurar plugin en Hermes
# =============================================================================

configure_plugin() {
    echo ""
    echo "=== Configurando plugin en Hermes ==="

    # Crear directorio de plugins si no existe
    mkdir -p "$PREFIX/plugin-data"

    # Copiar archivos del plugin
    if [[ -d "$PLUGIN_DIR" ]]; then
        cp -r "$PLUGIN_DIR" "$PREFIX/plugin-data/video-intake-knowledge-adapters" 2>/dev/null || true
        echo "✓ Archivos del plugin copiados"
    fi

    # Registrar plugin si Hermes lo soporta (hermos de config)
    if [[ -f "$PREFIX/plugin-data/registry.yaml" ]]; then
        # Agregar entrada al registry si no existe
        if ! grep -q "video-intake-knowledge" "$PREFIX/plugin-data/registry.yaml" 2>/dev/null; then
            echo "" >> "$PREFIX/plugin-data/registry.yaml"
            echo "# video-intake-knowledge plugin" >> "$PREFIX/plugin-data/registry.yaml"
            echo "- name: video-intake-knowledge" >> "$PREFIX/plugin-data/registry.yaml"
            echo "  version: 1.0.0" >> "$PREFIX/plugin-data/registry.yaml"
            echo "  enabled: true" >> "$PREFIX/plugin-data/registry.yaml"
            echo "✓ Plugin registrado en registry.yaml"
        else
            echo "✓ Plugin ya registrado"
        fi
    else
        echo "⚠ No se encontró registry.yaml — plugin disponible manualmente"
    fi
}

# =============================================================================
# Verificar instalación
# =============================================================================

verify_installation() {
    echo ""
    echo "=== Verificando instalación ==="

    if command -v vitk &>/dev/null; then
        echo "✓ Comando 'vitk' disponible"
        vitk --version 2>/dev/null || vitk --help 2>/dev/null | head -5
    else
        echo "⚠ Comando 'vitk' no disponible — agregar a PATH o usar 'python3 -m video_intake_core.cli'"
    fi

    if python3 -c "import video_intake_core" 2>/dev/null; then
        echo "✓ Paquete Python importable"
    else
        echo "⚠ Paquete Python no importable — verificiar instalación"
    fi
}

# =============================================================================
# Main
# =============================================================================

main() {
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║  Instalación de plugin Hermes — video-intake-knowledge   ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""

    install_python_deps
    configure_plugin
    verify_installation

    echo ""
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║  Instalación completada                                    ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""
    echo "Para usar el plugin:"
    echo "  1. Reinicia Hermes Agent si está ejecutándose"
    echo "  2. Las herramientas de video-intake-knowledge deberían"
    echo "     estar disponibles como tools del asistente"
    echo ""
    echo "Comandos disponibles:"
    echo "  vitk doctor              — Diagnóstico del entorno"
    echo "  vitk extract <url>       — Extracción interactiva de vídeo"
    echo "  vitk batch <archivo>     — Procesamiento por lotes"
    echo "  vitk status              — Estado de trabajos"
    echo "  vitk artifacts           — Listado de artefactos"
    echo "  vitk config validate     — Validar configuración"
}

main "$@"
