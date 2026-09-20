# =============================================================================
# visual-diagram/README.md — Ejemplo de extracción de diagramas visuales
# =============================================================================
#
# Este ejemplo demuestra cómo usar video-intake-knowledge para extraer
# diagramas, esquemas y contenido visual de vídeos.
#
# =============================================================================

# Extracción de contenido visual

# El sistema puede extraer elementos visuales de vídeos:
#   - Diagramas y esquemas
#   - Flujos de trabajo y procesos
#   - Capturas de pantalla de interfaces
#   - Texto en pantalla (OCR)
#   - Animaciones de procesos
#   - Transiciones entre pantallas

# =============================================================================
# Flujo de extracción visual
# =============================================================================

# 1. Extraer un vídeo con operación visual:

#   vitk extract https://www.youtube.com/watch?v=dQw4w9WgXcQ --operations 5

#   Esto ejecuta solo la extracción visual: detección de escenas,
#   keyframes, OCR y análisis de contenido visual.

# 2. O extraer todo junto:

#   vitk extract https://www.youtube.com/watch?v=dQw4w9WgXcQ --operations 6

# =============================================================================
# Componentes de la extracción visual
# =============================================================================

# Detección de escenas (PySceneDetect):
#   - Divide el vídeo en escenas basándose en cambios de contenido
#   - Umbral configurable en config/default.yaml
#   - Detecta transiciones relevantes entre planos

# Keyframes:
#   - Extrae frames representativos de cada escena
#   - Máximo configurable por escena (default: 3)
#   - Formato PNG por defecto

# OCR (Tesseract):
#   - Extrae texto presente en los frames
#   - Preprocesado de imagen para mejorar precisión
#   - Idiomas configurables (por defecto: español)
#   - Confidence score por palabra detectada

# Análisis visual:
#   - Detección de diagramas y esquemas
#   - Detección de capturas de pantalla
#   - Descripción de contenido visual
#   - Extracción de flujos de trabajo

# =============================================================================
# Configuración de extracción visual
# =============================================================================

# En config/default.yaml:

#   visual:
#     scene_detection: true
#     frame_sampling: scene_based
#     max_candidate_frames: 20
#     ocr_engine: tesseract
#     scene_detection_threshold: 30.0
#     min_scene_length: 2.0

# Para extracción visual completa, se recomienda:
#   - scene_detection: true (detectar escenas)
#   - ocr_engine: tesseract (extraer texto)
#   - max_candidate_frames: 20-50 (más frames = mejor cobertura)

# =============================================================================
# Resultados de la extracción visual
# =============================================================================

# Los resultados se guardan en:

#   data/jobs/<job_id>/visual/
#   ├── scenes/              — Metadatos de escenas detectadas
#   ├── keyframes/           — Imágenes de keyframes (PNG)
#   ├── ocr/                 — Resultados de OCR por frame
#   └── analysis/            — Análisis visual completo

# Formato de los resultados:

#   - scenes.json: lista de escenas con timestamps y descripciones
#   - keyframes/: imágenes PNG numeradas por escena y frame
#   - ocr_results.json: texto extraído con bounding boxes y confianza
#   - visual_context.json: análisis completo del contenido visual

# =============================================================================
# Ejemplo de uso práctico
# =============================================================================

# Para extraer diagramas de arquitectura de un vídeo técnico:

#   vitk extract https://...arquitectura... --operations 5

# Y luego consultar los resultados:

#   vitk artifacts list <job_id>
#   vitk export <job_id> --format json

# Los diagramas serán visibles en:
#   data/jobs/<job_id>/visual/keyframes/

# Y el análisis en:
#   data/jobs/<job_id>/context/visual_context.json

# =============================================================================
# Integración con generación de activos
# =============================================================================

# Los diagramas y elementos visuales extraídos pueden ser convertidos
# en activos reutilizables:

#   - Documentos de arquitectura
#   - Diagramas en formato markdown (con código ASCII o mermaid)
#   - Documentación visual para equipos
#   - Material de formación

# Ver scripts/generate-assets.sh para generar documentación a partir
# de los resultados de la extracción.
