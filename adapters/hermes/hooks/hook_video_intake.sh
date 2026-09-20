#!/usr/bin/env bash
# =============================================================================
# hook_video_intake.sh — Hook de detección de vídeos para Hermes Agent
# =============================================================================
#
# Este hook se ejecuta antes de cada respuesta del asistente para detectar
# si el usuario ha enviado vídeos o enlaces de vídeo.
#
# Instalación: copy a $HOME/.hermes/hooks/pre-response/video-intake.sh
# Habilitar: ln -s $HOME/.hermes/hooks/pre-response/video-intake.sh \
#            $HOME/.hermes/hooks/pre-response/99-video-intake.sh
#
# =============================================================================

set -e

# =============================================================================
# Configuración
# =============================================================================

VIDEO_INTAKE_CMD="${VIDEO_INTAKE_CMD:-vitk}"
MAX_FILE_SIZE_MB="${MAX_FILE_SIZE_MB:-100}"
SUPPORTED_EXTENSIONS="mp4 mov mkv webm avi m4v"

# =============================================================================
# Detección de enlaces de vídeo en el mensaje
# =============================================================================

detect_video_urls() {
    local message="$1"

    # Detectar URLs de plataformas conocidas
    local urls=()

    # YouTube
    while IFS= read -r url; do
        [[ -n "$url" ]] && urls+=("$url")
    done < <(echo "$message" | grep -oE 'https?://(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[a-zA-Z0-9_-]+' || true)

    # Facebook
    while IFS= read -r url; do
        [[ -n "$url" ]] && urls+=("$url")
    done < <(echo "$message" | grep -oE 'https?://(www\.)?facebook\.com/share/v/[a-zA-Z0-9_]+' || true)

    # Instagram
    while IFS= read -r url; do
        [[ -n "$url" ]] && urls+=("$url")
    done < <(echo "$message" | grep -oE 'https?://(www\.)?instagram\.com/(reel|reels|p|embed)/([a-zA-Z0-9_-]+)' || true)

    # TikTok
    while IFS= read -r url; do
        [[ -n "$url" ]] && urls+=("$url")
    done < <(echo "$message" | grep -oE 'https?://(www\.)?tiktok\.com/(@[^/]+/video/[0-9]+|t/[a-zA-Z0-9]+)' || true)

    # Devolver URLs únicas
    printf '%s\n' "${urls[@]}" | sort -u
}

# =============================================================================
# Detección de archivos adjuntos de vídeo
# =============================================================================

detect_video_attachments() {
    local attachments_dir="$1"

    if [[ ! -d "$attachments_dir" ]]; then
        return
    fi

    # Buscar archivos de vídeo por extensión
    find "$attachments_dir" -type f \( \
        -iname "*.mp4" -o \
        -iname "*.mov" -o \
        -iname "*.mkv" -o \
        -iname "*.webm" -o \
        -iname "*.avi" -o \
        -iname "*.m4v" \
    \) 2>/dev/null | while read -r video_file; do
        local size_mb=$(( $(stat -c%s "$video_file" 2>/dev/null || echo 0) / 1024 / 1024 ))
        if [[ $size_mb -le $MAX_FILE_SIZE_MB ]]; then
            echo "$video_file"
        fi
    done
}

# =============================================================================
# Iniciar interacción de extracción
# =============================================================================

initiate_extraction() {
    local sources="$1"

    echo ""
    echo "══════════════════════════════════════════════════════════════"
    echo "  VIDEO INTAKE — Detección de vídeo"
    echo "══════════════════════════════════════════════════════════════"
    echo ""
    echo "He detectado ${#sources[@]} vídeo(s)."
    echo ""
    echo "¿Qué deseas extraer?"
    echo ""
    echo "  [1] Descargar vídeo localmente"
    echo "  [2] Descargar audio localmente"
    echo "  [3] Transcripción de audio con timestamps"
    echo "  [4] Extraer contexto basado en audio"
    echo "  [5] Extraer contexto visual (diagramas, flujos, interfaces)"
    echo "  [6] Todo lo anterior"
    echo "  [0] Cancelar"
    echo ""
    echo "Puedes responder: 1,3,5; todos; o configurar individualmente."
    echo "══════════════════════════════════════════════════════════════"
    echo ""
}

# =============================================================================
# Main
# =============================================================================

main() {
    local message="${1:-}"
    local attachments_dir="${2:-${ATTACHMENTS_DIR:-}}"

    if [[ -z "$message" ]]; then
        return 0
    fi

    # Detectar URLs de vídeo
    local video_urls
    video_urls=$(detect_video_urls "$message")

    # Detectar archivos adjuntos
    local video_files=""
    if [[ -n "$attachments_dir" ]]; then
        video_files=$(detect_video_attachments "$attachments_dir")
    fi

    # Si hay algo que detectar
    if [[ -n "$video_urls" ]] || [[ -n "$video_files" ]]; then
        # En un entorno real, esto iniciaría la interacción
        # Por ahora, solo notificamos la detección
        echo "🎬 Video Intake: se han detectado vídeo(s) en el mensaje." >&2
    fi
}

main "$@"
