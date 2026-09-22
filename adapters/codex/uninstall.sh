#!/usr/bin/env bash
# =============================================================================
# uninstall.sh — Desinstalador del adaptador Codex para video-intake-knowledge
# =============================================================================

set -euo pipefail

PREFIX="${PREFIX:-$HOME/.codex}"
TARGET_DIR="$PREFIX/skills/video-intake"

echo "Desinstalando skill de video-intake-knowledge para Codex..."

if [[ -d "$TARGET_DIR" ]]; then
    rm -rf "$TARGET_DIR"
    echo "  [OK] Eliminado directorio $TARGET_DIR"
else
    echo "  [INFO] No se encontró instalación previa en $TARGET_DIR"
fi

echo "Desinstalación de Codex completada."
