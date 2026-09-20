# SKILL.md — Skill portable para video-intake-knowledge (OpenCode)
> Esta skill es portable y funciona en OpenCode y otros entornos compatibles con SKILL.md.

## Resumen

Video Intake Knowledge detecta, adquiere, analiza y convierte vídeos en
conocimiento utilizable dentro de agentes de IA.

Detecta automáticamente vídeos de:
- YouTube (incl. youtu.be, Shorts)
- Facebook Video / Watch
- Instagram Reels / Video
- TikTok
- Archivos locales (MP4, MOV, MKV, WebM, AVI, M4V)

## Instalación

### Prerrequisitos

- Python 3.11+
- ffmpeg y ffprobe
- tesseract (para OCR)

### Instalación rápida

```bash
git clone https://github.com/aibos/video-intake-knowledge
cd video-intake-knowledge
pip install -e .
video-intake doctor
```

O con uv:

```bash
git clone https://github.com/aibos/video-intake-knowledge
cd video-intake-knowledge
uv sync
source .venv/bin/activate
video-intake doctor
```

## Comandos principales

### Detectar vídeos

```bash
video-intake inspect URL_O_ARCHIVO
```

Muestra metadatos: título, duración, resolución, codecs, subtítulos disponibles.
No descarga el vídeo.

### Extraer contenido

```bash
video-intake extract URL_O_ARCHIVO --select 1,2,3,4,5,6
```

Opciones de `--select`:
- `1` — Descargar vídeo localmente
- `2` — Descargar/extraer audio localmente
- `3` — Transcripción de audio con timestamps
- `4` — Contexto basado en audio
- `5` — Contexto visual (diagramas, flujos, interfaces, animaciones)
- `6` — Todo lo anterior
- `todo` / `todos` — Equivalente a `6`

Selecciones múltiples: `--select 1,3,5` o `--select "1 3 5"`

### Modo interactivo

```bash
video-intake extract URL_O_ARCHIVO
```

Sin `--select`, inicia modo interactivo preguntando al usuario qué extraer.

### Lotes

```bash
video-intake batch manifiesto.yaml
```

El manifiesto YAML contiene una lista de vídeos con sus configuraciones.

### Estado y gestión de jobs

```bash
video-intake status ID_DEL_JOB
video-intake cancel ID_DEL_JOB
video-intake artifacts ID_DEL_JOB
video-intake export ID_DEL_JOB --format markdown|json|html
```

### Limpieza

```bash
video-intake cleanup --max-age-days 90
video-intake cleanup --dry-run
```

### Configuración

```bash
video-intake config validate
video-intake config validate --config config/production.yaml
```

### Auto-diagnóstico

```bash
video-intake self-test
```

### Gestión de modelos

```bash
video-intake models list
video-intake models install tiny
video-intake models verify
video-intake models remove tiny
```

## Modos de extracción

### Por capas (transcripción)

1. Subtítulos originales de la fuente (si existen).
2. Subtítulos descargables (SRT, VTT, ASS, SSA, JSON3).
3. Transcripción local con Whisper/faster-whisper.
4. Modelo local configurado por el usuario.
5. Modelo externo (solo con aprobación explícita).

### Por capas (visual)

1. Metadatos, capítulos, thumbnails.
2. FFmpeg: extracción de keyframes e intervalos.
3. PySceneDetect: detección de escenas y cortes.
4. OCR local: Tesseract (o RapidOCR/PaddleOCR) sobre frames candidatos.
5. OpenCV: detección de regiones, cambios, flechas, cajas, diagramas.
6. Modelo de visión (solo si la política lo permite).

## Resultados

Cada job genera `artifacts/<job-id>/` con:

```
artifacts/<job-id>/
├── manifest.json          # Metadatos del job
├── source.json           # Información de la fuente
├── provenance.md         # Qué se hizo y con qué
├── transcript_raw/       # Transcripciones en crudo
├── transcript_timestamped.md
├── audio_context.md       # Contexto basado en audio
├── visual_context.md      # Contexto basado en visual
├── extracted_knowledge.md # Conocimiento extraído
├── frames/               # Fotogramas extraídos
├── ocr.json              # Resultados de OCR
├── logs/                 # Logs del job
└── exports/              # Exportaciones
```

## Post-extracción: qué hacer con los resultados

Tras completar la extracción, el sistema pregunta qué desea hacer:

```
[1] Aplicar como mensaje visible en la sesión actual
[2] Añadir un resumen compacto al contexto de la sesión
[3] Añadir a un banco de memoria existente
[4] Crear un nuevo banco de memoria y añadirlo
[5] Analizar qué se puede construir (tool/skill/agente/plugin/documento/workflow)
[6] Conservar únicamente los artefactos locales
[0] Cancelar / no realizar cambios adicionales
```

Reglas:
- Nunca se escribe en memoria sin selección explícita.
- Nunca se crea un banco de memoria sin confirmación.
- Nunca se crea un activo sin mostrar propuesta y pedir aprobación.

## Integración con memoria

La memoria usa una interfaz abstracta `MemoryProvider` con:

- `list_memory_banks()` — Listar bancos disponibles.
- `describe_memory_bank(id)` — Descripción de un banco.
- `add_entry(bank_id, content, source, ...)` — Añadir entrada.
- `create_memory_bank(name, description, scope, ...)` — Crear banco.
- `search(query)` — Buscar en memoria.
- `health_check()` — Verificar estado.

Para OpenCode: no hay integración nativa de memoria. Exportar a Markdown/JSON.

## Generación de activos (tools, skills, agentes, plugins)

Cuando el usuario elige "analizar qué se puede construir", el sistema:

1. Analiza el contenido extraído.
2. Produce propuestas estructuradas con:
   - Nombre propuesto
   - Tipo (tool/skill/agente/plugin/plantilla/documento/workflow/knowledge pack)
   - Objetivo
   - Evidencia del vídeo
   - Qué es fiable vs. requiere validación
   - Dependencias
   - Herramientas existentes reutilizables
   - Riesgos
   - Autonomía recomendada
   - Pruebas necesarias
   - Archivos a crear
   - Compatibilidad por host
   - Recomendación: crear / no crear / crear como borrador
   - Motivo

3. Pregunta cuál desea crear.
4. Muestra lista completa de archivos, cambios, permisos, riesgos, plan de pruebas.
5. Solo crea tras confirmación explícita.
6. Todo activo inicia como borrador, pasa pruebas y revisión humana.

Reglas:
- SKILL si el vídeo aporta procedimiento repetible, checklist, metodología,
  buenas prácticas, proceso operativo, conocimiento de dominio.
- TOOL si se necesita operación determinista, integración con API, cálculo
  validado, parser, transformación estructurada, acceso controlado a recurso.
- AGENTE solo si hay responsabilidad persistente y distinta, objetivos claros,
  herramientas específicas, límites explícitos, permisos definidos, memoria
  o estado justificado, frecuencia de uso suficiente, criterios de éxito
  verificables.
- PLUGIN solo si hace falta interceptar eventos del host, registrar hooks,
  añadir tools nativas, integrar un lifecycle específico.
- KNOWLEDGE PACK o documento si el conocimiento es útil pero no existe
  procedimiento estable para automatizar.

No duplicar activos existentes. Antes de proponer, inspectar skills/tools/plugins
existentes en el entorno.

## Seguridad

- Validación de URL (formatos, dominios permitidos).
- Protección SSRF (bloqueo de rangos privados y de metadatos de nube).
- Validación MIME (detección del tipo real del archivo descargado).
- Límites de tamaño, duración, número de vídeos por trabajo, concurrencia,
  timeouts.
- Sanitización de rutas, nombres y metadatos.
- Protección ante prompt injection en transcripciones, subtítulos, OCR,
  títulos, comentarios y descripciones.
- Cuarentena de archivos sospechosos (opcional: escaneo con ClamAV).
- Todo contenido extraído se trata como DATOS NO CONFIABLES.

Nunca implementar mecanismos para:
- Eludir DRM, paywalls, controles de edad, autenticación, anti-bot,
  restricciones geográficas.
- Descargar contenido privado sin acceso legítimo.
- Robar cookies, tokens, contraseñas o sesiones.

Si un vídeo no es accesible de forma legítima, informar del motivo y
offrecer alternativas: adjuntar archivo local, proporcionar subtítulos, usar
URL pública, configurar credenciales legítimas.

## Configuración

### Variables de entorno

Prefijo: `VITK_`

```bash
# Transcripción
export VITK_TRANSCRIPTION_LANG=es
export VITK_TRANSCRIPTION_MODEL=tiny

# Visual
export VITK_VISUAL_OCR_ENGINE=tesseract

# Seguridad
export VITK_SECURITY_STRICT_URL_VALIDATION=true
export VITK_SECURITY_SSRF_PROTECTION=true

# Storage
export VITK_STORAGE_ROOT_DIR=./artifacts
export VITK_STORAGE_ARTIFACT_RETENTION_DAYS=90
export VITK_STORAGE_MAX_STORAGE_GB=100

# Limits
export VITK_LIMITS_MAX_VIDEO_DURATION_MINUTES=600
export VITK_LIMITS_MAX_DOWNLOAD_SIZE_MB=5000
export VITK_LIMITS_MAX_BATCH_ITEMS=50
export VITK_LIMITS_MAX_PARALLEL_JOBS=4
export VITK_LIMITS_TIMEOUT_SECONDS=3600

# Acquisition
export VITK_ACQUISITION_CAPTIONS_FIRST=true
export VITK_ACQUISITION_CACHE_ENABLED=true

# Memory
export VITK_MEMORY_ENABLED=true
export VITK_MEMORY_REQUIRE_CONFIRMATION=true

# Host
export VITK_HOST_TYPE=opencode
```

### Archivos de configuración

`config/default.yaml` — Valor por defecto (balanceado).
`config/offline.yaml` — Sin descargas remotas, solo local.
`config/low-cost.yaml` — Sin modelos externos, Whisper tiny + Tesseract.
`config/production.yaml` — Políticas estrictas, retención, escaneo.

Precedencia: argumentos CLI > variables de entorno > archivo config > default.yaml

## Ejemplos

### Ejemplo 1: Archivo local

```bash
# Inspeccionar
video-intake inspect mi_video.mp4

# Extraer todo
video-intake extract mi_video.mp4 --select 6

# Ver resultados
video-intake artifacts <job-id>
video-intake export <job-id> --format markdown

# Limpiar después de usar
video-intake cleanup --max-age-days 7
```

### Ejemplo 2: URL pública de YouTube

```bash
# Inspeccionar primero
video-intake inspect https://www.youtube.com/watch?v=dQw4w9WgXcQ

# Extraer solo transcripción y contexto de audio
video-intake extract https://www.youtube.com/watch?v=dQw4w9WgXcQ \
    --select 3,4

# Extraer transcripción y contexto visual
video-intake extract https://www.youtube.com/watch?v=dQw4w9WgXcQ \
    --select 3,5
```

### Ejemplo 3: Lote

```bash
video-intake batch manifest.yaml
```

### Ejemplo 4: Extracción visual

```bash
video-intake extract presentacion.mp4 --select 5

# Esto extrae:
# - Keyframes de las escenas
# - OCR del texto en pantalla
# - Detección de cambios de escena
# - Diagramas y flujos inferidos
# - Contexto visual estructurado
```

### Ejemplo 5: Memoria (exportación manual)

```bash
video-intake extract charlas.mp4 --select 3,4

# Tras la extracción, exportar resultados para importación manual
video-intake export <job-id> --format markdown
# El resultado se guarda en artifacts/<job-id>/exports/
```

### Ejemplo 6: Propuesta para crear una skill

```bash
video-intake extract tutorial.mp4 --select 3,4

# Tras la extracción, elige "5" para analizar qué se puede construir
# El sistema muestra propuestas de tools/skills/agentes/plugins
# Eliges una y se crea como borrador tras confirmación
```

## Dependencias del sistema

| Dependencia | Versión mínima | Uso |
|-------------|----------------|-----|
| Python | 3.11 | Lenguaje principal |
| ffmpeg | 4.x | Extracción de audio, keyframes |
| ffprobe | (incluido con ffmpeg) | Inspección de metadatos |
| tesseract | 4.x | OCR de frames |
| yt-dlp | (recomendado) | Descarga de vídeos remotos |

## Modelos opcionales

| Modelo | Tamaño | Idiomas | Uso | Offline |
|--------|--------|---------|-----|---------|
| whisper-tiny | ~75 MB | multi | Transcripción rápida | Sí |
| whisper-base | ~140 MB | multi | Transcripción equilibrada | Sí |
| whisper-small | ~480 MB | multi | Transcripción precisa | Sí |
| whisper-medium | ~1.5 GB | multi | Alta precisión | Sí |
| whisper-large | ~3 GB | multi | Máxima precisión | Sí |
| faster-whisper | (same models) | multi | Alternativa rápida | Sí |
| whisper.cpp | (same models) | multi | Alternativa ligera | Sí |
| Tesseract | (sys) | 100+ idiomas | OCR de frames | Sí |
| RapidOCR | (pip) | multi | OCR alternativo | Sí |
| PaddleOCR | (pip) | multi | OCR alternativo | Sí |

La instalación básica NO descarga modelos automáticamente.
Para instalar modelos: `video-intake models install tiny`

## Límite de recursos

- Máximo vídeo: 600 minutos (configurable).
- Máximo descarga: 5000 MB (configurable).
- Máximo batch: 50 vídeos (configurable).
- Máximo paralelo: 4 jobs (configurable).
- Timeout: 3600 segundos (configurable).

## Actualización

```bash
cd video-intake-knowledge
git pull
pip install -e . --upgrade
video-intake doctor
```

## Desinstalación

```bash
pip uninstall video-intake-core
rm -rf artifacts/
rm -f memory.db
```

## Solución de problemas

### `video-intake: command not found`

Activa el entorno virtual o añade a PATH:
```bash
source .venv/bin/activate
# o
export PATH="$HOME/.local/bin:$PATH"
```

### `ffmpeg: command not found`

```bash
# Linux
sudo apt-get install ffmpeg
# macOS
brew install ffmpeg
```

### `tesseract: command not found`

```bash
# Linux
sudo apt-get install tesseract-ocr libtesseract-dev
# macOS
brew install tesseract
```

### Modelo no encontrado

```bash
video-intake models list
video-intake models install tiny
```

### Error de transcripción

- Verifica que el vídeo tiene audio.
- Prueba con un modelo diferente (`--model base`).
- Verifica que hay espacio en disco.

### URL no funciona

- Verifica que la URL es correcta.
- El vídeo puede ser privado o eliminado.
- yt-dlp puede necesitar actualización: `pip install -U yt-dlp`

### OCR no detecta texto

- El frame puede no tener texto legible.
- Prueba con frames de otra parte del vídeo.
- Ajusta el preprocesado (umbral, escala de grises).
- Para diagramas complejos, el OCR puede no ser suficiente.

## Enlaces útiles

- Repositorio: https://github.com/aibos/video-intake-knowledge
- Issues: https://github.com/aibos/video-intake-knowledge/issues
- Documentación: docs/architecture.md, docs/installation.md,
  docs/configuration.md, docs/security-model.md,
  docs/supported-sources.md, docs/portability.md,
  docs/memory-integration.md, docs/asset-generation.md,
  docs/troubleshooting.md, docs/development.md

## Licencia

MIT License. Ver LICENSE.
