#!/bin/bash
# =============================================================================
# doctor.sh — Diagnóstico de salud del entorno
# =============================================================================
#
# Verifica que todas las dependencias y herramientas necesarias
# estén disponibles y correctamente configuradas.
#
# Uso:
#   ./scripts/doctor.sh [--verbose] [--json]
#
# Salidas:
#   --verbose  Muestra detalle de cada checks
#   --json     Salida en formato JSON para integración automática
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

VERBOSE=false
JSON_OUTPUT=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --verbose) VERBOSE=true; shift ;;
        --json)    JSON_OUTPUT=true; shift ;;
        --help|-h) echo "Usage: $0 [--verbose] [--json]"; exit 0 ;;
        *)         echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

# ------------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------------

check_pass() {
    if $JSON_OUTPUT; then
        echo "{\"check\": \"$1\", \"status\": \"pass\", \"detail\": \"$2\"},"
    elif $VERBOSE; then
        echo "  ✓ $1: $2"
    else
        echo "  ✓ $1"
    fi
}

check_fail() {
    if $JSON_OUTPUT; then
        echo "{\"check\": \"$1\", \"status\": \"fail\", \"detail\": \"$2\"},"
    else
        echo "  ✗ $1: $2" >&2
    fi
    FAILURES=$((FAILURES + 1))
}

check_warn() {
    if $JSON_OUTPUT; then
        echo "{\"check\": \"$1\", \"status\": \"warn\", \"detail\": \"$2\"},"
    elif $VERBOSE; then
        echo "  ⚠ $1: $2"
    else
        echo "  ⚠ $1"
    fi
    WARNINGS=$((WARNINGS + 1))
}

check_skip() {
    if $JSON_OUTPUT; then
        echo "{\"check\": \"$1\", \"status\": \"skip\", \"detail\": \"$2\"},"
    fi
}

# ------------------------------------------------------------------
# Initialisation
# ------------------------------------------------------------------

FAILURES=0
WARNINGS=0

echo "=== video-intake-knowledge — Health Check ==="
echo ""

# ------------------------------------------------------------------
# 1. Python
# ------------------------------------------------------------------
echo "--- Python Environment ---"

if command -v python3 &>/dev/null; then
    PY_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    check_pass "python3" "$PY_VERSION"
else
    check_fail "python3" "No encontrado"
fi

if command -v uv &>/dev/null; then
    UV_VERSION=$(uv --version 2>/dev/null || echo "desconocida")
    check_pass "uv" "$UV_VERSION"
else
    check_warn "uv" "No encontrado (opcional)"
fi

# Comprobar si el paquete está instalado
if python3 -c "import video_intake_core" 2>/dev/null; then
    check_pass "video_intake_core" "Instalado"
else
    check_warn "video_intake_core" "No instalado (ejecuta bootstrap.sh)"
fi

echo ""

# ------------------------------------------------------------------
# 2. Dependencias de sistema
# ------------------------------------------------------------------
echo "--- System Dependencies ---"

if command -v ffmpeg &>/dev/null; then
    FF_VERSION=$(ffmpeg -version 2>&1 | head -1 | awk -F' ' '{print $3}')
    check_pass "ffmpeg" "$FF_VERSION"
else
    check_fail "ffmpeg" "No encontrado (requerido)"
fi

if command -v ffprobe &>/dev/null; then
    FP_VERSION=$(ffprobe -version 2>&1 | head -1 | awk -F' ' '{print $3}')
    check_pass "ffprobe" "$FP_VERSION"
else
    check_warn "ffprobe" "No encontrado (incluido con ffmpeg)"
fi

if command -v tesseract &>/dev/null; then
    TSC_VERSION=$(tesseract --version 2>&1 | head -1)
    check_pass "tesseract" "$(echo "$TSC_VERSION" | awk '{print $3}')"
else
    check_fail "tesseract" "No encontrado (requerido para OCR)"
fi

if command -v yt-dlp &>/dev/null; then
    YTDL_VERSION=$(yt-dlp --version 2>/dev/null || echo "desconocida")
    check_pass "yt-dlp" "$YTDL_VERSION"
else
    check_warn "yt-dlp" "No encontrado (necesario para YouTube/Facebook)"
fi

echo ""

# ------------------------------------------------------------------
# 3. Python packages
# ------------------------------------------------------------------
echo "--- Python Packages ---"

python3 << 'PYEOF' 2>/dev/null || true
import importlib
import sys

packages = [
    ("yt_dlp", "yt-dlp"),
    ("whisper", "openai-whisper"),
    ("cv2", "opencv-python"),
    ("PIL", "Pillow"),
    ("pytesseract", "pytesseract"),
    ("py_scene_detect", "py_scene_detect"),
    ("numpy", "numpy"),
    ("PyYAML", "PyYAML"),
    ("jsonschema", "jsonschema"),
    ("rich", "rich"),
    ("questionary", "questionary"),
    ("click", "click"),
    ("pathlib", "pathlib (stdlib)"),
]

for mod_name, pkg_name in packages:
    try:
        importlib.import_module(mod_name)
        print(f"  ✓ {pkg_name}")
    except ImportError:
        print(f"  ✗ {pkg_name}")
PYEOF

echo ""

# ------------------------------------------------------------------
# 4. Estructura del proyecto
# ------------------------------------------------------------------
echo "--- Project Structure ---"

REQUIRED_DIRS=(
    "packages/video_intake_core/acquisition"
    "packages/video_intake_core/audio"
    "packages/video_intake_core/context"
    "packages/video_intake_core/inspection"
    "packages/video_intake_core/jobs"
    "packages/video_intake_core/policies"
    "packages/video_intake_core/schemas"
    "packages/video_intake_core/security"
    "packages/video_intake_core/storage"
    "packages/video_intake_core/utils"
    "scripts"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [[ -d "$ROOT_DIR/$dir" ]]; then
        check_pass "dir:$dir" "Existe"
    else
        check_fail "dir:$dir" "Falta"
    fi
done

REQUIRED_FILES=(
    "pyproject.toml"
    "README.md"
    "LICENSE"
    "SECURITY.md"
    "CONTRIBUTING.md"
    "scripts/bootstrap.sh"
    "scripts/doctor.sh"
    "packages/video_intake_core/__init__.py"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [[ -f "$ROOT_DIR/$file" ]]; then
        check_pass "file:$file" "Existe ($(wc -c < "$ROOT_DIR/$file") bytes)"
    else
        check_fail "file:$file" "Falta"
    fi
done

echo ""

# ------------------------------------------------------------------
# 5. Integración Hermes
# ------------------------------------------------------------------
echo "--- Hermes Integration ---"

HERMES_DIR="$HOME/.hermes"
if [[ -d "$HERMES_DIR" ]]; then
    check_pass "hermes_dir" "$HERMES_DIR"
else
    check_warn "hermes_dir" "No encontrado (la integración no es prioritaria aquí)"
fi

if [[ -d "$ROOT_DIR/adapters/hermes" ]]; then
    check_pass "hermes_adapter" "Adaptador presente"
else
    check_warn "hermes_adapter" "No presente"
fi

if [[ -f "$ROOT_DIR/adapters/hermes/plugin.yaml" ]]; then
    check_pass "hermes_plugin.yaml" "Presente"
else
    check_warn "hermes_plugin.yaml" "No presente"
fi

echo ""

# ------------------------------------------------------------------
# Resumen
# ------------------------------------------------------------------
echo "=== Resumen ==="

if $JSON_OUTPUT; then
    echo "{"
    echo "  \"status\": \"ok\","
    echo "  \"failures\": $FAILURES,"
    echo "  \"warnings\": $WARNINGS,"
    echo "  \"project_root\": \"$ROOT_DIR\""
    echo "}"
else
    if [[ $FAILURES -eq 0 ]]; then
        echo "Estado: ✓ Saludable"
        echo "Fallos: 0"
        echo "Advertencias: $WARNINGS"
    else
        echo "Estado: ✗ Con fallos"
        echo "Fallos: $FAILURES"
        echo "Advertencias: $WARNINGS"
        exit 1
    fi
fi
