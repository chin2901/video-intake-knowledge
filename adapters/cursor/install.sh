#!/usr/bin/env bash
# =============================================================================
# install.sh — Cursor Adapter Installer for video-intake-knowledge
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

GLOBAL_CURSOR="${HOME}/.cursor"
CURSOR_SKILLS="${GLOBAL_CURSOR}/skills/video-intake"

echo "Instalando adaptador Cursor para video-intake-knowledge..."

# 1. Instalar skill canónico en ~/.cursor/skills/video-intake
mkdir -p "$CURSOR_SKILLS"
ln -sf "$ROOT_DIR/SKILL.md" "$CURSOR_SKILLS/SKILL.md"
echo "  [OK] Skill enlazada en $CURSOR_SKILLS/SKILL.md"

# 2. Configurar .cursorrules global
mkdir -p "$GLOBAL_CURSOR"
if [[ -f "$SCRIPT_DIR/.cursorrules" ]]; then
    cp "$SCRIPT_DIR/.cursorrules" "$GLOBAL_CURSOR/rules-video-intake"
    echo "  [OK] Reglas copiadas a $GLOBAL_CURSOR/rules-video-intake"
fi

# 3. Si existe workspace local, configurar .cursor/skills/
WORKSPACE_DIR="${1:-}"
if [[ -n "$WORKSPACE_DIR" && -d "$WORKSPACE_DIR" ]]; then
    mkdir -p "$WORKSPACE_DIR/.cursor/skills"
    ln -sf "$ROOT_DIR/SKILL.md" "$WORKSPACE_DIR/.cursor/skills/video-intake.SKILL.md"
    if [[ ! -f "$WORKSPACE_DIR/.cursorrules" ]]; then
        cp "$SCRIPT_DIR/.cursorrules" "$WORKSPACE_DIR/.cursorrules"
        echo "  [OK] Workspace .cursorrules creado en $WORKSPACE_DIR/.cursorrules"
    fi
    echo "  [OK] Workspace skill enlazada en $WORKSPACE_DIR/.cursor/skills/"
fi

echo "Adaptador Cursor instalado correctamente."
