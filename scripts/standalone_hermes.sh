#!/bin/bash
# =============================================================================
# standalone_hermes.sh — CLI standalone para integración con Hermes Agent
# =============================================================================
#
# Este script permite que Hermes Agent use video-intake-knowledge como una
# herramienta CLI externa sin necesidad de integración en Python.
#
# Uso desde Hermes Agent:
#   !/home/aibos/video-intake-knowledge/scripts/standalone_hermes.sh detectar URL
#   !/home/aibos/video-intake-knowledge/scripts/standalone_hermes.sh extraer URL --select transcript,audio
#   !/home/aibos/video-intake-knowledge/scripts/standalone_hermes.sh menu URL1 URL2
#
# Opciones:
#   detectar <URL|PATH>       Detecta si es un video procesable
#   inspect <URL|PATH>        Muestra metadatos del video
#   extraer <URL|PATH> [opciones]
#   menu [URL|PATH...]        Modo interactivo
#   list                       Lista jobs pendientes
#   status <JOB_ID>           Estado de un job
#
# Para activar en Hermes Agent, añadir a config.yaml:
#   tools:
#     - name: video-intake
#       command: /ruta/a/standalone_hermes.sh
#       description: Extrae contenido de videos (YouTube, Facebook, etc.)
#
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV="$ROOT_DIR/.venv"

usage() {
    cat << 'USAGE'
Uso: standalone_hermes.sh <comando> [args...]

Comandos:
  detectar <URL|PATH>       Detecta si es un video procesable
  inspect <URL|PATH>        Muestra metadatos (duración, resolución, etc.)
  extraer <URL|PATH>        Extrae contenido según opciones
  menu [URL|PATH...]        Modo interactivo
  list                      Lista jobs pendientes
  status <JOB_ID>           Estado de un job
  help                      Esta ayuda

Opciones de extraer:
  --select STR    Qué extraer: transcript, audio, audio-context,
                  visual-context, frames, ocr, todo, todas
  --lang LANG     Idioma de transcripción (default: es)
  --model MODEL   Modelo Whisper (default: tiny)
  --out DIR       Directorio de salida
  --yes           No preguntar confirmación
  --force         Sobrescribir si existe

Ejemplos:
  standalone_hermes.sh detectar "https://www.youtube.com/watch?v=abc123"
  standalone_hermes.sh extraer "https://www.youtube.com/watch?v=abc123" \
      --select transcript,audio --lang es --out ./artifacts
  standalone_hermes.sh menu "https://www.youtube.com/watch?v=abc123" \
      "/ruta/a/video.mp4"
USAGE
    exit 0
}

log_error() {
    echo "[ERROR] $*" >&2
}

log_info() {
    echo "[INFO] $*"
}

log_warn() {
    echo "[WARN] $*"
}

# ------------------------------------------------------------------
# Check environment
# ------------------------------------------------------------------
check_env() {
    if [[ ! -d "$VENV" ]]; then
        log_error "Entorno virtual no encontrado: $VENV"
        log_error "Ejecuta primero: bash scripts/bootstrap.sh"
        exit 1
    fi
}

# ------------------------------------------------------------------
# detectar — Detecta si una URL o archivo es un video procesable
# ------------------------------------------------------------------
cmd_detectar() {
    local target="${1:?Requiere URL o ruta}"

    check_env

    source "$VENV/bin/activate"
    python3 -c "
import sys
sys.path.insert(0, '$ROOT_DIR/packages')
from video_intake_core.acquisition import detect_video_sources

sources = detect_video_sources('$target')
if sources:
    print('PROCESABLE')
    for s in sources:
        print(f\"  tipo: {s['type']}\")
        print(f\"  url: {s['resolved_url']}\")
        print(f\"  title: {s.get('title', 'N/A')}\")
        print(f\"  platform: {s.get('platform', 'local')}\")
else:
    print('NO_PROCESABLE')
    print('Este contenido no parece ser un video compatible.')
" 2>&1
    deactivate
}

# ------------------------------------------------------------------
# inspect — Muestra metadatos del video
# ------------------------------------------------------------------
cmd_inspect() {
    local target="${1:?Requiere URL o ruta}"

    check_env

    source "$VENV/bin/activate"
    python3 -c "
import sys
sys.path.insert(0, '$ROOT_DIR/packages')
from video_intake_core.inspection import inspect_video

info = inspect_video('$target')
if info:
    print(f\"Título: {info.get('title', 'N/A')}\")
    print(f\"Plataforma: {info.get('platform', 'local')}\")
    print(f\"Duración: {info.get('duration_secs', 0):.1f}s\")
    print(f\"Duración (formato): {info.get('duration', 'N/A')}\")
    if info.get('width') and info.get('height'):
        print(f\"Resolución: {info['width']}x{info['height']}\")
    if info.get('fps'):
        print(f\"FPS: {info['fps']}\")
    if info.get('video_codec'):
        print(f\"Codec video: {info['video_codec']}\")
    if info.get('audio_codec'):
        print(f\"Codec audio: {info['audio_codec']}\")
    if info.get('audio_channels'):
        print(f\"Canales audio: {info['audio_channels']}\")
    if info.get('streams'):
        print(f\"Streams: {len(info['streams'])}\")
    print(f\"URL: {info.get('url', 'N/A')}\")
else:
    print('No se pudieron obtener metadatos.')
" 2>&1
    deactivate
}

# ------------------------------------------------------------------
# extraer — Extrae contenido del video
# ------------------------------------------------------------------
cmd_extraer() {
    local target="${1:?Requiere URL o ruta}"
    local select="todo"
    local lang="es"
    local model="tiny"
    local out_dir=""
    local yes=false
    local force=false

    shift
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --select)  select="$2";      shift 2 ;;
            --lang)    lang="$2";        shift 2 ;;
            --model)   model="$2";       shift 2 ;;
            --out)     out_dir="$2";     shift 2 ;;
            --yes)     yes=true;         shift ;;
            --force)   force=true;       shift ;;
            --help|-h) usage ;;
            *)         log_error "Opción desconocida: $1"; exit 1 ;;
        esac
    done

    check_env

    source "$VENV/bin/activate"
    python3 -c "
import sys
sys.path.insert(0, '$ROOT_DIR/packages')

from video_intake_core.acquisition import detect_video_sources
from video_intake_core.jobs import create_job
from video_intake_core.artifacts import ArtifactManager
from video_intake_core.memory import create_memory_provider

source = detect_video_sources('$target')
if not source:
    print('ERROR: No se detectó contenido de video procesable')
    sys.exit(1)

src = source[0]
print(f'Procesando: {src.get(\"title\", \"N/A\")}')
print(f'Plataforma: {src.get(\"platform\", \"local\")}')

job = create_job(
    source_url=src['resolved_url'],
    source_title=src.get('title', ''),
    source_type=src['type'],
)

print(f'Job ID: {job.id}')

# Aquí se integraría la lógica completa de extracción
# Por ahora, confirmamos que el pipeline está disponible
print('Pipeline de extracción disponible.')
print(f'Selección: {select}')
print(f'Idioma: {lang}')
print(f'Modelo: {model}')

sys.exit(0)
" 2>&1
    deactivate
}

# ------------------------------------------------------------------
# menu — Modo interactivo
# ------------------------------------------------------------------
cmd_menu() {
    check_env

    source "$VENV/bin/activate"
    python3 -c "
import sys
sys.path.insert(0, '$ROOT_DIR/packages')

from video_intake_core.acquisition import detect_video_sources

targets = sys.argv[1:]
if not targets:
    print('Proporciona al menos una URL o ruta.')
    sys.exit(1)

sources = []
for t in targets:
    found = detect_video_sources(t)
    if found:
        sources.extend(found)

if not sources:
    print('No se detectaron videos procesables.')
    sys.exit(1)

print(f'He detectado {len(sources)} vídeo(s) procesable(s).')
print()
print('¿Deseas aplicar la misma extracción a todos o configurarlos individualmente?')
print()
print('[1] Aplicar la misma selección a todos')
print('[2] Configurar cada vídeo individualmente')
print('[0] Cancelar')
print()

selection = input('Tu selección: ').strip()

if selection == '1':
    print()
    print('¿Qué deseas extraer?')
    print()
    print('[1] Descargar el vídeo de forma local')
    print('[2] Descargar o extraer el audio de forma local')
    print('[3] Obtener transcripción de audio con timestamps')
    print('[4] Extraer contexto basado en el audio')
    print('[5] Extraer contexto visual')
    print('[6] Extraer todo')
    print('[0] Cancelar')
    print()
    extract = input('Tu selección: ').strip()
    print(f' extracción seleccionada: {extract}')
elif selection == '2':
    for i, src in enumerate(sources, 1):
        print()
        print(f'--- Vídeo {i}: {src.get(\"title\", \"N/A\")} ---')
        print()
        print('¿Qué deseas extraer?')
        print('[1] Descargar vídeo  [2] Audio  [3] Transcripción  [4] Contexto audio')
        print('[5] Contexto visual  [6] Todo    [0] Cancelar')
        print()
        resp = input('Tu selección: ').strip()
        print(f'  → {resp}')
elif selection == '0':
    print('Operación cancelada.')
else:
    print('Selección no válida.')
" 2>&1
    deactivate
}

# ------------------------------------------------------------------
# list — Lista jobs
# ------------------------------------------------------------------
cmd_list() {
    check_env

    source "$VENV/bin/activate"
    python3 -c "
import sys
sys.path.insert(0, '$ROOT_DIR/packages')
from video_intake_core.jobs import list_jobs, JobStatus

jobs = list_jobs(status=JobStatus.PENDING.value)
print(f'Jobs pendientes: {len(jobs)}')
for j in jobs[:20]:
    print(f'  {j.id}  {j.source_title[:60]}  {j.status.value}')
if len(jobs) > 20:
    print(f'  ... y {len(jobs) - 20} más')
" 2>&1
    deactivate
}

# ------------------------------------------------------------------
# status — Muestra estado de un job
# ------------------------------------------------------------------
cmd_status() {
    local job_id="${1:?Requiere JOB_ID}"

    check_env

    source "$VENV/bin/activate"
    python3 -c "
import sys
sys.path.insert(0, '$ROOT_DIR/packages')
from video_intake_core.jobs import get_job

job = get_job('$job_id')
if job:
    print(f'Job: {job.id}')
    print(f'Estado: {job.status.value}')
    print(f'Título: {job.source_title}')
    print(f'URL: {job.source_url}')
    print(f'Tipo: {job.source_type}')
    print(f'Creado: {job.created_at}')
    if job.result_metadata:
        print(f'Resultado: {job.result_metadata}')
else:
    print(f'Job no encontrado: $job_id')
" 2>&1
    deactivate
}

# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
main() {
    if [[ $# -eq 0 ]]; then
        usage
    fi

    local cmd="$1"
    shift

    case "$cmd" in
        detectar)  cmd_detectar "$@" ;;
        inspect)   cmd_inspect "$@" ;;
        extraer)   cmd_extraer "$@" ;;
        menu)      cmd_menu "$@" ;;
        list)      cmd_list "$@" ;;
        status)    cmd_status "$@" ;;
        help|-h|--help) usage ;;
        *)         log_error "Comando desconocido: $cmd"; usage ;;
    esac
}

main "$@"
