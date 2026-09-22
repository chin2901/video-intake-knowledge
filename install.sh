#!/usr/bin/env bash
# =============================================================================
# install.sh — Instalador universal de video-intake-knowledge
# =============================================================================
# Compatible con: Hermes Agent, AGY (Antigravity), OpenCode, Claude Code, Cursor, Codex
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"

print_usage() {
    echo "Uso: $0"
    echo ""
    echo "Instala el CLI video-intake y enlazará automáticamente el SKILL.md a"
    echo "los entornos de agentes detectados en tu sistema."
    echo ""
}

if [[ $# -gt 0 ]]; then
    if [[ "$1" == "--help" || "$1" == "-h" ]]; then
        print_usage
        exit 0
    fi
fi

echo "====================================================================="
echo " Instalador Universal de Video-Intake"
echo "====================================================================="
echo "Directorio base: $ROOT_DIR"
echo ""

# 1. Comprobación de Python
echo "[1/4] Comprobando Python..."
if command -v python3 &>/dev/null; then
    PY_BIN="$(command -v python3)"
else
    echo "ERROR: No se encontró Python 3 instalado en el sistema." >&2
    exit 1
fi
PY_VERSION=$("$PY_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "  Python detectado: $PY_BIN (versión $PY_VERSION)"

# 2. Entorno virtual e instalación
echo "[2/4] Instalando paquete y CLI (video-intake)..."
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
    if [[ ! -d "$ROOT_DIR/venv" ]]; then
        "$PY_BIN" -m venv "$ROOT_DIR/venv"
    fi
    PIP_CMD="$ROOT_DIR/venv/bin/pip"
    PYTHON_EXEC="$ROOT_DIR/venv/bin/python3"
else
    PIP_CMD="pip"
    PYTHON_EXEC="$PY_BIN"
fi

"$PIP_CMD" install -e "$ROOT_DIR" --quiet
echo "  [OK] Dependencias de Python instaladas."

# Crear symlink en ~/.local/bin
LOCAL_BIN="$HOME/.local/bin"
mkdir -p "$LOCAL_BIN"
if [[ -f "$ROOT_DIR/venv/bin/video-intake" ]]; then
    ln -sf "$ROOT_DIR/venv/bin/video-intake" "$LOCAL_BIN/video-intake"
    echo "  [OK] CLI habilitado globalmente: $LOCAL_BIN/video-intake"
fi

# 3. Integraciones de Skill
echo "[3/4] Instalando SKILL.md en entornos detectados..."

install_skill_to() {
    local target_dir="$1"
    local name="$2"
    mkdir -p "$target_dir"
    ln -sf "$ROOT_DIR/skill/SKILL.md" "$target_dir/SKILL.md"
    echo "  [OK] $name: SKILL vinculada en $target_dir"
}

# Hermes Agent
if [[ -d "$HOME/.hermes" ]]; then
    install_skill_to "$HOME/.hermes/skills/video-intake" "Hermes Agent"
fi
# OpenCode
if [[ -d "$HOME/.opencode" ]]; then
    install_skill_to "$HOME/.opencode/skills/video-intake" "OpenCode"
fi
# Claude Code
if [[ -d "$HOME/.claude" ]]; then
    install_skill_to "$HOME/.claude/skills/video-intake" "Claude Code"
fi
# AGY (Antigravity CLI)
if [[ -d "$HOME/.gemini/antigravity-cli" ]]; then
    install_skill_to "$HOME/.gemini/antigravity-cli/skills/video-intake" "Antigravity (AGY)"
fi
# Codex
if [[ -d "$HOME/.codex" ]]; then
    install_skill_to "$HOME/.codex/skills/video-intake" "Codex"
fi
# Cursor
if [[ -d "$HOME/.cursor" ]]; then
    install_skill_to "$HOME/.cursor/skills/video-intake" "Cursor"
fi

echo ""
echo "[4/4] Comprobando salud del sistema..."
"$PYTHON_EXEC" -m video_intake_core.cli doctor || true

echo "====================================================================="
echo " ¡Todo listo! La herramienta está instalada."
echo " Usa: video-intake interactive <URL> o pásale un link a tu agente."
echo "====================================================================="
