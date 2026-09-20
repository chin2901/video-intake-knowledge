# =============================================================================
# skill-generation/README.md — Ejemplo de generación de skills
# =============================================================================
#
# Este ejemplo demuestra cómo usar video-intake-knowledge para generar
# skills personalizados a partir del conocimiento extraído de vídeos.
#
# =============================================================================

# Generación de skills a partir de vídeos

# El sistema puede generar skills (competencias) que los agentes de IA
# pueden aprender a partir del contenido de vídeos procesados.

# =============================================================================
# Qué es un skill generado
# =============================================================================

# Un skill generado es un documento estructurado que contiene:
#   - Nombre y descripción del skill
#   - Procedimientos aprendidos del vídeo
#   - Ejemplos de uso
#   - Configuración recomendada
#   - Limitaciones conocidas

# Los skills se generan a partir del contenido extraído del vídeo:
#   - Transcripción → procedimientos, ejemplos, configuración
#   - Contexto de audio → resumen, temas, entidades
#   - Contexto visual → diagramas, flujos, interfaces

# =============================================================================
# Flujo de generación
# =============================================================================

# 1. Extraer un vídeo con conocimiento completo:

#   vitk extract https://www.youtube.com/watch?v=dQw4w9WgXcQ --operations 6

# 2. Generar propuesta de build (skill draft):

#   vitk proposals generate <job_id>

#   Esto analiza el contenido extraído y genera una propuesta de skill
#   con estructura y contenido sugerido.

# 3. Revisar y exportar la propuesta:

#   vitk proposals export <proposal_id> --format markdown

# 4. Usar el skill generado:

#   El skill se puede integrar con el sistema o usarse como referencia
#   para que el agente de IA aprenda nuevas capacidades.

# =============================================================================
# Tipos de skills que se pueden generar
# =============================================================================

# - Skills de procedimiento: "Cómo configurar X", "Pasos para hacer Y"
# - Skills de diagnóstico: "Cómo identificar problema Z"
# - Skills de análisis: "Cómo analizar W con herramienta T"
# - Skills de arquitectura: "Cómo diseñar sistema S"
# - Skills de integración: "Cómo conectar A con B"

# =============================================================================
# Ejemplo práctico
# =============================================================================

# Supongamos que extraemos un vídeo sobre "Cómo configurar un servidor
# web nginx":

#   vitk extract https://...nginx-config... --operations 6

# El sistema extraerá:
#   - Transcripción del vídeo
#   - Contexto de audio (resumen, temas, entidades)
#   - Contexto visual (diagramas de configuración, ejemplos de código)

# Luego podemos generar un skill:

#   vitk proposals generate <job_id>

# La propuesta incluirá:
#   - Nombre: "nginx-configuration"
#   - Descripción: "Configurar servidor web nginx"
#   - Procedimientos: los pasos del vídeo
#   - Ejemplos: los comandos y configs del vídeo
#   - Configuración: archivos de ejemplo extraídos

# =============================================================================
# APIs de Python para generación
# =============================================================================

# from video_intake_core.context import extract_knowledge, generate_build_proposal
# from video_intake_core.build_proposals import BuildProposalGenerator
#
# # Generar propuesta a partir de un job existente
# generator = BuildProposalGenerator()
# proposal = generator.generate_from_job(job_id="abc123")

# =============================================================================
# Integración con agentes de IA
# =============================================================================

# Los skills generados pueden ser:
#   - Incorporados al contexto del agente para sesiones futuras
#   - Almacenados como referencia documentada
#   - Compartidos con otros agentes o equipos
#   - Usados para entrenar o fine-tune de modelos
#   - Integrados en sistemas de gestión de conocimiento

# El skill se exporta en formatos compatibles:
#   - markdown: legible para humanos y máquinas
#   - json: estructura serializable
#   - mdx: markdown extendido con frontmatter

# =============================================================================
