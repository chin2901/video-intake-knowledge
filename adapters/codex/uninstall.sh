# =============================================================================
# uninstall.sh — Desinstalador del plugin Hermes para video-intake-knowledge
# =============================================================================
#
# Uso: bash uninstall.sh [--prefix ~/.hermes] [--dry-run]
#
# Elimina el plugin de la configuración de Hermes Agent.
#
# =============================================================================

set -e

PREFIX="${PREFIX:-$HOME/.hermes}"
DRY_RUN="${DRY_RUN:-}"

echo "Prefix: $PREFIX"
echo "Dry run: ${DRY_RUN:+yes}"

# =============================================================================
# Verificar dependencias
# =============================================================================

if ! command -v python3 &>/dev/null; then
    echo "✗ python3 no encontrado — no se puede continuar"
    exit 1
fi

# =============================================================================
# Desinstalar plugin
# =============================================================================

uninstall_plugin() {
    echo ""
    echo "=== Desinstalando plugin de Hermes ==="

    # Eliminar archivos del plugin
    if [[ -d "$PREFIX/plugin-data/video-intake-knowledge-adapters" ]]; then
        if [[ -n "$DRY_RUN" ]]; then
            echo "[DRY-RUN] Eliminar: $PREFIX/plugin-data/video-intake-knowledge-adapters"
        else
            rm -rf "$PREFIX/plugin-data/video-intake-knowledge-adapters"
            echo "✓ Plugin eliminado"
        fi
    else
        echo "⚠ Plugin no encontrado en $PREFIX/plugin-data/video-intake-knowledge-adapters"
    fi

    # Eliminar entrada del registry si existe
    if [[ -f "$PREFIX/plugin-data/registry.yaml" ]]; then
        if [[ -n "$DRY_RUN" ]]; then
            echo "[DRY-RUN] Eliminar entrada de video-intake-knowledge de registry.yaml"
        else
            # Usar sed para eliminar las líneas del plugin
            if grep -q "video-intake-knowledge" "$PREFIX/plugin-data/registry.yaml" 2>/dev/null; then
                # Eliminar bloque del plugin (desde '# video-intake-knowledge plugin' hasta siguientes líneas vacías)
                sed -i '/^# video-intake-knowledge plugin$/,/^$/d' "$PREFIX/plugin-data/registry.yaml"
                echo "✓ Entrada eliminada del registry"
            else
                echo "✓ Plugin no estaba registrado"
            fi
        fi
    fi
}

# =============================================================================
# Desinstalar dependencias de Python
# =============================================================================

uninstall_python() {
    echo ""
    echo "=== Desinstalando dependencias de Python ==="

    if [[ -n "$DRY_RUN" ]]; then
        echo "[DRY-RUN] Desinstalar video-intake-knowledge"
    else
        # Intentar desinstalar el paquete si fue instalado con pip
        python3 -m pip uninstall -y video-intake-knowledge 2>/dev/null || true
        echo "✓ Dependencias desinstaladas (si estaban instaladas)"
    fi
}

# =============================================================================
# Limpieza de datos
# =============================================================================

clean_data() {
    echo ""
    echo "=== Limpieza de datos ==="

    # Preguntar si desea eliminar datos
    if [[ -n "$DRY_RUN" ]]; then
        echo "[DRY-RUN] No se eliminarían datos automáticamente"
        return
    fi

    echo "¿Desea eliminar los datos de vídeos procesados?"
    echo "  (directorios de trabajos, artefactos, memoria, logs)"
    echo ""
    echo "  [1] Sí, eliminar todos los datos"
    echo "  [2] No, conservar los datos"
    echo ""

    read -r choice

    case "$choice" in
        1)
            # Eliminar directorios de datos
            rm -rf "$HOME/.video-intake-knowledge" 2>/dev/null || true
            echo "✓ Datos eliminados"
            ;;
        2)
            echo "✓ Datos conservados"
            ;;
        *)
            echo "⚠ Opción no válida — datos conservados"
            ;;
    esac
}

# =============================================================================
# Verificar desinstalación
# =============================================================================

verify_uninstall() {
    echo ""
    echo "=== Verificando desinstalación ==="

    if command -v vitk &>/dev/null; then
        echo "⚠ Comando 'vitk' todavía disponible — eliminar de PATH si es necesario"
    else
        echo "✓ Comando 'vitk' no disponible"
    fi

    if python3 -c "import video_intake_core" 2>/dev/null; then
        echo "⚠ Paquete Python todavía importable — desinstalar manualmente si es necesario"
    else
        echo "✓ Paquete Python no importable"
    fi
}

# =============================================================================
# Main
# =============================================================================

main() {
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║  Desinstalación de plugin Hermes — video-intake-knowledge ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""

    uninstall_plugin
    uninstall_python
    clean_data
    verify_uninstall

    echo ""
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║  Desinstalación completada                                 ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
}

main "$@"
