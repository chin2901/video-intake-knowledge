# =============================================================================
# README.md — Adaptador de Hermes para video-intake-knowledge
# =============================================================================

# Plugin de Hermes — video-intake-knowledge

Plugin nativo de Hermes Agent para detectar, adquirir, analizar y convertir
vídeos en conocimiento utilizable dentro de sesiones de agentes de IA.

## Instalación

```bash
cd video-intake-knowledge
cd adapters/hermes
./install.sh
```

O manualmente:

```bash
mkdir -p ~/.hermes/plugins/video-intake-knowledge
cp plugin.yaml ~/.hermes/plugins/video-intake-knowledge/
cp -r hooks ~/.hermes/plugins/video-intake-knowledge/ 2>/dev/null || true
cp -r tools ~/.hermes/plugins/video-intake-knowledge/ 2>/dev/null || true
cp -r skill ~/.hermes/plugins/video-intake-knowledge/ 2>/dev/null || true
cp ../../scripts/standalone_hermes.sh ~/.hermes/plugins/video-intake-knowledge/
chmod +x ~/.hermes/plugins/video-intake-knowledge/standalone_hermes.sh
```

Luego añade a tu `~/.hermes/config.yaml`:

```yaml
plugins:
  - video-intake-knowledge
```

Reinicia Hermes para que detecte el plugin.

## Desinstalación

```bash
cd video-intake-knowledge/adapters/hermes
./uninstall.sh
```

O manualmente:

```bash
rm -rf ~/.hermes/plugins/video-intake-knowledge
```

Luego elimina la referencia en tu `~/.hermes/config.yaml`:

```yaml
plugins:
  - video-intake-knowledge  # <-- eliminar esta línea
```

## Qué hace

1. **Detección automática** — Cuando Hermes detecta una URL de vídeo o un
   adjunto de vídeo en un mensaje, el plugin inicia la interacción guiada.

2. **Interacción guiada** — Pregunta qué desea extraer:
   - [1] Descargar vídeo localmente
   - [2] Descargar/extraer audio localmente
   - [3] Transcripción de audio con timestamps
   - [4] Contexto basado en audio
   - [5] Contexto visual (diagramas, flujos, interfaces, animaciones)
   - [6] Todo lo anterior
   - [0] Cancelar

3. **Procesamiento** — Ejecuta las operaciones seleccionadas usando el núcleo
   portable `video_intake_core`.

4. **Post-extracción** — Pregunta qué hacer con los resultados:
   - Aplicar como mensaje
   - Añadir al contexto
   - Añadir a memoria
   - Crear banco de memoria nuevo
   - Analizar qué se puede construir (tools, skills, agentes, plugins)
   - Conservar solo artefactos

5. **Generación de activos** — Si el usuario elige construir algo, el plugin
   analiza el contenido extraído y produce propuestas estructuradas para
   tools, skills, agentes, plugins, plantillas, documentos o workflows.
   **Nunca crea nada sin confirmación explícita.**

## Capacidades

- Detección de YouTube, Facebook, Instagram, TikTok y archivos locales.
- Inspección sin descarga.
- Transcripción por capas (captions → Whisper local).
- OCR local (Tesseract) sobre frames candidatos.
- Análisis visual (FFmpeg + PySceneDetect + OpenCV).
- Gestión de jobs asíncronos con estado.
- Cancelación de jobs.
- Artefactos reproducibles con manifiestos.
- Exportación a Markdown, JSON, HTML.
- Integración con memoria de Hermes (si disponible).
- CLI standalone como fallback.

## Tools registradas

El plugin registra las siguientes tools en Hermes:

- `video_intake_inspect_source` — Inspeccionar metadatos de una URL/archivo.
- `video_intake_create_job` — Crear un nuevo job de extracción.
- `video_intake_get_job_status` — Estado de un job.
- `video_intake_cancel_job` — Cancelar un job.
- `video_intake_get_artifacts` — Listar artefactos de un job.
- `video_intake_extract_transcript` — Extraer transcripción.
- `video_intake_extract_audio_context` — Extraer contexto de audio.
- `video_intake_extract_visual_context` — Extraer contexto visual.
- `video_intake_list_memory_banks` — Listar bancos de memoria.
- `video_intake_store_memory` — Añadir entrada a memoria.
- `video_intake_create_memory_bank` — Crear banco de memoria.
- `video_intake_analyze_build_options` — Analizar qué se puede construir.
- `video_intake_generate_asset_draft` — Generar un borrador de activo.

## Hooks

El plugin puede registrar hooks para detectar vídeos automáticamente:

- `message.processed` — Detecta URLs de vídeo en mensajes antes de que
  el modelo responda.
- `attachment.detected` — Detecta adjuntos de vídeo.

Estos hooks inician la interacción guiada sin esperar a que el usuario
lo solicite explícitamente.

## Comandos manuales

Si los hooks no están disponibles o no funcionan, puedes usar estos comandos
manualmente en tu sesión Hermes:

```
/video inspect URL_O_RUTA
/video extract URL_O_RUTA --select 1,3,5
/video status ID_DEL_JOB
/video cancel ID_DEL_JOB
/video artifacts ID_DEL_JOB
/video doctor
```

## Integración con memoria

Cuando el usuario elige guardar en memoria, el plugin:

1. Lista los bancos de memoria disponibles en Hermes.
2. Muestra para cada banco: nombre, descripción, ámbito, retención, permisos.
3. Pide selección explícita del banco.
4. Añade la entrada con contenido estructurado, fuente, timestamps,
   artefactos asociados, confianza, etiquetas, fecha.

Si Hermes no expone memoria programática, se ofrece exportación a
Markdown/JSON para importación manual.

## Configuración

Copia `config.example.yaml` a tu directorio de configuración de Hermes y
ajusta los valores:

```bash
cp config.example.yaml ~/.hermes/config.d/video-intake-knowledge.yaml
```

O intégralo en tu `config.yaml` principal bajo la clave `video_intake`.

## Seguridad

- Validación de URL y protección SSRF.
- Validación MIME de archivos descargados.
- Límites de tamaño, duración, concurrencia y timeouts.
- Protección ante prompt injection en transcripciones, OCR y subtítulos.
- Todo contenido extraído se trata como DATOS NO CONFIABLES.
- Sanitización de nombres de archivos y rutas.

## Limitaciones

- Los vídeos remotos requieren conexión a internet.
- Los modelos de IA locales requieren instalación explícita (`video-intake models install`).
- La memoria nativa solo está disponible si Hermes la expone.
- Los hooks pueden no estar disponibles en todas las versiones de Hermes.

## Solución de problemas

Ver `docs/troubleshooting.md` o ejecuta:

```bash
video-intake doctor
```

## Enlaces

- Repositorio: https://github.com/aibos/video-intake-knowledge
- Documentación: https://github.com/aibos/video-intake-knowledge/blob/main/README.md
- Issues: https://github.com/aibos/video-intake-knowledge/issues
