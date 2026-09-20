# =============================================================================
# local-video/README.md — Ejemplo de extracción de vídeo local
# =============================================================================
#
# Este ejemplo demuestra cómo usar video-intake-knowledge para extraer
# conocimiento de un archivo de vídeo local.
#
# =============================================================================

# Vídeo de ejemplo local

# Para este ejemplo, se usa un archivo de vídeo local MPP4 de prueba.
# El archivo debe estar en el directorio del ejemplo o en una ruta
# accesible especificada en la línea de comandos.

# =============================================================================
# Archivo de prueba
# =============================================================================

# Puedes usar cualquier vídeo local. Para pruebas, el directorio
# tests/fixtures/video/ contiene archivos de ejemplo.
#
# Si no hay archivos de prueba, el script doctor.sh puede generar
# un vídeo de prueba con ffmpeg:

#   bash scripts/doctor.sh --generate-sample

# =============================================================================
# Flujo de extracción
# =============================================================================

# 1. Extraer todo el conocimiento de un vídeo local:

#   vitk extract ./mi-video.mp4

#   El sistema iniciará el menú interactivo. Selecciona "6" (todo)
#   para extraer vídeo, audio, transcripción, contexto de audio y
#   contexto visual.

# 2. Especificar operaciones directamente (sin menú interactivo):

#   vitk extract ./mi-video.mp4 --operations 6

#   Esto ejecuta todas las operaciones sin preguntar.

# 3. Usar una configuración específica:

#   vitk extract ./mi-video.mp4 --config config/low-cost.yaml

# =============================================================================
# Comandos de ejemplo
# =============================================================================

# Extraer vídeo y transcripción:
#   vitk extract ./mi-video.mp4 --operations "1,3"

# Extraer contexto de audio:
#   vitk extract ./mi-video.mp4 --operations "1,3,4"

# Extraer contexto visual (OCR, keyframes, diagrams):
#   vitk extract ./mi-video.mp4 --operations "5"

# Todo (vídeo + audio + transcripción + contexto completo):
#   vitk extract ./mi-video.mp4 --operations "6"

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
# Archivos de prueba en el proyecto
# =============================================================================

# El proyecto incluye archivos de prueba en:
#   tests/fixtures/video/   — Archivos de vídeo de prueba
#   tests/fixtures/audio/   — Archivos de audio de prueba
#   tests/fixtures/subtitles/ — Archivos de subtítulos de prueba

# Para usar estos archivos en los ejemplos:

#   vitk extract tests/fixtures/video/sample.mp4 --operations 6

# =============================================================================
# Configuración
# =============================================================================

# Para pruebas locales, se puede usar la configuración por defecto o
# una configuración específica. Las opciones relevantes para vídeos
# locales son:

#   - storage.root_dir: directorio donde se guardan los artefactos
#   - limits.max_video_duration_minutes: duración máxima a procesar
#   - limits.max_download_size_mb: tamaño máximo (para archivos locales,
#     esto se aplica al archivo de vídeo)
#   - transcription.model: modelo Whisper a usar
#   - visual.ocr_engine: motor OCR (tesseract)

# Ver config/default.yaml para la configuración completa.
