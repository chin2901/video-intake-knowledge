#!/usr/bin/env bash
# =============================================================================
# install.sh — Instalador universal de video-intake-knowledge
# =============================================================================
# Compatible con: Hermes Agent, AGY, OpenCode, Claude Code, Codex y entornos CLI
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"

INSTALL_HERMES=false
INSTALL_AGY=false
INSTALL_CLAUDE=false
INSTALL_OPENCODE=false
INSTALL_CODEX=false
INSTALL_CURSOR=false
INSTALL_ALL=false
SKIP_DOCTOR=false

print_usage() {
    echo "Uso: $0 [opciones]"
    echo ""
    echo "Instala video-intake-knowledge y lo integra con entornos de agentes de IA."
    echo ""
    echo "Opciones de integración:"
    echo "  --hermes         Instalar/enlazar skill y plugin en Hermes Agent (~/.hermes)"
    echo "  --agy            Instalar/enlazar skill en AGY (~/.agy)"
    echo "  --claude-code    Instalar/enlazar skill en Claude Code (~/.claude)"
    echo "  --opencode       Instalar/enlazar skill en OpenCode (~/.opencode)"
    echo "  --codex          Instalar/enlazar skill en Codex (~/.codex)"
    echo "  --cursor         Instalar/enlazar skill y reglas en Cursor (~/.cursor)"
    echo "  --all            Instalar e integrar en todos los entornos detectados"
    echo "  --skip-doctor    Omitir la comprobación final de salud del sistema"
    echo "  --help, -h       Mostrar esta ayuda"
    echo ""
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --hermes)        INSTALL_HERMES=true; shift ;;
        --agy)           INSTALL_AGY=true; shift ;;
        --claude-code)   INSTALL_CLAUDE=true; shift ;;
        --opencode)      INSTALL_OPENCODE=true; shift ;;
        --codex)         INSTALL_CODEX=true; shift ;;
        --cursor)        INSTALL_CURSOR=true; shift ;;
        --all)           INSTALL_ALL=true; shift ;;
        --skip-doctor)   SKIP_DOCTOR=true; shift ;;
        --help|-h)       print_usage; exit 0 ;;
        *)               echo "Opción desconocida: $1" >&2; print_usage; exit 1 ;;
    esac
done

if $INSTALL_ALL; then
    INSTALL_HERMES=true
    INSTALL_AGY=true
    INSTALL_CLAUDE=true
    INSTALL_OPENCODE=true
    INSTALL_CODEX=true
    INSTALL_CURSOR=true
fi

echo "====================================================================="
echo " Instalador de video-intake-knowledge"
echo "====================================================================="
echo "Directorio base: $ROOT_DIR"
echo ""

# 1. Comprobación de Python
echo "[1/5] Comprobando Python..."
if command -v python3 &>/dev/null; then
    PY_BIN="$(command -v python3)"
elif command -v python &>/dev/null; then
    PY_BIN="$(command -v python)"
else
    echo "ERROR: No se encontró Python 3 instalado en el sistema." >&2
    exit 1
fi

PY_VERSION=$("$PY_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "  Python detectado: $PY_BIN (versión $PY_VERSION)"

# 2. Comprobación de herramientas del sistema
echo "[2/5] Comprobando herramientas del sistema (ffmpeg, tesseract)..."
if command -v ffmpeg &>/dev/null; then
    echo "  [OK] ffmpeg detectado ($(ffmpeg -version | head -n 1 | cut -d ' ' -f 3))"
else
    echo "  [AVISO] ffmpeg no detectado. Se recomienda: sudo apt install -y ffmpeg"
fi

if command -v tesseract &>/dev/null; then
    echo "  [OK] tesseract detectado ($(tesseract --version 2>&1 | head -n 1 | cut -d ' ' -f 2))"
else
    echo "  [AVISO] tesseract no detectado. Se recomienda: sudo apt install -y tesseract-ocr tesseract-ocr-spa"
fi

# 3. Entorno virtual e instalación de dependencias
echo "[3/5] Instalando dependencias de video-intake-knowledge..."
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
    if [[ ! -d "$ROOT_DIR/venv" ]]; then
        echo "  Creando entorno virtual en $ROOT_DIR/venv..."
        "$PY_BIN" -m venv "$ROOT_DIR/venv"
    fi
    # shellcheck disable=SC1091
    source "$ROOT_DIR/venv/bin/activate"
    PIP_CMD="$ROOT_DIR/venv/bin/pip"
    PYTHON_EXEC="$ROOT_DIR/venv/bin/python3"
else
    echo "  Usando entorno virtual activo: $VIRTUAL_ENV"
    PIP_CMD="pip"
    PYTHON_EXEC="$PY_BIN"
fi

echo "  Instalando paquete en modo editable (-e .)..."
"$PIP_CMD" install -e "$ROOT_DIR" --quiet
echo "  [OK] Paquete principal y dependencias instaladas."

# 4. Crear ejecutable en ~/.local/bin si es accesible
echo "[4/5] Configurando acceso al comando video-intake en PATH..."
LOCAL_BIN="$HOME/.local/bin"
mkdir -p "$LOCAL_BIN"

if [[ -f "$ROOT_DIR/venv/bin/video-intake" ]]; then
    ln -sf "$ROOT_DIR/venv/bin/video-intake" "$LOCAL_BIN/video-intake"
    echo "  [OK] Enlazado: $LOCAL_BIN/video-intake -> $ROOT_DIR/venv/bin/video-intake"
fi

# 5. Integración con plataformas compatibles con SKILL.md
echo "[5/5] Configurando integraciones de Skill multi-entorno..."

install_skill_to() {
    local target_dir="$1"
    local name="$2"
    mkdir -p "$target_dir"
    # Enlazar SKILL.md canónico
    ln -sf "$ROOT_DIR/SKILL.md" "$target_dir/SKILL.md"
    echo "  [OK] $name: Skill vinculada en $target_dir"
}

# Hermes Agent
if $INSTALL_HERMES || [[ -d "$HOME/.hermes" ]]; then
    install_skill_to "$HOME/.hermes/skills/video-intake" "Hermes Agent"
    if [[ -d "$ROOT_DIR/adapters/hermes" ]]; then
        mkdir -p "$HOME/.hermes/plugins"
        ln -sfn "$ROOT_DIR/adapters/hermes" "$HOME/.hermes/plugins/video-intake"
        echo "  [OK] Hermes Plugin: Vinculado en $HOME/.hermes/plugins/video-intake"
    fi
fi

# AGY
if $INSTALL_AGY || [[ -d "$HOME/.agy" ]]; then
    install_skill_to "$HOME/.agy/skills/video-intake" "AGY"
fi

# Claude Code
if $INSTALL_CLAUDE || [[ -d "$HOME/.claude" ]]; then
    install_skill_to "$HOME/.claude/skills/video-intake" "Claude Code"
fi

# OpenCode
if $INSTALL_OPENCODE || [[ -d "$HOME/.opencode" ]]; then
    install_skill_to "$HOME/.opencode/skills/video-intake" "OpenCode"
fi

# Codex
if $INSTALL_CODEX || [[ -d "$HOME/.codex" ]]; then
    install_skill_to "$HOME/.codex/skills/video-intake" "Codex"
fi

# Cursor
if $INSTALL_CURSOR || [[ -d "$HOME/.cursor" ]]; then
    install_skill_to "$HOME/.cursor/skills/video-intake" "Cursor"
    if [[ -d "$ROOT_DIR/adapters/cursor" && -f "$ROOT_DIR/adapters/cursor/.cursorrules" ]]; then
        mkdir -p "$HOME/.cursor"
        cp "$ROOT_DIR/adapters/cursor/.cursorrules" "$HOME/.cursor/rules-video-intake" 2>/dev/null || true
        echo "  [OK] Cursor: Reglas copiadas en $HOME/.cursor/rules-video-intake"
    fi
fi

echo ""
echo "====================================================================="
echo " Instalación completada con éxito."
echo "====================================================================="
echo ""
echo "Comandos disponibles:"
echo "  video-intake --help              Ver todos los comandos"
echo "  video-intake doctor              Comprobar salud y dependencias"
echo "  video-intake interactive         Modo interactivo en 2 fases"
echo "  video-intake proposals           Generar propuestas y scaffolding"
echo "  python3 scripts/interactive.py   Modo interactivo en 2 fases"
echo ""

if ! $SKIP_DOCTOR; then
    echo "Ejecutando diagnóstico inicial (doctor)..."
    "$PYTHON_EXEC" -m video_intake_core.cli doctor || true
fi
