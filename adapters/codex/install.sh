#!/usr/bin/env bash
# =============================================================================
# install.sh — Instalador del adaptador Codex para video-intake-knowledge
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

PREFIX="${PREFIX:-$HOME/.codex}"
TARGET_DIR="$PREFIX/skills/video-intake"

echo "====================================================================="
echo " Instalador de video-intake-knowledge para Codex"
echo "====================================================================="
echo "Destino: $TARGET_DIR"
echo ""

# 1. Verificar dependencias
echo "[1/3] Verificando dependencias del sistema..."
for cmd in ffmpeg tesseract; do
    if command -v "$cmd" &>/dev/null; then
        echo "  [OK] $cmd detectado"
    else
        echo "  [AVISO] $cmd no encontrado. Se recomienda instalarlo para funcionalidad completa."
    fi
done

# 2. Verificar comando video-intake
echo "[2/3] Verificando CLI video-intake..."
if command -v video-intake &>/dev/null; then
    echo "  [OK] Comando video-intake disponible en PATH"
else
    echo "  [AVISO] video-intake no encontrado en PATH. Ejecuta './install.sh' en la raíz del repositorio."
fi

# 3. Instalar skill en ~/.codex/skills/video-intake
echo "[3/3] Instalando skill para Codex..."
mkdir -p "$TARGET_DIR"

if [[ -f "$SCRIPT_DIR/SKILL.md" ]]; then
    ln -sf "$SCRIPT_DIR/SKILL.md" "$TARGET_DIR/SKILL.md"
else
    ln -sf "$ROOT_DIR/SKILL.md" "$TARGET_DIR/SKILL.md"
fi

echo "  [OK] Skill instalada y enlazada en $TARGET_DIR/SKILL.md"
echo ""
echo "Instalación completada con éxito."
