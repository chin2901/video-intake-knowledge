# =============================================================================
# SKILL.md — Skill específico para Hermes Agent
# =============================================================================
#
# Este skill es la versión específica para Hermes Agent, optimizada
# para aprovechar las capacidades nativas del host.
#
# =============================================================================

# =============================================================================
# Video Intake Knowledge — Skill para Hermes Agent
# =============================================================================

# Detecta, descarga, transcribe y extrae conocimiento de vídeos de
# YouTube, Facebook, Instagram, TikTok y archivos locales.

# PRIORIDAD: Hermes Agent (host nativo)
# COMPATIBILIDAD: También funciona en otros hosts vía SKILL.md canónico

# =============================================================================
# Capacidades específicas de Hermes
# =============================================================================

# Hermes Agent puede:

# 1. DETECCIÓN AUTOMÁTICA
#    - Detectar URLs de vídeo en mensajes del usuario antes de responder
#    - Detectar archivos adjuntos de vídeo en la conversación
#    - Iniciar interacción de extracción automáticamente

# 2. INTERRUPCIONES CONTROLADAS
#    - Pausar la generación de respuesta para preguntar al usuario
#    - Conservar estado de la interacción por session_id
#    - Evitar consultas repetidas al usuario

# 3. GESTIÓN DE TRABAJOS ASÍNCRONOS
#    - Ejecutar extracciones en background
#    - Consultar estado de trabajos en progreso
#    - Cancelar trabajos si el usuario lo solicita
#    - Recibir resultados cuando estén listos

# 4. MEMORIA NATIVA Y PERSISTENTE
#    - Usar el sistema de memoria nativo de Hermes si está disponible
#    - Almacenar conocimiento en bancos SQLite aislados en ~/.video-intake/
#    - Consultar memoria existente antes de extraer nuevo contenido

# =============================================================================
# Instalación en Hermes
# =============================================================================

# 1. Instalar el paquete:
#   cd /srv/video-intake-knowledge
#   pip install -e .

# 2. Instalar el plugin de Hermes:
#   bash adapters/hermes/install.sh

# 3. Reiniciar Hermes Agent para cargar el plugin.

# =============================================================================
# Herramientas registradas en Hermes
# =============================================================================

# Tras la instalación, Hermes tendrá disponibles las siguientes tools:
# - video_intake_detect_videos: detecta vídeos en un mensaje
# - video_intake_inspect: inspecciona metadatos de un vídeo
# - video_intake_extract: inicia extracción interactiva
# - video_intake_get_job_status: consulta estado de un trabajo
# - video_intake_cancel_job: cancela un trabajo en progreso
# - video_intake_get_artifacts: lista artefactos de un job
# - video_intake_extract_transcript: extrae transcripción específica
# - video_intake_extract_audio_context: extrae contexto de audio
# - video_intake_extract_visual_context: extrae contexto visual
# - video_intake_list_memory_banks: lista bancos de memoria disponibles
# - video_intake_store_memory: almacena entrada en banco de memoria
# - video_intake_create_memory_bank: crea un nuevo banco de memoria
# - video_intake_analyze_build_options: analiza opciones de build
# - video_intake_generate_asset_draft: genera borrador de activo

# =============================================================================
# Flujo de detección automática
# =============================================================================

# El hook de detección (adapters/hermes/hooks/hook_video_intake.sh)
# se ejecuta antes de cada respuesta del asistente para detectar si
# el usuario ha enviado vídeos o enlaces de vídeo.

# Si se detectan vídeos, el hook inicia la interacción mostrando
# el menú de opciones al usuario.

# El estado de la interacción se conserva por session_id, permitiendo
# que el usuario continúe la extracción en múltiples turnos.

# =============================================================================
# Gestión de trabajos en Hermes
# =============================================================================

# Los trabajos se ejecutan de forma asíncrona. Hermes puede:
# - Consultar estado: video-intake status <job_id> o video_intake_get_job_status
# - Cancelar: video-intake cancel <job_id> o video_intake_cancel_job
# - Ver resultados: video-intake artifacts <job_id> o video_intake_get_artifacts
# - Exportar: video-intake export <job_id> --format markdown
# - Propuestas: video-intake proposals --scaffold {skill,tool,agent}

# =============================================================================
# Aislamiento Estricto de Memoria
# =============================================================================

# Si Hermes tiene un sistema de memoria nativo disponible, el sistema
# puede usarlo en lugar del banco de memoria local. Para configurar:
#   memory:
#     provider: "host_native"  # usar memoria de Hermes si está disponible
#     fallback_to_local: true  # si no, usar banco local

# Si Hermes no tiene memoria nativa, el sistema usa automáticamente
# el banco SQLite persistente en el espacio de usuario: ~/.video-intake/memory.db
# NUNCA se almacenan bases de datos ni archivos temporales en el repositorio Git.

# =============================================================================
# Ejemplo de interacción en 2 Fases
# =============================================================================

# Usuario: "Mira este vídeo: https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Hermes:
#   "He detectado 1 vídeo.
#
#    FASE 1: ¿Qué necesitas extraer del vídeo?
#    [1] Descargar vídeo localmente
#    [2] Descargar audio localmente
#    [3] Transcripción de audio con timestamps
#    [4] Contexto basado en audio (resumen, puntos clave y tópicos)
#    [5] Contexto extraído de manera visual (diagramas, flujos, interfaces)
#    [6] Todo lo anterior (1, 2, 3, 4 y 5)
#    [0] Cancelar"

# Usuario: "todo"

# Hermes ejecuta la extracción con:
#   video-intake extract "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --select 6

# Hermes:
#   "Extracción completada con éxito.
#
#    FASE 2: ¿Qué deseas hacer con el conocimiento extraído?
#    [1] Aplicarlo como mensaje a la sesión en curso
#    [2] Añadirlo al contexto de la sesión en curso (memoria de trabajo compacta)
#    [3] Añadirlo a un banco de memoria existente en ~/.video-intake/
#    [4] Crear un nuevo banco de memoria para añadirlo
#    [5] Idear y construir herramientas/skills/agentes (video-intake proposals --scaffold)
#    [6] Conservar únicamente los artefactos locales en disco"

# =============================================================================
# Véase también
# =============================================================================
# - adapters/hermes/install.sh — Instalador del plugin
# - adapters/hermes/uninstall.sh — Desinstalador del plugin
# - adapters/hermes/plugin.yaml — Definición del plugin
# - adapters/hermes/hooks/hook_video_intake.sh — Hook de detección
# - SKILL.md — Especificación canónica universal
