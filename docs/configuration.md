# Configuración de video-intake-knowledge

## Resumen

El sistema se configura mediante archivos YAML y variables de entorno. La
precedencia de configuración, de mayor a menor prioridad, es:

1. **Argumentos CLI** (mayor precedencia)
2. **Variables de entorno** con prefijo `VITK_`
3. **Archivo de configuración** especificado (`--config` o `VITK_CONFIG_PATH`)
4. **Archivo por defecto** (`config/default.yaml`)

## Archivos de configuración

### `config/default.yaml`

Configuración por defecto. Balanceada, para uso general.

```yaml
transcription:
  strategy_order: [platform_captions, local_captions, whisper]
  language: es
  local_engine: whisper
  model: tiny
  fallback_enabled: true
  device: cpu

visual:
  scene_detection: true
  frame_sampling: scene_based
  max_candidate_frames: 20
  ocr_engine: tesseract
  vision_fallback_enabled: false
  scene_detection_threshold: 30.0
  min_scene_length: 2.0

models:
  priority:
    transcript: "local"
    visual: "local"
    reasoning: "local"
  allow_external_providers: false
  require_explicit_approval_for_paid: true
  configured_providers: {}

security:
  strict_url_validation: true
  ssrf_protection: true
  allowed_domains: []
  scan_downloaded_files: false
  redact_sensitive_data: false
  prompt_injection_protection: true
  sanitize_filenames: true

storage:
  root_dir: ./artifacts
  artifact_retention_days: 90
  max_storage_gb: 100
  cleanup_policy: age

limits:
  max_video_duration_minutes: 600
  max_download_size_mb: 5000
  max_batch_items: 50
  max_parallel_jobs: 4
  timeout_seconds: 3600

acquisition:
  enabled_sources: [youtube, facebook, instagram, tiktok, local]
  preferred_video_quality: best
  preferred_audio_quality: best
  captions_first: true
  cache_enabled: true

memory:
  enabled: true
  default_provider: local
  require_confirmation: true
  max_context_tokens: 4000

host:
  type: generic
  session_context_strategy: compact
  auto_detect_messages: true
  auto_detect_attachments: true
```

### `config/offline.yaml`

Para uso sin conexión. No permite descargas remotas.

```yaml
acquisition:
  enabled_sources: [local]
  cache_enabled: false

transcription:
  strategy_order: [local_captions, whisper]

visual:
  scene_detection: true
  ocr_engine: tesseract

security:
  allow_remote_downloads: false
  strict_url_validation: true
  ssrf_protection: true

host:
  type: generic
  auto_detect_messages: false
```

### `config/low-cost.yaml`

Sin modelos externos. Solo Whisper tiny + Tesseract.

```yaml
transcription:
  strategy_order: [platform_captions, local_captions, whisper]
  local_engine: whisper
  model: tiny
  fallback_enabled: true
  device: cpu

visual:
  scene_detection: true
  ocr_engine: tesseract
  vision_fallback_enabled: false
  max_candidate_frames: 10

models:
  priority:
    transcript: "local"
    visual: "local"
  allow_external_providers: false

storage:
  root_dir: ./artifacts
  artifact_retention_days: 30
  max_storage_gb: 10

limits:
  max_video_duration_minutes: 120
  max_download_size_mb: 1000
```

### `config/production.yaml`

Con políticas estrictas, retención, escaneo de seguridad.

```yaml
transcription:
  strategy_order: [platform_captions, local_captions, whisper]
  language: es
  local_engine: whisper
  model: small
  fallback_enabled: true
  device: cpu

visual:
  scene_detection: true
  ocr_engine: tesseract
  vision_fallback_enabled: false

models:
  policy: strict
  allow_external_providers: false
  require_explicit_approval_for_paid: true
  configured_providers: {}

security:
  strict_url_validation: true
  ssrf_protection: true
  allowed_domains: []
  scan_downloaded_files: true
  redact_sensitive_data: true
  prompt_injection_protection: true
  sanitize_filenames: true

storage:
  root_dir: /var/lib/video-intake/artifacts
  artifact_retention_days: 90
  max_storage_gb: 500
  cleanup_policy: age

limits:
  max_video_duration_minutes: 600
  max_download_size_mb: 5000
  max_batch_items: 10
  max_parallel_jobs: 2
  timeout_seconds: 3600

acquisition:
  enabled_sources: [youtube, facebook, instagram, tiktok, local]
  preferred_video_quality: 720p
  preferred_audio_quality: best
  captions_first: true
  cache_enabled: true
  allow_authenticated_sources: false

memory:
  enabled: true
  default_provider: local
  require_confirmation: true
  max_context_tokens: 4000

host:
  type: generic
  session_context_strategy: compact
  auto_detect_messages: true
  auto_detect_attachments: true
```

## Variables de entorno

Cada opción de configuración tiene una variable de entorno con prefijo `VITK_`:

```bash
# Transcripción
export VITK_TRANSCRIPTION_LANG=es
export VITK_TRANSCRIPTION_MODEL=tiny

# Visual
export VITK_VISUAL_OCR_ENGINE=tesseract

# Seguridad
export VITK_SECURITY_STRICT_URL_VALIDATION=true

# Storage
export VITK_STORAGE_ROOT_DIR=/ruta/a/artifacts

# Límites
export VITK_LIMITS_MAX_VIDEO_DURATION_MINUTES=600
```

Las variables anulan el archivo de configuración pero no a los argumentos CLI.

## Perfiles de instalación

| Perfil | Qué instala |
|--------|-------------|
| `core` | Solo el núcleo, sin modelos opcionales. |
| `local-transcription` | Núcleo + Whisper/faster-whisper. |
| `local-ocr` | Núcleo + Tesseract + OpenCV. |
| `visual-analysis` | Núcleo + OCR + PySceneDetect + OpenCV. |
| `full` | Todo lo anterior. |
| `hermes` | Núcleo + adaptador Hermes. |
| `development` | Núcleo + herramientas de desarrollo. |

## Comandos de gestión de modelos

```bash
# Listar modelos disponibles e instalados
video-intake models list

# Instalar un modelo
video-intake models install tiny      # ~75 MB
video-intake models install base      # ~140 MB
video-intake models install small     # ~480 MB

# Verificar modelos instalados
video-intake models verify

# Eliminar un modelo
video-intake models remove tiny
```

Cada modelo indica: tamaño, licencia, idiomas, uso, requisitos de CPU/RAM/GPU,
calidad esperada, destino en disco, si puede funcionar offline.

## Migración de configuración

 Cuando se actualiza el proyecto, la configuración puede migrarse con:

```bash
video-intake config migrate --from-version 0.1.0 --to-version 0.2.0
```

Esto aplica las migraciones de esquema de artefactos versionadas y genera un
backup de la configuración anterior.
