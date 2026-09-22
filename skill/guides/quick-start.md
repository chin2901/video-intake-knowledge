# Quick Start — Guía de inicio rápido para video-intake-knowledge

Esta guía te lleva de cero a extraer conocimiento de un vídeo en menos de
5 minutos.

---

## 1. Instalación

### Opción A — Instalación rápida con pip

```bash
pip install video-intake-knowledge
```

### Opción B — Instalación desde el repositorio

```bash
git clone https://github.com/aibos/video-intake-knowledge.git
cd video-intake-knowledge
pip install -e .
```

### Opción C — Con uv (recomendado para desarrollo)

```bash
uv pip install video-intake-knowledge
```

### Deps del sistema

Antes de usar el sistema, instala las dependencias del sistema:

```bash
bash scripts/install-system-deps.sh
```

Esto instalará ffmpeg, tesseract-ocr y otras herramientas necesarias.

---

## 2. Verificar la instalación

Ejecuta el comando doctor para verificar que todo está configurado:

```bash
video-intake doctor
```

Deberías ver una salida similar a:

```
✓ ffmpeg encontrado
✓ ffprobe encontrado
✓ yt-dlp encontrado
✓ tesseract encontrado
✓ Python 3.9+OK
...

Estado del entorno: HEALTHY
```

---

## 3. Extraer un vídeo de YouTube

El caso de uso más simple:extraer todo el conocimiento de un vídeo.

```bash
video-intake extract https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

El sistema iniciará un menú interactivo:

```
╔══════════════════════════════════════════════════════════╗
║  He detectado 1 vídeo.                                   ║
║                                                           ║
║  ¿Qué deseas extraer?                                     ║
║                                                           ║
║  [1] Descargar vídeo localmente                          ║
║  [2] Descargar audio localmente                          ║
║  [3] Transcripción de audio con timestamps                ║
║  [4] Extraer contexto basado en audio                     ║
║  [5] Extraer contexto visual (diagramas, flujos, etc.)   ║
║  [6] Todo el anterior                                     ║
║  [0] Cancelar                                             ║
║                                                           ║
║  Puedes responder: 1,3,5; todos; o configurar individualmente. ║
╚══════════════════════════════════════════════════════════╝
```

Elige una opción (ej. "6" para todo) y el sistema iniciará la extracción.

---

## 4. Selección de operaciones

El sistema acepta varias formas de selección:

- **Individual**: `1` — solo descargar vídeo
- **Múltiple con comas**: `1,3,5` — descargar, transcribir, contexto visual
- **Múltiple con espacios**: `1 3 5` — mismo efecto
- **Todo**: `todo`, `todos`, `6` — todas las operaciones
- **Cancelar**: `0`, `cancelar` — abortar

---

## 5. Resultados

Los resultados se guardan en:

```
data/jobs/<job_id>/
├── video/
│   └── video.mp4
├── audio/
│   └── audio.wav
├── transcript/
│   └── transcript.json
├── context/
│   ├── audio_context.json
│   └── visual_context.json
└── manifest.json
```

---

## 6. Ver resultados

Para ver los artefactos generados:

```bash
video-intake artifacts
```

Para exportar los resultados en un formato específico:

```bash
video-intake export <job_id> --format mdx
video-intake export <job_id> --format markdown
video-intake export <job_id> --format json
```

---

## 7. Procesamiento por lotes (Batch)

Para procesar múltiples vídeos a la vez, crea un archivo con una URL
por línea:

```
# urls.txt
https://www.youtube.com/watch?v=dQw4w9WgXcQ
https://www.youtube.com/watch?v=jNQXAC9IVRw
https://www.tiktok.com/@user/video/123456789
```

Luego ejecuta:

```bash
video-intake batch urls.txt
```

El sistema preguntará si quieres aplicar la misma selección a todos
los vídeos o configurar cada uno individualmente.

---

## 8. Vídeos locales

Puedes procesar archivos de vídeo locales directamente:

```bash
video-intake extract /ruta/a/mi-video.mp4
```

Se soportan los formatos: MP4, MOV, MKV, WebM, AVI, M4V.

---

## 9. Configuración personalizada

El sistema se puede configurar mediante archivos YAML. Las opciones
incluyen:

- Estrategia de transcripción (captions, whisper, auto)
- Modelo Whisper a usar (tiny, base, small, medium, large)
- Idioma de transcripción
- Generación de contexto de audio y visual
- Almacenamiento y retención de artefacts
- Protección de seguridad (SSRF, MIME, prompt injection)
- Sistema de memoria para conocimiento extraído

Ver `config/default.yaml` para la configuración completa y
`config/low-cost.yaml` para una configuración mínima.

Para usar una configuración específica:

```bash
video-intake extract <url> --config config/low-cost.yaml
```

---

## 10. Integración con Hermes Agent

Para usar video-intake-knowledge desde Hermes Agent:

1. Instala el paquete:
   ```bash
   pip install video-intake-knowledge
   ```

2. Registra el plugin de Hermes:
   ```bash
   bash adapters/hermes/install.sh
   ```

3. Reinicia Hermes Agent.

Las herramientas de video-intake-knowledge estarán disponibles para
el asistente en las conversaciones.

El sistema detectará automáticamente vídeos en los mensajes del usuario
y ofrecerá las opciones de extracción.

---

## 11. Integración con otros agentes

El sistema es compatible con cualquier entorno que soporte SKILL.md:

- **Claude Code**: usar `adapters/claude-code/SKILL.md`
- **OpenCode**: usar `adapters/opencode/SKILL.md`
- **Codex**: usar `adapters/codex/SKILL.md`
- **AGY**: usar `adapters/agy/SKILL.md`

Cada adaptador incluye un SKILL.md portable y scripts de instalación.

---

## 12. Próximos pasos

- Explorar la documentación en `docs/` para conocer todas las capacidades
- Revisar la arquitectura en `docs/architecture.md`
- Configurar políticas personalizadas en `config/`
- Integrar con tu flujo de trabajo de agentes de IA
- Consultar `docs/troubleshooting.md` si encuentras problemas
