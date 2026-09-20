# =============================================================================
# references/architecture.md — Referencias de arquitectura interna
# =============================================================================
#
# Este documento describe la arquitectura interna del paquete
# video_intake_core para desarrolladores y contribuyentes.
#
# =============================================================================

# =============================================================================
# Estructura del paquete
# =============================================================================

# video_intake_core/
# ├── __init__.py           # Versión, exportación de APIs públicas
# ├── acquisition/          # Detección y resolución de fuentes de vídeo
# ├── audio/                # Extracción de audio de vídeos
# ├── inspection/           # Inspección de metadatos de vídeo
# ├── transcription/        # Estrategias de transcripción
# ├── visual/               # Detección de escenas y extracción de keyframes
# ├── ocr/                  # OCR de frames con Tesseract
# ├── context/              # Generación de contexto (audio, visual, knowledge)
# ├── artifacts/            # Gestión de artefactos generados
# ├── jobs/                 # Gestión del ciclo de vida de trabajos
# ├── storage/              # Almacenamiento de archivos con dedup
# ├── security/             # Validación de URL, SSRF, MIME, sanitización
# ├── utils/                # Utilidades generales
# ├── schemas/              # JSON Schemas versionados
# ├── policies/             # Resolución de políticas desde YAML
# ├── memory/               # Interfaz + implementación local de memoria
# └── cli/                  # Interfaz de línea de comandos

# =============================================================================
# Flujo de datos
# =============================================================================

# 1. DETECCIÓN (acquisition)
#    Entrada: texto del usuario o mensaje del sistema
#    Salida: lista de VideoSource detectados (URLs o paths locales)
#
# 2. INSPEKCIÓN (inspection)
#    Entrada: VideoSource
#    Salida: VideoInfo (metadatos: título, duración, resolución, etc.)
#
# 3. DESCARGA/EXTRACCIÓN (acquisition + storage)
#    Entrada: VideoSource
#    Salida: archivo local en storage, metadatos del artefacto
#
# 4. AUDIO (audio)
#    Entrada: archivo de vídeo local
#    Salida: archivo de audio extraído (wav/mp3/m4a/etc.)
#
# 5. TRANSCRIPCIÓN (transcription)
#    Entrada: archivo de vídeo o audio
#    Salida: TranscriptionResult (texto + timestamps)
#
# 6. CONTEXTO DE AUDIO (context.audio_context)
#    Entrada: TranscriptionResult
#    Salida: AudioContext (resumen, timeline, temas, entidades, citas)
#
# 7. CONTEXTO VISUAL (context.visual_context + visual + ocr)
#    Entrada: archivo de vídeo local
#    Salida: VisualContext (escenas, keyframes, OCR, descripciones)
#
# 8. EXTRACCIÓN DE CONOCIMIENTO (context.knowledge_extraction)
#    Entrada: AudioContext + VisualContext
#    Salida: KnowledgeExtraction (síntesis de todo el contenido)
#
# 9. ALMACENAMIENTO DE ARTEFACTOS (artifacts + storage)
#    Entrada: todos los artefactos generados
#    Salida: artefactos persistidos en storage
#
# 10. MEMORIA (memory)
#     Entrada: KnowledgeExtraction
#     Salida: entry almacenada en memory provider

# =============================================================================
# Diseño de módulos
# =============================================================================

# CADA MÓDULO TIENE:
# - __init__.py con la API pública documentada
# - Funciones puras donde sea posible (fáciles de testear)
# - Manejo explícito de errores (no propagar excepciones silenciosamente)
# - Documentación en docstrings (Google style)

# PRINCIPIOS:
# - Inyección de dependencias: los módulos no crean sus propias deps
#   globales; reciben lo que necesitan como argumentos.
# - Separación de concerns: cada módulo hace una cosa y la hace bien.
# - TypeScript-style type hints: funciones tipadas con tipos explícitos.
# - E/S determinista cuando sea posible: mesma entrada → misma salida.

# =============================================================================
# Persistencia
# =============================================================================

# JOBS (jobs/)
# - SQLite para trabajos activos y completados
# - Cada trabajo tiene un ID único, estado, progreso, fases
# - Persistencia de resultados para reanudación

# STORAGE (storage/)
# - Estructura de directorios: <root>/jobs/<job_id>/<tipo>/<archivo>
# - SHA-256 para deduplicación de archivos
# - Metadatos en JSON junto a cada archivo

# MEMORY (memory/)
# - SQLite para entradas de conocimiento extraído
# - Schema normalizado: entries, metadata, tags, relaciones
# - Búsqueda por texto completo y por tags

# =============================================================================
# Extensibilidad
# =============================================================================

# FUENTES DE VÍDEO:
# - Agregar una nueva fuente en acquisition/detectors/
# - Implementar la detección de URL y resolución de metadatos
# - Registrar en el mapa de detectores

# ESTRATEGIAS DE TRANSCRIPCIÓN:
# - Agregar una nueva estrategia en transcription/strategies/
# - Implementar la interfaz base TranscriptionStrategy
# - Registrar en el mapa de estrategias

# MODELOS DE IA:
# - Los modelos se gestionan mediante el sistema de políticas
# - configurables en el YAML: modelo, idioma, tamaño
# - el módulo de transcripción carga el modelo indicado

# PROVEEDORES DE MEMORIA:
# - Agregar un nuevo proveedor implementando MemoryProvider
# - Registrar en el factory de memoria
# - Configurable en el YAML

# HOOKS:
# - Sistema de hooks en cada etapa del procesamiento
# - Plugables vía configuración YAML
# - Scripts ejecutables o funciones Python registrables

# =============================================================================
# Seguridad
# =============================================================================

# - Toda URL externa pasa por validación SSRF antes de descargar
# - Archivos descargados se verifican con MIME detection
# - Contenido de transcripción y OCR se sanitiza contra inyección
# - Nombres de archivo se sanitizan para prevenir path traversal
# - Datos sensibles en texto se redactan automáticamente
# - Límites de tamaño y tiempo previenen DoS accidentales

# =============================================================================
# Testing
# =============================================================================

# - Contract tests: verifican que las APIs públicas cumplen el contrato
# - Unit tests: prueban funciones individuales con mocks
# - Integration tests: verifican el flujo completo con datos reales o
#   datos de prueba generados
# - Security tests: prueban protecciones de seguridad
# - E2E tests: verifican el CLI y flujos completos

# Los tests usan pytest y se ejecutan con `make test` o `make test-all`.
