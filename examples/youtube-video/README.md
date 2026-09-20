# =============================================================================
# examples/youtube-video/README.md — Ejemplo de extracción de vídeo de YouTube
# =============================================================================
#
# Este ejemplo demuestra cómo usar video-intake-knowledge para extraer
# conocimiento de un vídeo de YouTube.
#
# =============================================================================

# Vídeo de ejemplo: "Big Buck Bunny"

# Big Buck Bunny es un corto de animación producido por la Blender
# Foundation, disponible en YouTube bajo licencia Creative Commons.
# Es un vídeo de dominio público ideal para pruebas.

# URL de ejemplo:
#   https://www.youtube.com/watch?v=YE7VzlLhI6E

# =============================================================================
# Flujo de extracción
# =============================================================================

# 1. Extraer todo el conocimiento:

#   vitk extract https://www.youtube.com/watch?v=YE7VzlLhI6E

#   El sistema iniciará el menú interactivo. Selecciona "6" (todo)
#   para extraer vídeo, audio, transcripción, contexto de audio y
#   contexto visual.

# 2. Selección de operaciones:

#   Puedes responder "1,3,5" para descargar el vídeo, transcribir y
#   extraer contexto visual, o "todo" para todas las operaciones.

# 3. Resultados:

#   Los resultados se guardan en data/jobs/<job_id>/ y están
#   disponibles para exportación en markdown, JSON o MDX.

# =============================================================================
# Comandos de ejemplo
# =============================================================================

# Extraer vídeo y transcripción solamente:
#   vitk extract https://www.youtube.com/watch?v=YE7VzlLhI6E
#   (luego selecciona "1,3" en el menú)

# Extraer contexto de audio completo:
#   vitk extract https://www.youtube.com/watch?v=YE7VzlLhI6E
#   (luego selecciona "1,3,4" en el menú)

# Extraer contexto visual (diagramas, OCR, keyframes):
#   vitk extract https://www.youtube.com/watch?v=YE7VzlLhI6E
#   (luego selecciona "5" en el menú)

# Todo en un solo paso:
#   vitk extract https://www.youtube.com/watch?v=YE7VzlH6E
#   (luego selecciona "6" o "todo" en el menú)

# =============================================================================
# Exportación de resultados
# =============================================================================

# Después de la extracción, exporta los resultados:

#   vitk export <job_id> --format markdown
#   vitk export <job_id> --format json
#   vitk export <job_id> --format mdx

# El job_id se muestra al completar la extracción o se puede
# obtener con:
#   vitk status

# =============================================================================
# Configuración para este ejemplo
# =============================================================================

# Para pruebas rápidas, se puede usar la configuración low-cost:
#   vitk extract https://www.youtube.com/watch?v=YE7VzlH6E --config config/low-cost.yaml

# Esto usa:
#   - Modelo Whisper tiny (más rápido, menos preciso)
#   - OCR básico
#   - Sin almacenamiento en memoria

# =============================================================================
