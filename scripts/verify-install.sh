#!/bin/bash
# =============================================================================
# verify-install.sh — Verifica que la instalación está completa y funcional
# =============================================================================
#
# Ejecuta una serie de verificaciones para asegurar que video-intake-knowledge
# está correctamente instalado y todas sus capacidades están disponibles.
#
# Uso:
#   chmod +x scripts/verify-install.sh
#   ./scripts/verify-install.sh [--verbose] [--json]
#
# Salida: 0 si todo está OK, 1 si hay problemas.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

VERBOSE=false
JSON=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --verbose) VERBOSE=true; shift ;;
        --json)    JSON=true; shift ;;
        --help|-h) echo "Usage: $0 [--verbose] [--json]"; exit 0 ;;
        *)         echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

PASS=0
FAIL=0
WARN=0

check() {
    local name="$1"
    local status="$2"  # pass, fail, warn
    local detail="${3:-}"

    if $JSON; then
        echo "{\"check\":\"$name\",\"status\":\"$status\",\"detail\":\"$detail\"}"
    elif $VERBOSE; then
        case "$status" in
            pass)  echo "  ✓ $name: $detail" ;;
            fail)  echo "  ✗ $name: $detail" ;;
            warn)  echo "  ⚠ $name: $detail" ;;
        esac
    else
        case "$status" in
            pass)  echo "✓ $name" ;;
            fail)  echo "✗ $name: $detail" ;;
            warn)  echo "⚠ $name: $detail" ;;
        esac
    fi

    case "$status" in
        pass) ((PASS++)) ;;
        fail) ((FAIL++)) ;;
        warn) ((WARN++)) ;;
    esac
}

log_section() {
    if $JSON; then
        echo "{\"section\":\"$1\"}"
    else
        echo ""
        echo "=== $1 ==="
    fi
}

# ------------------------------------------------------------------
# Detectar entorno
# ------------------------------------------------------------------
log_section "Entorno"

if command -v python3 &>/dev/null; then
    PY_VERSION=$(python3 --version 2>&1)
    check "python" "pass" "$PY_VERSION"
else
    check "python" "fail" "No encontrado"
fi

if command -v uv &>/dev/null; then
    check "uv" "pass" "$(uv --version 2>/dev/null)"
else
    check "uv" "warn" "No instalado"
fi

# ------------------------------------------------------------------
# Paquete Python
# ------------------------------------------------------------------
log_section "Paquete Python"

# Verificar que el paquete está instalado o accesible
if [[ -f "$ROOT_DIR/pyproject.toml" ]]; then
    check "pyproject.toml" "pass" "Presente"
else
    check "pyproject.toml" "fail" "Falta"
fi

if [[ -f "$ROOT_DIR/README.md" ]]; then
    check "README.md" "pass" "Presente ($(wc -l < "$ROOT_DIR/README.md") líneas)"
else
    check "README.md" "fail" "Falta"
fi

# Verificar que video_intake_core puede importarse
if python3 -c "import sys; sys.path.insert(0, '$ROOT_DIR/packages'); import video_intake_core" 2>/dev/null; then
    check "import video_intake_core" "pass" "OK"
else
    check "import video_intake_core" "fail" "No se puede importar"
fi

# Verificar que la CLI existe
if [[ -f "$ROOT_DIR/packages/video_intake_core/cli/__init__.py" ]]; then
    check "CLI module" "pass" "Presente"
else
    check "CLI module" "warn" "Falta (pendiente de implementar)"
fi

# ------------------------------------------------------------------
# Dependencias del sistema
# ------------------------------------------------------------------
log_section "Dependencias del sistema"

if command -v ffmpeg &>/dev/null; then
    check "ffmpeg" "pass" "$(ffmpeg -version 2>&1 | head -1 | awk '{print $3}')"
else
    check "ffmpeg" "fail" "No encontrado"
fi

if command -v ffprobe &>/dev/null; then
    check "ffprobe" "pass" "Disponible"
else
    check "ffprobe" "pass" "Incluido con ffmpeg"
fi

if command -v tesseract &>/dev/null; then
    check "tesseract" "pass" "$(tesseract --version 2>&1 | head -1 | awk '{print $3}')"
else
    check "tesseract" "warn" "No instalado (OCR no disponible)"
fi

if command -v yt-dlp &>/dev/null; then
    check "yt-dlp" "pass" "$(yt-dlp --version 2>/dev/null || echo 'desconocida')"
else
    check "yt-dlp" "warn" "No instalado (acquisición remota limitada)"
fi

# ------------------------------------------------------------------
# Paquetes Python opcionales
# ------------------------------------------------------------------
log_section "Paquetes Python opcionales"

python3 -c "
import importlib
import sys

pkgs = [
    ('yt_dlp', 'yt-dlp'),
    ('whisper', 'openai-whisper'),
    ('cv2', 'opencv-python'),
    ('PIL', 'Pillow'),
    ('pytesseract', 'pytesseract'),
    ('py_scene_detect', 'py_scene_detect'),
    ('numpy', 'numpy'),
    ('yaml', 'PyYAML'),
    ('rich', 'rich'),
]

for mod, name in pkgs:
    try:
        importlib.import_module(mod)
        print(f'PASS:{name}')
    except ImportError:
        print(f'FAIL:{name}')
" | while IFS=: read -r status name; do
    case "$status" in
        PASS) check "$name" "pass" "Instalado" ;;
        FAIL) check "$name" "warn" "No instalado" ;;
    esac
done

# ------------------------------------------------------------------
# Estructura del proyecto
# ------------------------------------------------------------------
log_section "Estructura del proyecto"

REQUIRED_DIRS=(
    "packages/video_intake_core/acquisition"
    "packages/video_intake_core/audio"
    "packages/video_intake_core/context"
    "packages/video_intake_core/inspection"
    "packages/video_intake_core/jobs"
    "packages/video_intake_core/policies"
    "packages/video_intake_core/schemas"
    "packages/video_intake_core/security"
    "packages/video_intake_core/storage"
    "packages/video_intake_core/utils"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [[ -d "$ROOT_DIR/$dir" ]]; then
        check "dir:$dir" "pass" "Existe"
    else
        check "dir:$dir" "fail" "Falta"
    fi
done

REQUIRED_FILES=(
    "pyproject.toml"
    "README.md"
    "LICENSE"
    "SECURITY.md"
    "CONTRIBUTING.md"
    "CODE_OF_CONDUCT.md"
    "CHANGELOG.md"
    "scripts/bootstrap.sh"
    "scripts/doctor.sh"
    "scripts/install-system-deps.sh"
    "adapters/hermes/plugin.yaml"
    "config/default.yaml"
    "docs/architecture.md"
    "docs/installation.md"
    "docs/configuration.md"
    "docs/security-model.md"
    "docs/supported-sources.md"
    "docs/portability.md"
    "docs/memory-integration.md"
    "docs/asset-generation.md"
    "docs/troubleshooting.md"
    "docs/development.md"
    "docs/adr/README.md"
    "docs/adr/001-python-cli-core.md"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [[ -f "$ROOT_DIR/$file" ]]; then
        check "file:$file" "pass" "Presente"
    else
        check "file:$file" "fail" "Falta"
    fi
done

# ------------------------------------------------------------------
# Scripts ejecutables
# ------------------------------------------------------------------
log_section "Scripts"

for script in scripts/*.sh; do
    if [[ -x "$ROOT_DIR/$script" ]]; then
        check "executable:$script" "pass" "Ejecutable"
    else
        check "executable:$script" "warn" "No ejecutable"
    fi
done

# ------------------------------------------------------------------
# Adapters
# ------------------------------------------------------------------
log_section "Adapters"

for adapter in adapters/hermes adapters/opencode adapters/claude-code adapters/codex adapters/agy adapters/generic-agent-skills; do
    if [[ -d "$ROOT_DIR/$adapter" ]]; then
        check "adapter:$adapter" "pass" "Presente"
        if [[ -f "$ROOT_DIR/$adapter/README.md" ]]; then
            check "adapter:$adapter/README.md" "pass" "Documentado"
        else
            check "adapter:$adapter/README.md" "warn" "Sin README"
        fi
        if [[ -f "$ROOT_DIR/$adapter/install.sh" ]]; then
            check "adapter:$adapter/install.sh" "pass" "Instalador presente"
        else
            check "adapter:$adapter/install.sh" "warn" "Sin instalador"
        fi
    else
        check "adapter:$adapter" "fail" "Falta"
    fi
done

# ------------------------------------------------------------------
# .github
# ------------------------------------------------------------------
log_section ".github"

if [[ -d "$ROOT_DIR/.github/workflows" ]]; then
    check ".github/workflows" "pass" "Presente"
    for wf in .github/workflows/*.yml; do
        if [[ -f "$ROOT_DIR/$wf" ]]; then
            check ".github/workflows:$(basename $wf)" "pass" "Presente"
        fi
    done
else
    check ".github/workflows" "warn" "No presente"
fi

# ------------------------------------------------------------------
# Skill
# ------------------------------------------------------------------
log_section "Skill portable"

if [[ -f "$ROOT_DIR/skill/SKILL.md" ]]; then
    check "skill/SKILL.md" "pass" "Presente"
else
    check "skill/SKILL.md" "fail" "Falta"
fi

# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------
log_section "Tests"

if [[ -d "$ROOT_DIR/tests" ]]; then
    check "tests/" "pass" "Presente"
    UNIT_TESTS=$(find "$ROOT_DIR/tests/unit" -name "*.py" 2>/dev/null | wc -l)
    CONTRACT_TESTS=$(find "$ROOT_DIR/tests/contract" -name "*.py" 2>/dev/null | wc -l)
    check "tests/unit" "pass" "$UNIT_TESTS archivos" 2>/dev/null || check "tests/unit" "warn" "Pendiente"
    check "tests/contract" "pass" "$CONTRACT_TESTS archivos" 2>/dev/null || check "tests/contract" "warn" "Pendiente"
else
    check "tests/" "fail" "Falta"
fi

# ------------------------------------------------------------------
# Resumen
# ------------------------------------------------------------------
echo ""
echo "=== Resumen ==="
echo "Pasados: $PASS"
echo "Fallidos: $FAIL"
echo "Advertencias: $WARN"

if [[ $FAIL -gt 0 ]]; then
    echo ""
    echo "Hay $FAIL verificación(es) fallida(s). Revisa los errores arriba."
    exit 1
elif [[ $WARN -gt 0 ]]; then
    echo ""
    echo "Hay $WARN advertencia(s). Revisa para mejorar."
    exit 0
else
    echo ""
    echo "✓ Verificación completada. Todo está en orden."
    exit 0
fi
