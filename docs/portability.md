# Portabilidad de video-intake-knowledge

## Resumen

El núcleo (`video_intake_core`) es agnóstico al host. Se ejecuta en cualquier
entorno con Python 3.11+ y las dependencias del sistema requeridas. Los
adaptadores añaden integración nativa con hosts específicos.

## Matriz de compatibilidad

### Core (todos los hosts)

| Capacidad | Disponibilidad |
|-----------|----------------|
| CLI `video-intake` | Sí, en todos los hosts |
| Detección de vídeo | Sí (CLI + API) |
| Inspección | Sí |
| Extracción de audio | Sí (FFmpeg) |
| Transcripción local | Sí (Whisper/faster-whisper) |
| OCR local | Sí (Tesseract) |
| Análisis visual | Sí (FFmpeg + PySceneDetect + OpenCV) |
| Gestión de jobs | Sí (SQLite) |
| Artefactos | Sí |
| Exportación | Sí (markdown, JSON, HTML) |
| Memoria local | Sí (SQLite) |
| CLI standalone | Sí |

### Hermes Agent (prioritario)

| Capacidad | Estado |
|-----------|--------|
| Plugin nativo | Sí |
| Tools registradas | Sí (ver plugin.yaml) |
| Hooks de detección | Sí (hooks/) |
| Integración de memoria | Sí (si el host la expone) |
| Comandos manuales `/video` | Sí |
| CLI standalone fallback | Sí |
| Instalación | adapters/hermes/install.sh |
| Desinstalación | adapters/hermes/uninstall.sh |

**Capacidades degradadas:**
- Si Hermes no expone hooks de `message.processed`, la detección automática
  no funciona. El usuario debe invocar manualmente.
- Si Hermes no expone memoria programática, no hay integración nativa de memoria.
  Se ofrece exportación manual.

### AGY

| Capacidad | Estado |
|-----------|--------|
| CLI standalone | Sí |
| Skills | Sí (SKILL.md portable) |
| Tools nativas | No (AGY no las soporta) |
| Hooks | No (AGY no los soporta) |
| Memoria nativa | No documentada |
| Comandos manuales | CLI directamente |

**Flujo:** El usuario o el agente ejecuta `video-intake` directamente desde
la CLI. La skill portable describe cómo usarla.

### OpenCode

| Capacidad | Estado |
|-----------|--------|
| CLI standalone | Sí |
| Skills | Sí (SKILL.md portable) |
| Tools nativas | No (OpenCode no las soporta) |
| Hooks | No documentado |
| Memoria nativa | No documentada |
| Comandos manuales | CLI directamente |

### Claude Code

| Capacidad | Estado |
|-----------|--------|
| CLI standalone | Sí |
| Skills | Sí (SKILL.md portable) |
| Tools nativas | No (Claude Code no las soporta) |
| Hooks | No documentado |
| Memoria nativa | No documentada |
| Comandos manuales | CLI directamente |

### Codex

| Capacidad | Estado |
|-----------|--------|
| CLI standalone | Sí |
| Skills | Sí (SKILL.md portable) |
| Tools nativas | No (Codex no las soporta) |
| Hooks | No documentado |
| Memoria nativa | No documentado |
| Comandos manuales | CLI directamente |

### Genérico (CLI standalone)

| Capacidad | Estado |
|-----------|--------|
| CLI standalone | Sí, completo |
| Detección manual | Sí (el usuario ejecuta los comandos) |
| Memoria | SQLite local |
| Exportación | Sí |
| Sin dependencias de host | Sí |

## Skill portable

El archivo `skill/SKILL.md` es la referencia portable para cualquier entorno
compatible con SKILL.md. Describe:

- Qué hace el proyecto.
- Cómo instalarlo.
- Cómo usar cada comando.
- Ejemplos para cada caso de uso.
- Configuración y variables de entorno.
- Integración con memoria.
- Generación de activos.
- Seguridad.
- Solución de problemas.

## Fallbacks por capacidad

Cuando un host no soporta una capacidad nativamente, el fallback es:

| Capacidad no soportada | Fallback |
|------------------------|----------|
| Detección automática de vídeos | El usuario o agente ejecuta `video-intake inspect URL`. |
| Tools nativas | CLI directamente. |
| Hooks | Invocación manual del CLI. |
| Memoria nativa | SQLite local o exportación Markdown/JSON. |
| Jobs asíncronos | CLI con polling (`video-intake status`). |
| Cancelación | `video-intake cancel <job-id>`. |

## Requisitos mínimos por host

Todos los hosts requieren:
- Python 3.11+
- ffmpeg y ffprobe
- El paquete `video-intake-core` instalado
- `video-intake` en PATH (o invocable vía Python)

Para funcionalidades específicas:
- Transcripción local: Whisper/faster-whisper instalado.
- OCR: Tesseract instalado.
- Análisis visual avanzado: OpenCV + PySceneDetect instalados.
- Memoria nativa (Hermes): Integración con la API de memoria del host.

## Limitaciones reales

1. **Los vídeos remotos requieren conexión a internet.** Sin conexión, solo se
   pueden procesar archivos locales (ver `config/offline.yaml`).

2. **La disponibilidad de fuentes remotas depende de la plataforma.** YouTube,
   Facebook, Instagram y TikTok pueden cambiar sus políticas y bloquear el
   acceso en cualquier momento. yt-dlp es la herramienta de adquisición
   principal y su capacidad depende de su mantenimiento.

3. **Los modelos de IA locales requieren instalación explícita.** No se
   descargan automáticamente durante la instalación básica. El usuario debe
   usar `video-intake models install <model>`.

4. **Los hosts sin hooks no tienen detección automática.** El usuario o el
   agente deben invocar manualmente el CLI.

5. **La memoria nativa solo está disponible en Hermes.** Otros hosts usan
   SQLite local o exportación manual.

6. **Los adaptadores para AGY, OpenCode, Claude Code y Codex son version 1.0**
   y pueden tener limitaciones no documentadas. Se recomienda usar el CLI
   directamente en estos hosts hasta que se validen más integraciones.

## Implanteación de nuevos hosts

Para añadir soporte para un nuevo host:

1. Crear `adapters/<host>/`.
2. Añadir `README.md` con capacidades, limitaciones, instalación y desinstalación.
3. Añadir `install.sh` si el host lo requiere.
4. Añadir `uninstall.sh` si el host lo requiere.
5. Si el host soporta SKILL.md, añadir `SKILL.md`.
6. Actualizar `docs/portability.md` con la nueva fila de la matriz.
7. Declarar honestamente qué capacidades soporta y cuáles no.

## Transición entre hosts

El proyecto está diseñado para que los resultados sean portables entre hosts:

- Los artefactos se guardan en `artifacts/<job-id>/` con una estructura
  definida.
- Los manifiestos JSON registran todo lo necesario para reproducir o auditar.
- La exportación Markdown/JSON permite mover resultados entre hosts.
- La memoria local SQLite puede exportarse e importarse.
- Las skills son portables vía `skill/SKILL.md`.

Esto significa que un job iniciado en Hermes puede exportarse y continuar en
otro host, o que un resultado obtenido en un host puede ser procesado en otro.
