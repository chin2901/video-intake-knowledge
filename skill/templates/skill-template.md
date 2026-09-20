# =============================================================================
# skill-templates.md — Plantilla de skill para video-intake-knowledge
# =============================================================================
#
# Esta plantilla demuestra cómo estructurar un skill compatible con
# video-intake-knowledge para diferentes entornos de agentes de IA.
#
# =============================================================================

# =============================================================================
# Estructura de un skill compatible
# =============================================================================

# Un skill para video-intake-knowledge debe incluir:

# 1. SKILL.md — Instrucciones para el asistente (ver skill/SKILL.md)
# 2. Comandos disponibles:
#    - vitk doctor       — Diagnóstico del entorno
#    - vitk extract      — Extracción interactiva de vídeo
#    - vitk batch        — Procesamiento por lotes
#    - vitk status       — Estado de trabajos en ejecución
#    - vitk artifacts    — Listing de artefactos generados
#    - vitk export       — Exportar resultados
#    - vitk knowledge    — Gestión de conocimiento extraído
# 3. Configuración: ver config/default.yaml

# =============================================================================
# Integración con diferentes entornos
# =============================================================================

# Hermes Agent:
#   - Usar adapters/hermes/plugin.yaml para registrar las tools
#   - Usar adapters/hermes/hooks/ para detección automática de vídeos
#   - Instalar con: bash adapters/hermes/install.sh

# Claude Code:
#   - Usar adapters/claude-code/SKILL.md como referencia
#   - Instalar con: bash adapters/claude-code/install.sh

# OpenCode:
#   - Usar adapters/opencode/SKILL.md como referencia
#   - Instalar con: bash adapters/opencode/install.sh

# Codex:
#   - Usar adapters/codex/SKILL.md como referencia
#   - Instalar con: bash adapters/codex/install.sh

# AGY:
#   - Usar adapters/agy/SKILL.md como referencia
#   - Configurar con: adapters/agy/config.example.yaml

# Otros entornos compatibles con SKILL.md:
#   - Usar skill/SKILL.md como base portable
#   - Ajustar la integración según las capacidades del host

# =============================================================================
# Flujo de trabajo recomendado
# =============================================================================

# 1. DETECCIÓN
#    El sistema detecta automáticamente vídeos o enlaces de vídeo
#    en la conversación del usuario.

# 2. INTERACCIÓN
#    Se ofrece al usuario un menú de opciones:
#    [1] Descargar vídeo localmente
#    [2] Descargar audio localmente
#    [3] Transcripción de audio con timestamps
#    [4] Extraer contexto basado en audio
#    [5] Extraer contexto visual
#    [6] Todo lo anterior
#    [0] Cancelar

# 3. SELECCIÓN
#    El usuario selecciona una o varias opciones.
#    Formato aceptado: "1,3,5", "1 3 5", "todo", "todos", "6", "0"

# 4. PROCESAMIENTO
#    El sistema ejecuta las operaciones seleccionadas en las
#    siguientes capas (según la configuración):
#    - Estrategia determinista primero (subtítulos de plataforma)
#    - Estrategia local (Whisper) si no hay subtítulos
#    - OCR de frames para contenido visual
#    - Generación de contexto después de la transcripción

# 5. RESULTADOS
#    Los resultados se almacenan en el sistema de storage y
#    están disponibles para:
#    - Exportación en formato markdown, JSON o MDX
#    - Almacenamiento en memoria para consulta futura
#    - Generación de activos de conocimiento (documentos, paquetes)

# =============================================================================
# Ejemplo de integración mínima
# =============================================================================

# Para integrar video-intake-knowledge en un entorno de agente de IA
# sin modificar el agente mismo, basta con:

# 1. Instalar el paquete:
#    pip install video-intake-knowledge
#    o: uv pip install video-intake-knowledge

# 2. Asegurar que los comandos están en PATH:
#    export PATH="$HOME/.local/bin:$PATH"
#    (o la ruta donde se instaló vitk)

# 3. Usar los comandos desde el agente:
#    vitk extract <url> --operations 6

# 4. (Opcional) Registrar las tools en el entorno del agente
#    siguiendo los ejemplos de los adaptadores.

# =============================================================================
# Véase también
# =============================================================================

# - skill/SKILL.md — Skill portable completo
# - docs/portability.md — Guía de compatibilidad por entorno
# - adapters/hermes/ — Adaptador para Hermes Agent
# - adapters/claude-code/ — Adaptador para Claude Code
# - adapters/opencode/ — Adaptador para OpenCode
# - adapters/codex/ — Adaptador para Codex
# - adapters/agy/ — Adaptador para AGY
# - config/default.yaml — Configuración por defecto
