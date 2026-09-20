[tool-video-intake-knowledge] /srv/video-intake-knowledge/ — Ubicación del proyecto
================================================================================

Este proyecto NO pertenece a AibOS, Aibot, Hermes ni ningún sistema relacionado.
Es un proyecto independiente de conversión de vídeos en conocimiento para agentes
de IA, instalado en /srv/ como servicio propio.

Banco de memoria independiente
================================================================================
La memoria de conocimiento extraído se almacena en una base de datos SQLite
dedicada, separada del resto del proyecto:

  - SQLite DB: /srv/video-intake-knowledge/memory/memory.db
  - Configuración: memory.db_path en config/default.yaml
  - Variable de entorno: VITK_MEMORY_DIR=/srv/video-intake-knowledge/memory

Ruta del proyecto: /srv/video-intake-knowledge/
  - Código fuente: /srv/video-intake-knowledge/packages/video_intake_core/
  - Documentación: /srv/video-intake-knowledge/docs/
  - Scripts: /srv/video-intake-knowledge/scripts/
  - Configuración: /srv/video-intake-knowledge/config/
  - Memory bank: /srv/video-intake-knowledge/memory/
  - Adapters de host: /srv/video-intake-knowledge/adapters/
  - Skill portable: /srv/enty-knowledge/skill/

Esta ubicación fue elegida porque:
  - Está en /srv/, la convención para servicios/servidores independientes
  - No está dentro de /home/aibos/ ni de /srv/aibos/ (AibOS/Hermes)
  - Es agnóstica del usuario y de AibOS
  - Tiene su propio banco de memoria en subdirectorio dedicado

Para actualizar la ruta de la memoria en caso de necesidad:
  export VITK_MEMORY_DIR=/srv/video-intake-knowledge/memory
