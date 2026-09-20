[[artifact]]
# Ejemplo avanzado: batch processing de múltiples vídeos con modos de uso
# =============================================================================

# Este ejemplo demuestra cómo usar video-intake-knowledge para procesar
# múltiples vídeos (YouTube + local) en modo batch con diferentes configuraciones.

# =============================================================================

# =============================================================================
# file: batch-mixed.sh
# =============================================================================
#!/usr/bin/env bash
# =============================================================================
# Batch processing mixto: YouTube + vídeos locales
# =============================================================================

set -e

VIDEO_INTKE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# =============================================================================
# Configuración
# =============================================================================

# Directorio de salida para los artefactos
OUTPUT_DIR="$VIDEO_INTKE_DIR/../output/batch-example"
mkdir -p "$OUTPUT_DIR"

# =============================================================================
# Vídeos a procesar
# =============================================================================

YOUTUBE_1="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
YOUTUBE_2="https://www.youtube.com/watch?v=jNQXAC9IVRw"
LOCAL_VIDEO="$VIDEO_INTKE_DIR/../fixtures/video/sample.mp4"

# =============================================================================
# Procesar vídeos de YouTube (modo 6 = todo)
# =============================================================================

echo "============================================================"
echo "Procesando vídeos de YouTube"
echo "============================================================"

for url in "$YOUTUBE_1" "$YOUTUBE_2"; do
    echo ""
    echo "--- Procesando: $url ---"

    vitk extract "$url" --operations 6 \
        --output-dir "$OUTPUT_DIR/youtube" \
        --config "$VIDEO_INTKE_DIR/../config/default.yaml"

    echo "✓ Completado: $url"
done

# =============================================================================
# Procesar vídeo local (modo 6 = todo)
# =============================================================================

if [ -f "$LOCAL_VIDEO" ]; then
    echo ""
    echo "============================================================"
    echo "Procesando vídeo local"
    echo "============================================================"

    vitk extract "$LOCAL_VIDEO" --operations 6 \
        --output-dir "$OUTPUT_DIR/local" \
        --config "$VIDEO_INTKE_DIR/../config/default.yaml"

    echo "✓ Completado: $LOCAL_VIDEO"
else
    echo "⚠ No se encontró vídeo de prueba local: $LOCAL_VIDEO"
    echo "  Para ejecutar este ejemplo, coloca un vídeo de prueba en:"
    echo "  $LOCAL_VIDEO"
fi

# =============================================================================
# Generar resumen del batch
# =============================================================================

echo ""
echo "============================================================"
echo "Resumen del batch"
echo "============================================================"

echo ""
echo "Artifacts generados:"
find "$OUTPUT_DIR" -type f | while read -r artifact; do
    echo "  $artifact ($(du -h "$artifact" | cut -f1))"
done

echo ""
echo "✓ Batch processing completado"
echo "  Output directory: $OUTPUT_DIR"

# =============================================================================
# EOF
# =============================================================================
