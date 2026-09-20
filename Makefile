# Makefile — Tareas comunes para el desarrollo de video-intake-knowledge
# =============================================================================
#
# Uso:
#   make install       Instala dependencias de desarrollo
#   make dev           Instala con todas las extras
#   make test          Ejecuta todas las pruebas
#   make test-unit     Pruebas unitarias
#   make test-contract Pruebas de contrato
#   make test-integration Pruebas de integración
#   make test-e2e      Pruebas end-to-end
#   make test-security Pruebas de seguridad
#   make lint          Ejecuta ruff check
#   make format        Ejecuta ruff format
#   make format-check  Verifica formatting sin cambiar archivos
#   make type-check    Ejecuta pyright
#   make docs          Genera documentación (si está configurado)
#   make clean         Limpia artefactos de build y cache
#   make clean-test    Limpia cache de pruebas
#   make self-test     Ejecuta video-intake self-test
#   make doctor        Ejecuta video-intake doctor
#   make help          Muestra esta ayuda
# =============================================================================

.PHONY: install dev test test-unit test-contract test-integration test-e2e test-security lint format format-check type-check docs clean clean-test self-test doctor help

# Detectar entorno Python
PYTHON := python3
UV := uv

# Directorio del proyecto
ROOT_DIR := $(shell pwd)

#-----------------------------------------------------------------------
# Instalación
#-----------------------------------------------------------------------

install:
	@echo "=== Instalando dependencias de desarrollo ==="
	$(UV) sync --group dev --group core

dev:
	@echo "=== Instalando todas las dependencias ==="
	$(UV) sync --group dev --group full --group docs

#-----------------------------------------------------------------------
# Pruebas
#-----------------------------------------------------------------------

test: test-unit test-contract test-integration
	@echo "=== Todas las pruebas completadas ==="

test-unit:
	@echo "=== Pruebas unitarias ==="
	$(UV) run pytest tests/unit/ -v --tb=short

test-contract:
	@echo "=== Pruebas de contrato ==="
	$(UV) run pytest tests/contract/ -v --tb=short

test-integration:
	@echo "=== Pruebas de integración ==="
	$(UV) run pytest tests/integration/ -v --tb=short --timeout=120

test-e2e:
	@echo "=== Pruebas end-to-end ==="
	$(UV) run pytest tests/e2e/ -v --tb=short --timeout=300

test-security:
	@echo "=== Pruebas de seguridad ==="
	$(UV) run pytest tests/security/ -v --tb=short

#-----------------------------------------------------------------------
# Calidad de código
#-----------------------------------------------------------------------

lint:
	@echo "=== Linting con ruff ==="
	$(UV) run ruff check .

format:
	@echo "=== Formateando con ruff ==="
	$(UV) run ruff format .

format-check:
	@echo "=== Verificando formatting ==="
	$(UV) run ruff format --check .

type-check:
	@echo "=== Type checking con pyright ==="
	$(UV) run pyright packages/video_intake_core/ tests/ scripts/ adapters/ skill/ --pythonversion 3.11

#-----------------------------------------------------------------------
# Documentación y diagnóstico
#-----------------------------------------------------------------------

docs:
	@echo "=== Generando documentación ==="
	@# Para extender: añadir generación de docs aquí
	@echo "No hay generador de documentación configurado."

clean:
	@echo "=== Limpiando artefactos ==="
	rm -rf dist/ build/ *.egg-info/
	rm -rf __pycache__/ packages/**/__pycache__/
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
	rm -rf .venv/
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete

clean-test:
	@echo "=== Limpiando cache de pruebas ==="
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

self-test:
	@echo "=== Ejecutando video-intake self-test ==="
	$(UV) run video-intake self-test

doctor:
	@echo "=== Ejecutando video-intake doctor ==="
	$(UV) run video-intake doctor

#-----------------------------------------------------------------------
# Help
#-----------------------------------------------------------------------

help:
	@echo "=== video-intake-knowledge — Makefile ==="
	@echo ""
	@echo "Comandos disponibles:"
	@echo ""
	@echo "  make install          Instalar dependencias de desarrollo"
	@echo "  make dev              Instalar todas las dependencias (+ extras)"
	@echo "  make test             Ejecutar todas las pruebas"
	@echo "  make test-unit        Pruebas unitarias"
	@echo "  make test-contract    Pruebas de contrato"
	@echo "  make test-integration Pruebas de integración"
	@echo "  make test-e2e         Pruebas end-to-end"
	@echo "  make test-security    Pruebas de seguridad"
	@echo "  make lint             Ejecutar ruff check"
	@echo "  make format           Formatear código con ruff"
	@echo "  make format-check     Verificar formatting sin cambiar archivos"
	@echo "  make type-check       Type checking con pyright"
	@echo "  make clean            Limpiar artefactos de build y cache"
	@echo "  make clean-test       Limpiar cache de pruebas"
	@echo "  make self-test        Ejecutar video-intake self-test"
	@echo "  make doctor           Ejecutar video-intake doctor"
	@echo "  make help             Mostrar esta ayuda"
	@echo ""
