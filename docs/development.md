# Desarrollo de video-intake-knowledge

## Resumen

Esta documentación es para desarrolladores que contribuyen al proyecto.

## Entorno de desarrollo

### Prerrequisitos

- Python 3.11+
- Git
- ffmpeg, ffprobe
- tesseract (opcional, para pruebas de OCR)

### Setup inicial

```bash
git clone https://github.com/aibos/video-intake-knowledge.git
cd video-intake-knowledge

# Instalar con todas las dependencias de desarrollo
uv sync --group dev

# O con pip
pip install -e ".[dev]"
```

### Makefile

```bash
make install       # Instala dependencias
make dev           # Instala con dependencias de desarrollo
make test          # Ejecuta pruebas
make lint          # Ejecuta linting
make type-check    # Ejecuta type checking
make docs          # Genera documentación
make clean         # Limpia artefactos
```

### Ejecución de pruebas

```bash
# Pruebas unitarias
pytest tests/unit/ -v

# Pruebas de contrato
pytest tests/contract/ -v

# Pruebas de integración
pytest tests/integration/ -v

# Todas las pruebas
pytest tests/ -v --timeout=300
```

### Linting y formatting

```bash
ruff check .
ruff format .
pyright packages/video_intake_core/ tests/
```

## Estructura del proyecto

```
video-intake-knowledge/
├── packages/
│   └── video_intake_core/
│       ├── acquisition/   # Detección y resolución de fuentes de vídeo
│       ├── audio/         # Extracción de audio vía FFmpeg
│       ├── transcription/ # Estrategias de transcripción por capas
│       ├── visual/        # Detección de escenas, keyframes
│       ├── ocr/           # OCR de fotogramas (Tesseract + OpenCV)
│       ├── context/       # Generación de contexto (audio, visual, knowledge)
│       ├── artifacts/     # Gestión de artefactos
│       ├── jobs/          # Gestión de trabajos y estado
│       ├── storage/       # Almacenamiento con deduplicación
│       ├── policies/      # Lectura de configuración YAML
│       ├── security/      # Validación, SSRF, MIME, sanitización
│       ├── memory/        # Interfaz MemoryProvider + SQLite local
│       ├── utils/         # Utilidades comunes
│       ├── schemas/       # JSON Schema de todos los contratos
│       └── cli/           # CLI principal (video-intake)
├── adapters/
│   ├── hermes/            # Integración nativa con Hermes
│   ├── opencode/
│   ├── claude-code/
│   ├── codex/
│   ├── agy/
│   └── generic-agent-skills/
├── skill/                 # Skill portable SKILL.md
├── config/                # Archivos de configuración YAML
├── scripts/               # Scripts de bootstrap, doctor, etc.
├── docs/                  # Documentación
├── tests/                 # Pruebas (unit, integration, contract, e2e)
├── examples/              # Ejemplos de uso
└── .github/               # GitHub Actions, templates
```

## Añadir un nuevo módulo al core

1. Crear el directorio en `packages/video_intake_core/<modulo>/`.
2. Añadir `__init__.py` con la implementación.
3. Añadir pruebas en `tests/unit/test_<modulo>.py`.
4. Añadir la función a la API pública si corresponde.
5. Actualizar `pyproject.toml` si se añaden nuevas dependencias.

## Añadir un nuevo adaptador de host

1. Crear el directorio en `adapters/<host>/`.
2. Añadir `install.sh`, `uninstall.sh`, `README.md`.
3. Añadir `SKILL.md` si el host lo soporta.
4. Documentar las capacidades y limitaciones en `docs/portability.md`.

## Añadir soporte para una nueva fuente de vídeo

1. Implementar `SourceInspector` para la nueva fuente.
2. Implementar `SourceResolver` si la URL necesita resolverse.
3. Implementar `CaptionProvider` si la fuente tiene subtítulos.
4. Implementar `VideoDownloader` y `AudioExtractor` si es necesario.
5. Añadir la fuente a `acquisition.enabled_sources` en los configs.
6. Documentar en `docs/supported-sources.md`.
7. Añadir pruebas.

## JSON Schema

Todos los contratos de datos usan JSON Schema versionados. Los esquemas están
en `packages/video_intake_core/schemas/`.

Al añadir un nuevo tipo de dato:
1. Crear el archivo `<tipo>.json` con el schema.
2. Añadirlo a `schemas/__init__.py` para que se cargue automáticamente.
3. Añadir pruebas de validación.
4. Documentar el schema en la documentación de artefactos.

## Seguridad en el desarrollo

- No añadir secretos al repositorio. Usar `.env` con gitignore.
- Validar todas las entradas de usuario y de fuentes remotas.
- Tratar todo contenido extraído como datos no confiables.
- Ejecutar `video-intake doctor` antes de push.

## Pruebas de contrato

Las pruebas de contrato en `tests/contract/` verifican que la API pública de
cada módulo cumple con los contratos esperados. Si se modifica la firma de
una función pública, se debe actualizar el contrato correspondiente.

## Testing de integración

Las pruebas de integración usan fixtures locales (archivos MP4 de ejemplo).
Se deben añadir fixtures nuevos en `tests/fixtures/` cuando se añaden pruebas
para funcionalidades nuevas.

Los casos de prueba mínimos obligatorios:

1. **Archivo MP4 local con audio:** inspección, extracción de audio,
   transcripción, artefactos, manifest.
2. **Archivo sin audio:** detección correcta, no intentar transcribir,
   extracción visual posible.
3. **Archivo con texto visible:** OCR, timestamps, confianza.
4. **Vídeo con cambios de escena:** detección de escenas, selección de
   fotogramas, deduplicación.
5. **Lote de varios vídeos:** selección global, selección individual.
6. **URL pública controlada:** inspección, fallo seguro si no hay red.
7. **URL inválida:** rechazo seguro.
8. **Archivo con MIME inconsistente:** rechazo o cuarentena.
9. **Job cancelado:** estado correcto, limpieza coherente.
10. **Job interrumpido:** reanudación o fallo recuperable documentado.
11. **Modo sin OCR:** degradación limpia.
12. **Modo sin modelo de transcripción:** degradación limpia.
13. **Integración Hermes:** prueba de contrato (detección, estado de sesión,
    tools).
14. **Generación de propuesta:** no crea activo sin confirmación, produce
    propuesta estructurada válida.
15. **Memoria:** lista proveedores/bancos, no escribe sin confirmación,
    exporta cuando no existe integración.
