# Video Intake Knowledge

Sistema completo de extracción de contenido audiovisual: transcripción, contexto de audio, contexto visual, elementos OCR, detección de escenas, extracción de keyframes y generación de conocimiento estructurado a partir de vídeos de YouTube, Facebook, Instagram, TikTok y archivos locales.

## Requisitos

- Python 3.11+
- `uv` (gestión de dependencias)
- `ffmpeg` / `ffprobe` (procesado de vídeo/audio)
- `yt-dlp` (descarga de vídeos de plataformas)
- `tesseract` (OCR, opcional)
- `openai-whisper` (transcripción local, opcional)

## Instalación rápida

```bash
cd video-intake-knowledge
uv sync --extra core
```

Para transcripción local:
```bash
uv sync --extra local-transcription
```

Para análisis visual completo:
```bash
uv sync --extra full
```

## Uso rápido con la CLI

```bash
# Inspeccionar un vídeo sin descargarlo
video-intake inspect https://www.youtube.com/watch?v=VIDEO_ID

# Extraer transcripción y contexto de audio desde un vídeo
video-intake extract https://www.youtube.com/watch?v=VIDEO_ID \
  --select transcript,audio-context

# Extraer todo desde un vídeo local
video-intake extract ./mi-video.mp4 --select video,audio,transcript,audio-context,visual-context

# Procesar varios vídeos desde un manifiesto
video-intake batch videos.yaml
```

## Integración con Hermes Agent

Instala el plugin nativo:

```bash
cp -r adapters/hermes/plugin ~/.hermes/plugins/video-intake-knowledge/
hermes plugins enable video-intake-knowledge
```

El plugin registra herramientas automáticamente y agrega comandos slash (`/video`).

## Integración con otros agentes

Cada adaptador incluye un `SKILL.md` y un script de instalación:

```bash
# AGY
cp -r adapters/agy ~/.agy/skills/video-intake-knowledge

# OpenCode
cp -r adapters/opencode ~/.opencode/skills/video-intake-knowledge

# Claude Code
cp -r adapters/claude-code ~/.claude/skills/video-intake-knowledge

# Codex
cp -r adapters/codex ~/.codex/skills/video-intake-knowledge
```

## Estructura del proyecto

```
video-intake-knowledge/
├── pyproject.toml          # Dependencias y configuración del paquete
├── packages/
│   └── video_intake_core/  # Núcleo portable (Python)
│       ├── acquisition/    # Detección y descarga de fuentes
│       ├── inspection/     # Inspección de metadatos (ffprobe)
│       ├── audio/          # Extracción y normalización de audio
│       ├── transcription/  # Transcripción (whisper + subtítulos)
│       ├── visual/         # Detección de escenas y keyframes
│       ├── ocr/            # Reconocimiento óptico de caracteres
│       ├── context/        # Generación de contexto de audio/visual
│       ├── artifacts/      # Generación de artefactos de salida
│       ├── jobs/           # Gestión de trabajos y estado
│       ├── storage/        # Almacenamiento de artefactos
│       ├── schemas/        # Definiciones JSON Schema
│       ├── policies/       # Políticas de modelos y procesamiento
│       ├── security/       # Validación de URLs y sanitización
│       ├── memory/         # Abstracción de providers de memoria
│       ├── cli/            # CLI completa (video-intake)
│       └── utils/          # Utilidades compartidas
├── skill/                  # Skill portable para agentes
│   ├── SKILL.md
│   ├── scripts/
│   ├── templates/
│   ├── references/
│   └── assets/
├── adapters/               # Adaptadores para entornos de agentes
│   ├── hermes/             # Plugin nativo para Hermes Agent
│   ├── agy/                # Skill para AGY
│   ├── opencode/           # Skill para OpenCode
│   ├── claude-code/        # Skill para Claude Code
│   ├── codex/              # Skill para Codex
│   └── generic-agent-skills/  # Formato portable genérico
├── scripts/                # Scripts de instalación y utilidad
├── config/                 # Archivos de configuración de ejemplo
├── tests/                  # Pruebas unitarias, integración, e2e
├── docs/                   # Documentación y ADRs
├── .github/workflows/     # CI/CD con GitHub Actions
└── examples/               # Ejemplos de uso
```

## Licencia

MIT
