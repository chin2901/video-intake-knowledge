# Arquitectura de video-intake-knowledge

## Resumen

`video-intake-knowledge` es un sistema modular que detecta, adquiere, analiza y
convierte vídeos en conocimiento utilizable dentro de agentes de IA. El núcleo es
un paquete Python portable (`video_intake_core`) que se ejecuta vía CLI o como
librería, con adaptadores específicos para cada host (Hermes, AGY, OpenCode, etc.).

## Capas

```
                     ┌─────────────────────────────────┐
                     │       Adaptador de Host          │
                     │  (Hermes / AGY / OpenCode / ...) │
                     └───────────────┬─────────────────┘
                                     │ invoca
                                     ▼
                     ┌─────────────────────────────────┐
                     │         CLI / Tools              │
                     │   video-intake <comando> ...     │
                     └───────────────┬─────────────────┘
                                     │ importa
                                     ▼
            ┌──────────────────────────────────────────────────┐
            │               video_intake_core                    │
            │  acquisition │ audio │ transcription │ visual     │
            │  ocr         │ context │ artifacts │ jobs         │
            │  storage     │ policies │ security │ utils        │
            └──────────────────────────────────────────────────┘
                                     │ usa
                                     ▼
            ┌──────────────────────────────────────────────────┐
            │           Herramientas del sistema                 │
            │  FFmpeg │ yt-dlp │ OpenCV │ Tesseract │           │
            │  faster-whisper │ whisper.cpp │ PySceneDetect    │
            └──────────────────────────────────────────────────┘
```

## Núcleo (`packages/video_intake_core/`)

El núcleo es un paquete Python sin dependencia de Hermes ni de ningún host. Sus
módulos son:

| Módulo         | Responsabilidad                                              |
|----------------|--------------------------------------------------------------|
| `acquisition`  | Detección y resolución de URL de vídeo. Fuentes soportadas: YouTube, Facebook, Instagram, TikTok, archivos locales. |
| `inspection`   | Extracción de metadatos: duración, resolución, codecs, streams, subtítulos disponibles, sin descargar el vídeo. |
| `audio`        | Extracción de audio desde archivos locales o URLs remotas vía FFmpeg. Formatos: wav, mp3, m4a, opus, flac. |
| `transcription`| Estrategias de transcripción por capas: platform captions → descargables (SRT/VTT/ASS/JSON3) → Whisper/faster-whisper → user models. |
| `visual`       | Detección de escenas (PySceneDetect), extracción de keyframes, análisis de fotogramas. |
| `ocr`          | OCR de fotogramas: Tesseract con preprocesado OpenCV, batch OCR, scores de confianza, bounding boxes. |
| `context`      | Generación de contexto de audio (summary, índice temporal, temas, entidades, citas, niveles de confianza). Contexto visual (escenas, OCR, diagramas inferidos). Extracción de conocimiento. Exportación MDX. |
| `artifacts`    | Registro y gestión de artefactos: transcript, audio, frames, OCR, context documents. |
| `jobs`         | Gestión de trabajos: creación, ejecución, estado, cancelación, persistencia en SQLite, reanudación. |
| `storage`      | Almacenamiento de artefactos con deduplicación SHA-256, estructura por job, limpieza por antigüedad. |
| `policies`     | Lectura de configuración YAML, política de modelos, límites, permisos. |
| `security`     | Validación de URL (SSRF), detección MIME, sanitización de nombres, protección contra prompt injection en transcripciones/OCR, redacción de datos sensibles. |
| `memory`       | Interfaz abstracta `MemoryProvider` y implementación local SQLite. |
| `utils`        | Utilidades: validación de URL, hashing SHA-256, manejo de archivos, carga de config YAML, validación contra JSON Schema. |
| `schemas`      | JSON Schema versionados para todos los contratos de datos del sistema. |

## Flujo típico de un trabajo

```
1. DETECCIÓN
   El host (Hermes plugin, CLI, etc.) detecta una URL o adjunto de vídeo.

2. INSPECCIÓN
   video_intake_core.inspect(video_source) → metadatos sin descarga.
   Se muestra al usuario: título, duración, plataforma, qué subtítulos existen.

3. SELECCIÓN (interacción guiada)
   El usuario elige qué extraer:
   [1] Video   [2] Audio   [3] Transcript   [4] Audio context
   [5] Visual context   [6] Todo   [0] Cancelar

   Si hay varios vídeos: modo global o individual.

4. EJECUCIÓN
   Se crea un job en jobs/ con un job_id único.
   Cada operación seleccionada se ejecuta en orden:
   - Siempre se intenta primero estrategias deterministas (captions).
   - Si no hay captions, se descarga audio y se transcribe con Whisper.
   - Si se eligió contexto visual, se extraen frames, se detectan escenas,
     se hace OCR, y se genera contexto visual.
   - Los artefactos se guardan en artifacts/<job_id>/.

5. POST-EXTRACCIÓN (interacción obligatoria)
   "¿Qué desea hacer con los resultados?"
   [1] Aplicar como mensaje   [2] Añadir al contexto
   [3] Banco de memoria existente   [4] Crear nuevo banco
   [5] Analizar qué se puede construir   [6] Solo artefactos
   [0] Cancelar

6. MEMORIA O EXPORTACIÓN
   Si el usuario eligió memoria, se usa MemoryProvider para añadir entradas.
   Si no, los artefactos persisten localmente con su política de retención.

7. LIMPIEZA
   La política de retención elimina artefactos antiguos automáticamente.
```

## Adaptadores

### Hermes (prioritario)

Integración nativa completa:

- **Plugin** registrado en `adapters/hermes/plugin.yaml`.
- **Tools** registradas: `video_intake_inspect_source`, `video_intake_create_job`, `video_intake_get_job_status`, etc.
- **Hooks** de detección de mensajes con vídeo.
- **Skills** registrables para flujos complejos.
- **CLI standalone** en `scripts/standalone_hermes.sh` para fallback.
- **Comandos manuales**: `/video`, `/video status`, `/video cancel`, `/video artifacts`, `/video doctor`.

### Otros hosts (AGY, OpenCode, Claude Code, Codex, genérico)

Cada adaptador declara:

- Qué capacidades soporta nativamente.
- Qué capacidades están degradadas.
- Cómo instalar y desinstalar.
- Cómo usar el fallback (CLI o script manual) cuando el host no tiene hooks, memoria, tools, etc.

La referencia común es `skill/SKILL.md`.

## Configuración

La configuración se lee de YAML y variables de entorno. Precedencia:

1. Argumentos CLI (mayor precedencia)
2. Variables de entorno `VITK_*`
3. Archivo de configuración especificado (`--config` o `VITK_CONFIG_PATH`)
4. `config/default.yaml` (por defecto)

Perfiles de configuración:

| Perfil        | Uso                                                          |
|---------------|--------------------------------------------------------------|
| `default.yaml`| Valor por defecto. Equilibrado.                             |
| `offline.yaml`| Sin descargas remotas. Solo archivos locales.              |
| `low-cost.yaml`| Sin modelos externos. Solo Whisper tiny + Tesseract.       |
| `production.yaml`| Con políticas estrictas, retención, escaneo de seguridad. |

## Estrategias por capas

### Transcripción

1. **Platform captions** (YouTube, Facebook, etc.) — si existen, se usan.
2. **Descargables** — SRT, VTT, ASS, SSA, JSON3 descargados vía yt-dlp.
3. **Whisper local** — faster-whisper con modelo configurable (tiny por defecto).
4. **Modelos del usuario** — instalados explícitamente.
5. **Modelos externos** — solo si la política lo permite y el usuario aprueba.

### Visual

1. **Metadatos y thumbnails** de la fuente.
2. **FFmpeg** para extraer keyframes y fotogramas por intervalo.
3. **PySceneDetect** para detectar cortes y cambios de escena.
4. **OCR local** — Tesseract sobre candidatos relevantes.
5. **OpenCV** para detección de regiones, cambios, flechas, cajas.
6. **Modelo de visión local** — si el usuario lo instaló.
7. **Modelo de visión externo** — solo si la política lo permite.

## Datos y artefactos

Cada job genera `artifacts/<job-id>/` con:

```
artifacts/<job-id>/
├── manifest.json          # Metadatos del job yLista de artefactos
├── source.json           # Información de la fuente
├── provenance.md         # Qué se hizo, con qué herramientas y versiones
├── transcript_raw/       # Transcripciones en crudo (txt, srt, vtt)
├── transcript_timestamped.md
├── audio_context.md
├── visual_context.md
├── extracted_knowledge.md
├── frames/               # Fotogramas extraídos
├── ocr.json              # Resultados de OCR
├── logs/                 # Logs del job
└── exports/              # Exportaciones (markdown, json, html)
```

El `manifest.json` registra job_id, timestamp UTC, URL o hash del archivo, plataforma,
título, duración, operaciones seleccionadas, herramientas y versiones usadas, modelos
usados, parámetros, tiempos de ejecución, errores/warnings, hashes SHA-256 de
artefactos, política de retención, estado final.

## Seguridad

- **Validación de URL:** se valida formato y se rechazan URLs internas/sospechosas.
- **Protección SSRF:** se bloquean accesos a rangos de IP privados y de metadatos de nube.
- **Validación MIME:** se detecta el tipo real del archivo descargado y se verifica que
  coincida con la extensión esperada.
- **Límites:** tamaño máximo de descarga, duración máxima de vídeo, número máximo de
  vídeos por trabajo, concurrencia máxima, timeouts.
- **Sanitización:** nombres de archivo y rutas se sanitizan.
- **Prompt injection:** transcripciones, subtítulos y OCR se tratan como datos no
  confiables. Se marcan en los logs las inyecciones detectadas.
- **Cuarentena:** archivos sospechosos se aíslan en `quarantine/` para revisión.
- **Escanéo opcional:** configurable mediante ClamAV si está disponible.
- **Sin secretos en el repo:** las claves de API se obtienen exclusivamente de
  variables de entorno, mecanismos de secretos del host o archivos locales explícitamente
  excluidos de Git.

## Storage y memoria

### Storage local

Los artefactos se guardan localmente con deduplicación SHA-256. La estructura es
`artifacts/<job-id>/`. La política de retención elimina artefactos antiguos
automáticamente.

### Memory provider

Interfaz abstracta `MemoryProvider` con:

- `list_memory_banks()`
- `describe_memory_bank()`
- `add_entry()`
- `create_memory_bank()`
- `search()`
- `health_check()`

Implementación local: `LocalSQLiteMemoryProvider` (SQLite en `./video_intake_memory.db`).

Para Hermes: integración real con el mecanismo de memoria disponible en Hermes.
Para hosts sin memoria programática: exportar paquete Markdown/JSON para importación
manual.

## Reproducibilidad

- Cada job tiene un `job_id` único.
- Los artefactos tienen hashes SHA-256.
- El manifest registra herramientas, versiones y parámetros.
- Los comandos de exportación permiten obtener markdown, json o html.
- Los logs permiten auditar el proceso.
