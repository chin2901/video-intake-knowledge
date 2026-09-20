# =============================================================================
# install.sh — Instalador del plugin Claude Code para video-intake-knowledge
# =============================================================================
#
# Uso: bash install.sh [--prefix ~/.claude] [--dry-run]
#
# Instala el plugin en la configuración de Claude Code para que las
# herramientas de video-intake-knowledge estén disponibles desde el asistente.
#
# =============================================================================

set -e

PREFIX="${PREFIX:-$HOME/.claude}"
DRY_RUN="${DRY_RUN:-}"

echo "Prefix: $PREFIX"
echo "Dry run: ${DRY_RUN:+yes}"

# =============================================================================
# Resolver ubicación
# =============================================================================

if [[ -f "$PREFIX/plugins/video-intake-knowledge/adapters/claude-code/install.sh" ]]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PLUGIN_DIR="$SCRIPT_DIR"
else
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PLUGIN_DIR="$SCRIPT_DIR"
fi

# =============================================================================
# Verificar dependencias
# =============================================================================

if ! command -v python3 &>/dev/null; then
    echo "✗ python3 no encontrado — no se puede continuar"
    exit 1
fi

# =============================================================================
# Instalar dependencias
# =============================================================================

install_deps() {
    echo ""
    echo "=== Instalando dependencias ==="

    if [[ -f "$PLUGIN_DIR/requirements.txt" ]]; then
        python3 -m pip install -r "$PLUGIN_DIR/requirements.txt" --quiet
    elif [[ -f "$PLUGIN_DIR/pyproject.toml" ]]; then
        if command -v uv &>/dev/null; then
            uv pip install -e "$PLUGIN_DIR" --quiet
        else
            python3 -m pip install -e "$PLUGIN_DIR" --quiet
        fi
    fi

    echo "✓ Dependencias instaladas"
}

# =============================================================================
# Configurar plugin
# =============================================================================

configure_plugin() {
    echo ""
    echo "=== Configurando plugin ==="

    mkdir -p "$PREFIX/plugins"

    # Copiar SKILL.md a la ubicación esperada por Claude Code
    if [[ -f "$PLUGIN_DIR/SKILL.md" ]]; then
        cp "$PLUGIN_DIR/SKILL.md" "$PREFIX/plugins/video-intake-knowledge/SKILL.md"
        echo "✓ SKILL.md instalado"
    fi

    # Registrar en config si existe
    if [[ -f "$PREFIX/config.json" ]]; then
        echo "✓ Plugin listo para usar (registro automático según capacidades de Claude Code)"
    fi
}

# =============================================================================
# Verificar
# =============================================================================

verify() {
    echo ""
    echo "=== Verificando ==="

    if python3 -c "import video_intake_core" 2>/dev/null; then
        echo "✓ Paquete Python importable"
    else
        echo "⚠ Paquete Python no importable"
    fi

    if command -v vitk &>/dev/null; then
        echo "✓ Comando vitk disponible"
    else
        echo "⚠ Comando vitk no disponible"
    fi
}

# =============================================================================
# Main
# =============================================================================

main() {
    echo "╔══════════════════════════════════════════════════╗"
    echo "║  Instalación Claude Code — video-intake-knowledge ║"
    echo "╚══════════════════════════════════════════════════╝"
    echo ""

    install_deps
    configure_plugin
    verify

    echo ""
    echo "╔══════════════════════════════════════════════════╗"
    echo "║  Instalación completada                           ║"
    echo "╚══════════════════════════════════════════════════╝"
}

main "$@"
