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

if [[ -n "${VIRTUAL_ENV:-}" && -d "$VIRTUAL_ENV" ]]; then
    VENV="$VIRTUAL_ENV"
elif [[ -d "$ROOT_DIR/venv" ]]; then
    VENV="$ROOT_DIR/venv"
elif [[ -d "$ROOT_DIR/.venv" ]]; then
    VENV="$ROOT_DIR/.venv"
else
    VENV="$ROOT_DIR/venv"
fi

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
        st = getattr(s, 'source_type', 'local')
        url = getattr(s, 'resolved_path', None) or getattr(s, 'url', '$target')
        title = getattr(s, 'title', None) or 'N/A'
        print(f\"  tipo: {st}\")
        print(f\"  url: {url}\")
        print(f\"  title: {title}\")
        print(f\"  platform: {st}\")
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
    title = getattr(info, 'title', '') or 'N/A'
    platform = getattr(info, 'extractor', '') or 'local'
    dur = getattr(info, 'duration', 0.0)
    dur_str = getattr(info, 'duration_string', '') or 'N/A'
    url = getattr(info, 'url', '$target')
    print(f\"Título: {title}\")
    print(f\"Plataforma: {platform}\")
    print(f\"Duración: {float(dur):.1f}s\")
    print(f\"Duración (formato): {dur_str}\")
    print(f\"URL: {url}\")
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
from pathlib import Path
sys.path.insert(0, '$ROOT_DIR/packages')

from video_intake_core.acquisition import detect_video_sources
from video_intake_core.orchestrator import check_and_extract, parse_extraction_choices

source = detect_video_sources('$target')
if not source:
    print('ERROR: No se detectó contenido de video procesable')
    sys.exit(1)

src = source[0]
st = getattr(src, 'source_type', 'local')
src_dict = [{
    'type': st,
    'original_input': '$target',
    'resolved_url': getattr(src, 'resolved_path', None) or getattr(src, 'url', '$target'),
    'platform': str(st),
    'title': getattr(src, 'title', None) or Path('$target').stem,
    'is_local': st == 'local',
}]
ops = parse_extraction_choices('$select')
out = Path('$out_dir' if '$out_dir' else './artifacts')
artifacts = check_and_extract(src_dict, ops, out)
print(f\"Job completado: {artifacts.get('job_id')}\")
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
    st = getattr(j.status, 'value', str(j.status))
    print(f'  {j.id}  {j.source_title[:60]}  {st}')
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
    st = getattr(job.status, 'value', str(job.status))
    print(f'Job: {job.id}')
    print(f'Estado: {st}')
    print(f'Título: {job.source_title}')
    print(f'URL: {job.source_url}')
    print(f'Tipo: {job.source_type}')
    print(f'Creado: {job.created_at}')
    if job.result_metadata:
        print(f'Resultado: {job.result_metadata}')
else:
    print('Job no encontrado: $job_id')
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
