# =============================================================================
# sample-video-thumbnail.png.md — Referencia para generar un thumbnail de ejemplo
# =============================================================================
#
# Este documento describe cómo generar un thumbnail (miniatura) de ejemplo
# para uso en documentación y demostraciones del proyecto.
#
# =============================================================================

# Generación de thumbnails

# Para generar un thumbnail de un vídeo existente, usar ffmpeg:

#   ffmpeg -i input.mp4 -vframes 1 -ss 00:00:01 -vf "scale=320:-1" output/thumbnail.png

# Parámetros:
#   -i input.mp4         — Archivo de vídeo de entrada
#   -vframes 1           — Solo 1 frame
#   -ss 00:00:01         — Tiempo de extracción (1 segundo)
#   -vf "scale=320:-1"   — Escalar a 320px de ancho, mantener proporción
#   output/thumbnail.png — Ruta de salida

# Thumbnails múltiples (uno por cada 10 segundos):

#   ffmpeg -i input.mp4 -vf "fps=1/10,scale=320:-1" output/thumb_%03d.png

# Esto genera un thumbnail cada 10 segundos del vídeo.

# =============================================================================

# Para documentación y demos del proyecto, se pueden usar thumbnails de
# vídeos de ejemplo disponibles en tests/fixtures/video/ o de vídeos
# de dominio público como los de YouTube (ej. "Big Buck Bunny").

# =============================================================================
