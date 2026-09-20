#!/bin/bash
# =============================================================================
# install-system-deps.sh — Instalación de dependencias del sistema
# =============================================================================
#
# Instala las dependencias del sistema necesarias para video-intake-knowledge:
# ffmpeg, tesseract, libra CCTV, etc.
#
# Uso:
#   chmod +x scripts/install-system-deps.sh
#   ./scripts/install-system-deps.sh [--quiet] [--dry-run]
#
# Requiere privilegios de root/administrador en la mayoría de sistemas.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

QUIET=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --quiet)   QUIET=true; shift ;;
        --dry-run) DRY_RUN=true; shift ;;
        --help|-h) echo "Usage: $0 [--quiet] [--dry-run]"; exit 0 ;;
        *)         echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

log() {
    if ! $QUIET; then
        echo "[install-deps] $*"
    fi
}

error() {
    echo "[install-deps] ERROR: $*" >&2
    exit 1
}

is_root() {
    [[ $EUID -eq 0 ]] || [[ "$(id -u)" -eq 0 ]]
}

detect_package_manager() {
    if command -v apt-get &>/dev/null; then
        echo "apt"
    elif command -v dnf &>/dev/null; then
        echo "dnf"
    elif command -v yum &>/dev/null; then
        echo "yum"
    elif command -v pacman &>/dev/null; then
        echo "pacman"
    elif command -v brew &>/dev/null; then
        echo "brew"
    else
        echo "unknown"
    fi
}

install_apt() {
    log "Usando apt (Debian/Ubuntu)..."
    if ! is_root; then
        error "Se requieren privilegios de root para apt. Usa sudo."
    fi
    apt-get update -qq
    apt-get install -y -qq ffmpeg tesseract-ocr libtesseract-dev \
        pkg-config libavcodec-extra 2>/dev/null || \
        apt-get install -y ffmpeg tesseract-ocr libtesseract-dev pkg-config
    log "apt instalado OK"
}

install_dnf() {
    log "Usando dnf (Fedora/RHEL)..."
    if ! is_root; then
        error "Se requieren privilegios de root para dnf."
    fi
    dnf install -y ffmpeg tesseract tesseract-langpack-spa
    log "dnf instalado OK"
}

install_yum() {
    log "Usando yum (CentOS/RHEL)..."
    if ! is_root; then
        error "Se requieren privilegios de root para yum."
    fi
    yum install -y ffmpeg tesseract tesseract-langpack-spa
    log "yum instalado OK"
}

install_pacman() {
    log "Usando pacman (Arch Linux)..."
    if ! is_root; then
        error "Se requieren privilegios de root para pacman."
    fi
    pacman -S --noconfirm ffmpeg tesseract tesseract-data-spa
    log "pacman instalado OK"
}

install_brew() {
    log "Usando Homebrew (macOS)..."
    brew install ffmpeg tesseract
    log "brew instalado OK"
}

install_unknown() {
    log "No se detectó gestor de paquetes conocido."
    log "Por favor instala manualmente:"
    log "  - ffmpeg: https://ffmpeg.org/download.html"
    log "  - tesseract: https://github.com/tesseract-ocr/tesseract/wiki"
    log "  - libtesseract-dev (si aplica)"
}

install_system_deps() {
    if $DRY_RUN; then
        log "Modo dry-run: no se instalará nada."
        log "Gestor detectado: $(detect_package_manager)"
        return
    fi

    PM=$(detect_package_manager)
    case "$PM" in
        apt)     install_apt ;;
        dnf)     install_dnf ;;
        yum)     install_yum ;;
        pacman)  install_pacman ;;
        brew)    install_brew ;;
        *)       install_unknown ;;
    esac
}

verify_installation() {
    log "Verificando instalación de dependencias..."

    local missing=()

    if command -v ffmpeg &>/dev/null; then
        log "  ✓ ffmpeg: $(ffmpeg -version 2>&1 | head -1 | awk '{print $3}')"
    else
        missing+=("ffmpeg")
    fi

    if command -v ffprobe &>/dev/null; then
        log "  ✓ ffprobe"
    else
        missing+=("ffprobe")
    fi

    if command -v tesseract &>/dev/null; then
        log "  ✓ tesseract: $(tesseract --version 2>&1 | head -1 | awk '{print $3}')"
    else
        missing+=("tesseract")
    fi

    if [[ ${#missing[@]} -gt 0 ]]; then
        log "Faltan: ${missing[*]}"
        return 1
    fi

    log "Todas las dependencias del sistema están instaladas."
    return 0
}

# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
main() {
    log "=== Instalación de dependencias del sistema ==="
    log "Raíz: $ROOT_DIR"

    install_system_deps

    if verify_installation; then
        log "✓ Listo"
    else
        log "✗ Algo falló. Revisa los logs."
        exit 1
    fi
}

main
