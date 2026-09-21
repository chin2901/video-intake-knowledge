#!/usr/bin/env bash
# =============================================================================
# bootstrap.sh — Instalación completa de video-intake-knowledge
# =============================================================================
#
# Instala el paquete y todas las dependencias en el entorno actual.
# Uso:
#   chmod +x scripts/bootstrap.sh
#   ./scripts/bootstrap.sh [--system-deps] [--dev] [--quiet]
#
# Opciones:
#   --system-deps  Instala también dependencias del sistema (ffmpeg, tesseract)
#   --dev         Instala también dependencias de desarrollo (pytest, etc.)
#   --quiet       Silencia salida no esencial
#
# Requiere: bash 4+, python3.10+, pip o uv
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_NAME="video-intake-knowledge"
PACKAGE_NAME="video_intake_core"

SYSTEM_DEPS=false
DEV=false
QUIET=false

usage() {
    echo "Usage: $0 [--system-deps] [--dev] [--quiet]"
    echo ""
    echo "Instala video-intake-knowledge y sus dependencias."
    echo ""
    echo "Opciones:"
    echo "  --system-deps  Instala dependencias del sistema (ffmpeg, tesseract)"
    echo "  --dev          Incluye dependencias de desarrollo"
    echo "  --quiet        Output mínimo"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --system-deps) SYSTEM_DEPS=true; shift ;;
        --dev)         DEV=true; shift ;;
        --quiet)       QUIET=true; shift ;;
        --help|-h)     usage ;;
        *)             echo "Opción desconocida: $1" >&2; usage ;;
    esac
done

log() {
    if ! $QUIET; then
        echo "[bootstrap] $*"
    fi
}

error() {
    echo "[bootstrap] ERROR: $*" >&2
    exit 1
}

# ------------------------------------------------------------------
# Detectar entorno Python
# ------------------------------------------------------------------
detect_python() {
    if command -v uv &>/dev/null; then
        PYTHON_CMD="uv run python"
    elif command -v python3 &>/dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &>/dev/null; then
        PYTHON_CMD="python"
    else
        error "Python no encontrado. Instala python3.10+."
    fi
    log "Python: $PYTHON_CMD"
}

# ------------------------------------------------------------------
# Verificar / instalar dependencias del sistema
# ------------------------------------------------------------------
install_system_deps() {
    log "Instalando dependencias del sistema..."

    if [[ "$(uname -s)" == "Linux" ]]; then
        if command -v apt-get &>/dev/null; then
            sudo apt-get update -qq
            sudo apt-get install -y -qq ffmpeg tesseract-ocr libtesseract-dev \
                pkg-config libavcodec-extra \
                2>/dev/null || sudo apt-get install -y ffmpeg tesseract-ocr \
                libtesseract-dev pkg-config 2>/dev/null || true
        elif command -v dnf &>/dev/null; then
            sudo dnf install -y ffmpeg tesseract tesseract-langpack-spa
        elif command -v pacman &>/dev/null; then
            sudo pacman -S --noconfirm ffmpeg tesseract tesseract-data-spa
        fi
    elif [[ "$(uname -s)" == "Darwin" ]]; then
        if command -v brew &>/dev/null; then
            brew install ffmpeg tesseract
        fi
    elif [[ "$(uname -s)" == "Windows"* ]]; then
        log "Windows detectado: instala ffmpeg y tesseract manualmente"
        log "  ffmpeg:  https://ffmpeg.org/download.html"
        log "  tesseract: https://github.com/UB-Mannheim/tesseract/wiki"
    fi

    log "Dependencias del sistema OK"
}

# ------------------------------------------------------------------
# Crear entorno virtual si no existe
# ------------------------------------------------------------------
setup_virtualenv() {
    log "Configurando entorno virtual..."

    if [[ -d "$ROOT_DIR/.venv" ]]; then
        log "Entorno virtual ya existe: .venv/"
    else
        $PYTHON_CMD -m venv "$ROOT_DIR/.venv" 2>/dev/null || \
            python3 -m venv "$ROOT_DIR/.venv" 2>/dev/null || \
            error "No se pudo crear el entorno virtual"

        # Activar y actualizar pip
        source "$ROOT_DIR/.venv/bin/activate"
        pip install --upgrade pip setuptools wheel >/dev/null 2>&1 || true
        deactivate
    fi

    log "Entorno virtual listo"
}

# ------------------------------------------------------------------
# Instalar el paquete
# ------------------------------------------------------------------
install_package() {
    log "Instalando $PROJECT_NAME..."

    source "$ROOT_DIR/.venv/bin/activate"

    if $DEV; then
        pip install -e ".[dev]" 2>&1 | grep -v "already satisfied" || true
    else
        pip install -e "." 2>&1 | grep -v "already satisfied" || true
    fi

    deactivate
    log "Paquete instalado"
}

# ------------------------------------------------------------------
# Verificar instalación
# ------------------------------------------------------------------
verify_install() {
    log "Verificando instalación..."

    source "$ROOT_DIR/.venv/bin/activate"

    $PYTHON_CMD -c "
import video_intake_core
from video_intake_core.acquisition import detect_video_sources
from video_intake_core.inspection import inspect_video
from video_intake_core.audio import extract_audio
from video_intake_core.transcription import transcribe
from video_intake_core.visual import analyze_scenes
from video_intake_core.ocr import batch_ocr
from video_intake_core.context import generate_all_context
from video_intake_core.jobs import create_job, list_jobs
from video_intake_core.storage import StorageManager
from video_intake_core.policies import PolicyResolver
from video_intake_core.memory import create_memory_provider

print('video_intake_core OK')
print(f'  versión: {video_intake_core.__version__}')
print(f'  módulos: acquisition, inspection, audio, transcription,')
print(f'           visual, ocr, context, jobs, storage,')
print(f'           policies, memory, security, utils')
" 2>&1

    deactivate
    log "Verificación completada"
}

# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
main() {
    log "=== Bootstrap $PROJECT_NAME ==="
    log "Raíz: $ROOT_DIR"

    detect_python

    if $SYSTEM_DEPS; then
        install_system_deps
    fi

    setup_virtualenv
    install_package
    verify_install

    log "=== Bootstrap completado ==="
    log ""
    log "Para usar el CLI:"
    log "  source $ROOT_DIR/.venv/bin/activate"
    log "  vitk --help"
    log ""
    log "Para integración con Hermes Agent:"
    log "  Ver scripts/standalone_hermes.sh"
}

main
