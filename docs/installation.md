# Instalación de video-intake-knowledge

## Requisitos del sistema

- **Python:** 3.11 o superior
- **Sistema operativo:** Linux, macOS o Windows (con WSL recomendado)
- **Dependencias de sistema:** ffmpeg, tesseract (para OCR)

## Instalación rápida (local)

### 1. Clonar el repositorio

```bash
git clone https://github.com/aibos/video-intake-knowledge.git
cd video-intake-knowledge
```

### 2. Instalar dependencias del sistema

```bash
# Linux (Debian/Ubuntu)
sudo apt-get update
sudo apt-get install -y ffmpeg tesseract-ocr libtesseract-dev

# macOS (con Homebrew)
brew install ffmpeg tesseract

# Windows (WSL o manual)
# ffmpeg: https://ffmpeg.org/download.html
# tesseract: https://github.com/UB-Mannheim/tesseract/wiki
```

### 3. Instalar el paquete

```bash
# Con uv (recomendado)
uv sync

# O con pip
pip install -e .
```

### 4. Verificar la instalación

```bash
video-intake doctor
```

Si la instalación fue correcta, verás un informe con todas las dependencias OK.

### 5. Efecto

```bash
# Ver la ayuda
video-intake --help

# Probar con un archivo local
video-intake inspect /ruta/a/video.mp4

# Extraer transcripción de un vídeo
video-intake extract /ruta/a/video.mp4 --select transcript
```

## Instalación con modelos de transcripción locales

### Whisper (recomendado)

```bash
# Instala faster-whisper
pip install faster-whisper

# El primer uso descargará el modelo automáticamente
# Para instalar un modelo explícitamente:
video-intake models install tiny  # ~75 MB
video-intake models install base  # ~140 MB
video-intake models install small  # ~480 MB
video-intake models install medium  # ~1.5 GB
video-intake models install large  # ~3 GB

# Verifica modelos instalados
video-intake models list
```

### whisper.cpp (alternativa ligera)

```bash
# Instala whisper.cpp
git clone https://github.com/ggerganov/whisper.cpp
cd whisper.cpp
make

# Descarga un modelo
./models/download-ggml-model.sh tiny

# video-intake detectará whisper.cpp si está en PATH
```

## Instalación en Hermes Agent

### Automática (si Hermes soporta descubrimiento de plugins)

```bash
cd video-intake-knowledge
cp -r adapters/hermes ~/.hermes/plugins/video-intake-knowledge/
```

Luego reinicia Hermes o recarga plugins. El plugin se registrará automáticamente.

### Manual

1. Añade a tu `config.yaml` de Hermes:

```yaml
plugins:
  - video-intake-knowledge

tools:
  - video_intake_inspect_source
  - video_intake_create_job
  - video_intake_get_job_status
  - video_intake_cancel_job
  - video_intake_get_artifacts
  - video_intake_extract_transcript
  - video_intake_extract_audio_context
  - video_intake_extract_visual_context
  - video_intake_list_memory_banks
  - video_intake_store_memory
  - video_intake_create_memory_bank
  - video_intake_analyze_build_options
  - video_intake_generate_asset_draft
```

2. Asegúrate de que el script `standalone_hermes.sh` tenga permisos de ejecución:

```bash
chmod +x scripts/standalone_hermes.sh
```

3. Usa los comandos manuales en tu sesión Hermes:

```
/video inspect URL_O_RUTA
/video extract URL_O_RUTA --select transcript
/video status ID_DEL_JOB
/video cancel ID_DEL_JOB
/video artifacts ID_DEL_JOB
/video doctor
```

### Desinstalación de Hermes

```bash
rm -rf ~/.hermes/plugins/video-intake-knowledge/
# Removes registered tools from config.yaml
```

## Instalación en otros hosts

Cada host tiene su propio adaptador en `adapters/<host>/`.

### OpenCode

```bash
cd video-intake-knowledge
cp adapters/opencode/SKILL.md ~/.opencode/skills/video-intake-knowledge/SKILL.md
```

Consulta `adapters/opencode/README.md` para el flujo completo.

### Claude Code

```bash
cd video-intake-knowledge
cp adapters/claude-code/SKILL.md ~/.claude/skills/video-intake-knowledge/SKILL.md
```

Consulta `adapters/claude-code/README.md` para el flujo completo.

### Codex

```bash
cd video-intake-knowledge
cp adapters/codex/SKILL.md ~/.codex/skills/video-intake-knowledge/SKILL.md
```

Consulta `adapters/codex/README.md` para el flujo completo.

### AGY

Consulta `adapters/agy/README.md` para el flujo específico de AGY.

### Genérico (sin agente)

Si no usas ningún agente, la CLI es todo lo que necesitas:

```bash
# La CLI funciona directamente tras la instalación
video-intake doctor
video-intake inspect archivo.mp4
video-intake extract archivo.mp4 --select transcript,audio
```

## Configuración

### Archivo de configuración

Por defecto, el sistema lee `config/default.yaml`. Puedes especificar otro archivo
con la opción `--config` o la variable `VITK_CONFIG_PATH`.

```bash
video-intake extract archivo.mp4 --config config/low-cost.yaml --select transcript
```

### Variables de entorno

Cada opción de configuración tiene una variable de entorno correspondiente con
prefijo `VITK_`:

```bash
export VITK_TRANSCRIPTION_LANG=es
export VITK_MODEL_PRIORITY_TRANSCRIPT=local
export VITK_SECURITY_STRICT_URL_VALIDATION=true
```

La precedencia es: argumentos CLI > variables de entorno > archivo de config > default.yaml.

### Perfiles de instalación

| Perfil        | Qué instala                                                    |
|---------------|---------------------------------------------------------------|
| `core`        | Solo el núcleo, sin modelos ni herramientas opcionales.       |
| `local-transcription` | Núcleo + Whisper/faster-whisper.                        |
| `local-ocr`   | Núcleo + Tesseract + OpenCV para OCR.                         |
| `visual-analysis` | Núcleo + OCR + PySceneDetect + OpenCV para análisis visual.|
| `full`        | Todo lo anterior.                                              |
| `hermes`      | Núcleo + adaptador Hermes.                                    |
| `development` | Núcleo + herramientas de desarrollo (tests, lint, docs).     |

## Actualización

```bash
# Pull de nueva versión
cd video-intake-knowledge
git pull

# Actualizar dependencias
uv sync

# Verificar que todo sigue funcionando
video-intake doctor
```

## Desinstalación

```bash
# Desinstalar el paquete
pip uninstall video-intake-core

# Eliminar artefactos (si deseas)
rm -rf artifacts/

# Eliminar banco de memoria local (si lo usaste)
rm -f video_intake_memory.db

# En Hermes
rm -rf ~/.hermes/plugins/video-intake-knowledge/
```

## Troubleshooting

### "video-intake: command not found"

```bash
# Asegúrate de que el entorno virtual esté activado
source .venv/bin/activate  # o el que usaste

# O añade el directorio a tu PATH
export PATH="$HOME/.local/bin:$PATH"
```

### "ffmpeg no encontrado"

```bash
# Instala ffmpeg
sudo apt-get install ffmpeg  # Debian/Ubuntu
brew install ffmpeg         # macOS
```

### "tesseract no encontrado"

```bash
# Instala tesseract
sudo apt-get install tesseract-ocr libtesseract-dev  # Debian/Ubuntu
brew install tesseract                                 # macOS
```

Para más solución de problemas, ver `docs/troubleshooting.md`.
