# =============================================================================
# references/configuration.md — Referencias de configuración de video-intake-knowledge
# =============================================================================
#
# Este documento sirve como referencia rápida para la configuración del sistema.
# Explica cada sección del archivo YAML y sus opciones.
#
# =============================================================================

# =============================================================================
# Estructura de configuración
# =============================================================================

# La configuración se carga desde un archivo YAML. El sistema busca en
# este orden:
#   1. Variable de entorno VIDEO_INTAKE_CONFIG
#   2. ./config/default.yaml (relativo al directorio de trabajo)
#   3. ~/.video-intake-knowledge/config.yaml
#   4. Valores por defecto internos del paquete
#
# Se puede combinar con variables de entorno para personalizar sin
# modificar el archivo YAML.

# =============================================================================
# Sección: transcription
# =============================================================================

# Estrategia de transcripción:
#   - "captions": usa subtítulos originales de la plataforma (gratuito)
#   - "whisper": usa modelo Whisper local para transcribir desde audio
#   - "auto": intenta captions primero, si no hay, usa Whisper
transcription:
  strategy: "auto"           # "captions" | "whisper" | "auto"
  whisper_model: "base"      # "tiny" | "base" | "small" | "medium" | "large"
  language: "auto"           # "auto" o código ISO (ej. "es")
  include_timestamps: true   # incluir timestamps en la transcripción
  timestamp_granularity: "segment"  # "segment" | "word"

# =============================================================================
# Sección: audio_context
# =============================================================================

# Generación de contexto a partir del audio transcrito.
audio_context:
  generate: true

  summary:
    generate: true
    max_sentences: 12        # longitud máxima del resumen
    language: "es"           # idioma del resumen

  timeline:
    generate: true
    split_by_topic: true     # dividir por temas
    min_segment_duration_sec: 30  # duración mínima de un segmento

  topics:
    generate: true
    max_topics: 15           # número máximo de temas

  entities:
    generate: true
    max_entities: 50         # número máximo de entidades

  quotes:
    generate: true
    max_quotes: 10
    min_quote_length: 20     # longitud mínima de una cita

  confidence:
    generate: true
    include_for: ["summary", "topics", "entities"]

  language: "es"

# =============================================================================
# Sección: visual_context
# =============================================================================

visual_context:
  generate: true

  scene_detection:
    generate: true
    method: "content"        # "content" (PySceneDetect) | "frame" (muestreo)
    threshold: 30            # umbral de detección (0-100)

  keyframes:
    generate: true
    max_per_scene: 3         # keyframes por escena
    format: "png"            # formato de imagen

  frame_analysis:
    generate: true
    ocr:
      enable: true
      min_confidence: 60    # confianza mínima por palabra
      preprocess: true       # preprocesado de imagen
      languages: ["spa"]    # idiomas de Tesseract

    visual_descriptions:
      enable: true
      extract_diagram: true
      extract_screenshots: true
      extract_flowcharts: true

  language: "es"

# =============================================================================
# Sección: storage
# =============================================================================

storage:
  max_storage_gb: 50         # límite de espacio en disco (GB)
  retention_days: 30         # retener artefactos completados por N días
  auto_cleanup: "monthly"    # "daily" | "weekly" | "monthly" | "never"
  deduplication: true        # deduplicar por SHA-256
  compress_video: false      # comprimir vídeos en artefactos

# =============================================================================
# Sección: memory
# =============================================================================

memory:
  enabled: true
  provider: "local"          # "local" | "host_native" | "none"
  default_tags:
    - "video-intake-knowledge"
    - "auto-extracted"
  dedupe_by_video: true      # deduper por URL/ID de vídeo
  retention_days: 0          # 0 = permanente

# =============================================================================
# Sección: security
# =============================================================================

security:
  ssrf_protection: true      # protección contra SSRF
  blocked_hosts: []          # hosts adicionales bloqueados
  verify_mime: true          # verificar MIME de archivos descargados
  sanitize_filenames: true   # sanitizar nombres de archivo
  redact_sensitive_data: true  # redactar datos sensibles
  prompt_injection_protection: true  # protección contra inyección
  max_download_size_mb: 500
  max_audio_size_mb: 100
  network_timeout_secs: 60
  ffmpeg_timeout_secs: 300
  whisper_timeout_secs: 1800

# =============================================================================
# Sección: batch
# =============================================================================

batch:
  max_concurrent: 1          # número máximo de trabajos concurrentes
  auto_enable: false         # habilitar batch automáticamente
  auto_select_operations: true  # seleccionar operaciones automáticamente

# =============================================================================
# Sección: build_proposals
# =============================================================================

build_proposals:
  generate_auto: false       # generar propuestas automáticamente
  output_formats:
    - "markdown"
    - "mdx"
  max_proposals: 5

# =============================================================================
# Sección: platform
# =============================================================================

platform:
  ffmpeg_path: "ffmpeg"
  ffprobe_path: "ffprobe"
  yt_dlp_path: "yt-dlp"
  tesseract_path: "tesseract"
  tesseract_default_lang: "spa"
  whisper_model_dir: null    # null = usar default de la librería
  captions_cache_dir: null   # null = usar default

# =============================================================================
# Sección: hooks
# =============================================================================

hooks:
  on_detection: []           # hooks cuando se detectan vídeos
  on_download_complete: []   # hooks tras descarga
  on_transcription_complete: []  # hooks tras transcripción
  on_extraction_complete: []      # hooks tras extracción completa
  on_error: []              # hooks tras error

# =============================================================================
# Sección: logging
# =============================================================================

logging:
  level: "info"              # "debug" | "info" | "warning" | "error"
  retention_days: 7
  audit_trail: true          # trail de auditoría de extracciones

# =============================================================================
# Sección: development (solo desarrollo)
# =============================================================================

development:
  strict_checks: false       # checks extra de integridad
  keep_intermediates: false  # conservar outputs intermedios
  verbose_network: false     # logs detallados de red
