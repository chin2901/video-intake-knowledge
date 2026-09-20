# =============================================================================
# SKILL.md — Skill genérico compatible con cualquier entorno de agentes
# =============================================================================
#
# Este skill es la versión más portable de video-intake-knowledge.
# Funciona en cualquier entorno que soporte skills/SKILL.md.
#
# =============================================================================

# =============================================================================
# Video Intake Knowledge — Skill portable
# =============================================================================

# Detecta, descarga, transcribe y extrae conocimiento de vídeos de
# YouTube, Facebook, Instagram, TikTok y archivos locales.
#
# Prioridad: Hermes Agent, pero compatible con cualquier entorno que
# soporte SKILL.md.

# =============================================================================
# Instalación
# =============================================================================

# Opción 1 — Instalación global (recomendada):
#   pip install video-intake-knowledge
#   o: uv pip install video-intake-knowledge
#
# Opción 2 — Instalación local desde el repositorio:
#   git clone https://github.com/aibos/video-intake-knowledge.git
#   cd video-intake-knowledge
#   pip install -e .
#
# Opción 3 — Uso desde el directorio del proyecto:
#   export PYTHONPATH="$(pwd)/packages:$PYTHONPATH"
#   python3 -m video_intake_core.cli extract <url>

# =============================================================================
# Requisitos del sistema
# =============================================================================

# - Python 3.9+
# - ffmpeg (para extracción de audio y manipulación de vídeo)
# - tesseract (para OCR de frames)
# - yt-dlp (para descarga de vídeos de plataformas)
#
# Instalación de deps del sistema:
#   bash scripts/install-system-deps.sh

# =============================================================================
# Comandos disponibles
# =============================================================================

# vitk doctor              — Diagnóstico del entorno
# vitk inspect <url|file> — Inspección de metadatos de vídeo
# vitk extract <url|file> — Extracción interactiva de vídeo
# vitk batch <archivo>    — Procesamiento por lotes
# vitk status             — Estado de trabajos en ejecución
# vitk cancel <job_id>    — Cancelar un trabajo
# vitk artifacts          — Listing de artefactos generados
# vitk export <job_id>    — Exportar resultados
# vitk cleanup            — Limpiar artefactos antiguos
# vitk knowledge          — Gestión de conocimiento extraído
# vitk config validate    — Validar configuración
# vitk self-test          — Auto-prueba del sistema
# vitk models list        — Listar modelos disponibles
# vitk models install     — Instalar modelo de transcripción
# vitk models verify      — Verificar modelo instalado

# =============================================================================
# Uso básico
# =============================================================================

# 1. Detectar vídeos en una conversación:
#    El sistema detecta automáticamente URLs de YouTube, Facebook,
#    Instagram, TikTok y archivos locales de vídeo.
#
# 2. Extraer de un vídeo:
#    vitk extract https://www.youtube.com/watch?v=dQw4w9WgXcQ
#
#    El sistema iniciará un menú interactivo preguntando qué desea
#    extraer: [1] descargar vídeo, [2] descargar audio, [3] transcribir,
#    [4] contexto de audio, [5] contexto visual, [6] todo, [0] cancelar.
#
# 3. Selección de operaciones:
#    Puede responder: 1,3,5 / 1 3 5 / todo / todos / 6 / cancelar / 0
#
# 4. Modo batch (múltiples vídeos):
#    vitk batch urls.txt
#
#    El archivo urls.txt debe contener una URL por línea.
#    El sistema preguntará si aplicar la misma selección a todos
#    o configurar cada vídeo individualmente.

# =============================================================================
# Salida y resultados
# =============================================================================

# Los resultados se almacenan en:
#   - data/jobs/<job_id>/  — Trabajo específico
#   - data/artifacts/      — Artefactos persistentes (con dedupe)
#
# Formatos de exportación disponibles:
#   - markdown  — Documento markdown legible
#   - json      — Datos estructurados para consumo por IA
#   - mdx       — Markdown extendido con frontmatter y componentes
#
# Ejemplo de exportación:
#   vitk export <job_id> --format mdx --output resultado.mdx

# =============================================================================
# Configuración
# =============================================================================

# El sistema se configura mediante archivos YAML en config/:
#   - default.yaml    — Configuración por defecto
#   - offline.yaml    — Solo procesamiento local (sin descargas)
#   - low-cost.yaml   — Mínimo consumo de recursos
#   - production.yaml — Políticas estrictas para producción
#
# Para usar una configuración específica:
#   vitk extract <url> --config config/low-cost.yaml
#
# Variables de entorno también son respectadas:
#   VIDEO_INTAKE_CONFIG=/ruta/a/config.yaml
#   VIDEO_INTAKE_STORAGE_DIR=/ruta/a/storage
#   VIDEO_INTAKE_LOG_LEVEL=debug|info|warning|error

# =============================================================================
# Integración con memoria
# =============================================================================

# El sistema puede almacenar conocimiento extraído en una memoria
# persistente para consulta futura:
#   vitk knowledge store <job_id>
#   vitk knowledge search "término de búsqueda"
#   vitk knowledge list
#
# La memoria se almacena en SQLite local por defecto.
# Para usar la memoria nativa del host (si está disponible):
#   Establecer memory.provider: "host_native" en la configuración.

# =============================================================================
# Seguridad
# =============================================================================

# - SSRF protection: bloquea accesos a redes privadas y cloud metadata
# - MIME verification: verifica tipo de archivo descargado
# - Prompt injection protection: sanitiza contenido extraído
# - Sensitive data redaction: redacta tarjetas, emails, teléfonos, IPs
# - Filename sanitization: previene path traversal attacks
#
# Ver docs/security-model.md para detalles completos.

# =============================================================================
# Troubleshooting
# =============================================================================

# Problemas comunes y soluciones:
#   - "comando vitk no encontrado": Verify instalación con vitk doctor
#   - "ffmpeg no encontrado": Instalar ffmpeg (apt install ffmpeg)
#   - "tesseract no encontrado": Instalar tesseract (apt install tesseract-ocr)
#   - "modelo Whisper no encontrado": vitk models install tiny
#   - "URL no funciona": Verificar que la URL es válida y accesible
#   - "OCR no detecta texto": Ajustar preprocess y languages en config
#
# Ver docs/troubleshooting.md para más detalles.

# =============================================================================
# Extensibilidad
# =============================================================================

# Agregar una nueva fuente de vídeo:
#   1. Crear detector en packages/video_intake_core/acquisition/detectors/
#   2. Registrar en el mapa de detectores
#   3. Implementar detección de URL y resolución de metadata
#
# Agregar una nueva estrategia de transcripción:
#   1. Crear estrategia en packages/video_intake_core/transcription/strategies/
#   2. Implementar la interfaz TranscriptionStrategy
#   3. Registrar en el mapa de estrategias
#
# Agregar un nuevo proveedor de memoria:
#   1. Implementar MemoryProvider en packages/video_intake_core/memory/
#   2. Registrar en el factory de memoria
#   3. Configurar en el YAML: memory.provider: "nombre_del_provider"

# =============================================================================
# Licencia
# =============================================================================

# Apache License 2.0 — ver LICENSE para detalles completos.
