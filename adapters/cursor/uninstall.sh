#!/usr/bin/env bash
# =============================================================================
# uninstall.sh — Desinstalador del adaptador Cursor para video-intake-knowledge
# =============================================================================

set -euo pipefail

GLOBAL_CURSOR="${HOME}/.cursor"
CURSOR_SKILLS="${GLOBAL_CURSOR}/skills/video-intake"

echo "Desinstalando adaptador Cursor para video-intake-knowledge..."

if [[ -d "$CURSOR_SKILLS" ]]; then
    rm -rf "$CURSOR_SKILLS"
    echo "  [OK] Eliminado directorio $CURSOR_SKILLS"
fi

if [[ -f "$GLOBAL_CURSOR/rules-video-intake" ]]; then
    rm -f "$GLOBAL_CURSOR/rules-video-intake"
    echo "  [OK] Eliminado $GLOBAL_CURSOR/rules-video-intake"
fi

echo "Desinstalación de Cursor completada."
