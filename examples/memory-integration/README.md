# =============================================================================
# memory-integration/README.md — Ejemplo de integración con banco de memoria
# =============================================================================
#
# Este ejemplo demuestra cómo usar video-intake-knowledge con el banco de
# memoria independiente para almacenar y consultar conocimiento extraído.
#
# =============================================================================

# Banco de memoria independiente

# El proyecto usa un banco de memoria dedicado, separado del resto del
# código y de AibOS/Hermes. La memoria vive en:

#   /srv/video-intake-knowledge/memory/memory.db

# Este banco almacena conocimiento extraído de vídeos procesados y es
# accesible vía los comandos de memoria del CLI o directamente desde
# las APIs de Python.

# =============================================================================
# Ubicación y configuración
# =============================================================================

# La ubicación del banco se configura en config/default.yaml:

#   memory:
#     db_path: "/srv/video-intake-knowledge/memory/memory.db"

# También se puede configurar con variable de entorno:

#   export VITK_MEMORY_DIR=/srv/video-intake-knowledge/memory

# El script create_memory_db.py permite inicializar o reinicializar
# el banco:

#   python3 scripts/create_memory_db.py

# =============================================================================
# Flujo de integración
# =============================================================================

# 1. Extraer un vídeo (con memoria habilitada):

#   vitk extract https://www.youtube.com/watch?v=dQw4w9WgXcQ

#   Durante la extracción, el sistema preguntará si deseas almacenar
#   el conocimiento extraído en el banco de memoria (por defecto: sí,
#   si require_confirmation está habilitado).

# 2. Consultar la memoria:

#   vitk memory list                    — Listar entradas
#   vitk memory search "término"        — Buscar por texto
#   vitk memory get <entry_id>          — Obtener entrada específica
#   vitk memory delete <entry_id>       — Eliminar entrada

# 3. APIs de Python para integración avanzada:

#   from video_intake_core.memory import MemoryProvider, LocalMemoryProvider
#
#   provider = LocalMemoryProvider(db_path="/srv/video-intake-knowledge/memory/memory.db")
#   entries = provider.list(content_type="knowledge")
#   results = provider.search(query="Python", limit=10)

# =============================================================================
# Casos de uso del banco de memoria
# =============================================================================

# - Almacenar conocimiento extraído de forma persistente
# - Consultar vídeos procesados anteriormente sin reprocesarlos
# - Enlazar entradas relacionadas (ej. varios vídeos sobre el mismo tema)
# - Buscar por contenido, tipo, fecha o tags
# - Exportar el banco completo para backup o migración

# =============================================================================
# Gestión del banco de memoria
# =============================================================================

# Backup:
#   cp /srv/video-intake-knowledge/memory/memory.db /ruta/de/backup/

# Exportar a JSON:
#   vitk memory export --output memory_export.json

# Importar desde JSON:
#   vitk memory import --input memory_export.json

# Estadísticas:
#   vitk memory stats

# Limpiar todo (requiere confirmación):
#   vitk memory clear

# Reinicializar el banco (borra todo):
#   python3 scripts/create_memory_db.py --reset

# =============================================================================
# Integración con otros sistemas
# =============================================================================

# El banco de memoria es independiente y puede ser accedido por otros
# sistemas o scripts fuera de video-intake-knowledge:

# - SQLite directo: cualquier herramienta SQLite puede leer la DB
# - Python: usar el módulo video_intake_core.memory
# - Exportación JSON: para integración con otros sistemas de IA

# La memoria es de conocimiento extraído de vídeos y no contiene
# datos personales ni información sensible sin redactar.
