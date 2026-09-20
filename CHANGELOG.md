# CHANGELOG

Todas las notas de versión notables siguen [SemVer](https://semver.org/).
Registradas en orden cronológico inverso (más reciente primero).

## [0.1.0] — 2026-09-20

### Added (nuevo)

- **Core Python package** `video_intake_core` con módulos:
  - `acquisition` — Detección y resolución de fuentes de vídeo (YouTube, Facebook,
    Instagram, TikTok, archivos locales). Soporta MP4, MOV, MKV, WebM, AVI, M4V,
    MPEG, MPG, FLV, WMV.
  - `audio` — Extracción de audio de vídeo vía FFmpeg. Formatos: wav, mp3, m4a,
    opus, flac.
  - `inspection` — Inspección de metadatos sin descarga vía ffprobe (local) y yt-dlp
    (remoto).
  - `transcription` — Estrategias de transcripción por capas: captions de plataforma,
    captions descargables (SRT, VTT, ASS, SSA, JSON3), Whisper local.
  - `visual` — Detección de escenas (PySceneDetect), extracción de keyframes,
    análisis de frames.
  - `ocr` — OCR de frames con Tesseract + preprocesado OpenCV. Batch OCR, confianza,
    bounding boxes.
  - `context` — Generación de contexto de audio (resumen, índice temporal, temas,
    entidades, citas, niveles de confianza), contexto visual, extracción de
    conocimiento. Exportación de Markdown y MDX.
  - `artifacts` — Registro de artefactos (transcript, audio, frames, OCR, context,
    video). Integración con StorageManager.
  - `jobs` — Gestión de trabajos: creación, ejecución, estado, cancelación,
    reanudación. Persistencia en SQLite. Progreso y notificación.
  - `storage` — Almacenamiento de artefactos con deduplicación SHA-256, estructura
    por job, limpieza por antigüedad.
  - `security` — Validación de URL, protección SSRF (bloqueo de rangos privados y
    de metadatos de nube), detect MIME, redacción de datos sensibles, sanitización
    de nombres de archivos y rutas, protección contra prompt injection.
  - `utils` — Utilidades: validación de URL, hashing SHA-256, manejo de archivos
    (borrar, copiar, mover), carga de config YAML, validación contra JSON Schema.
  - `policies` — Lectura de configuración YAML, resolución de políticas por capas:
    transcripción, visual, modelos, almacenamiento, seguridad, límites, adquisición,
    memoria, host.
  - `memory` — Interfaz abstracta `MemoryProvider` y implementación local SQLite.
    CRUD de entradas de memoria, búsqueda por texto, estadísticas.
  - `schemas` — JSON Schemas versionados para source, job, artifact_manifest,
    transcript_segment, ocr_block, audio_context, visual_context, knowledge_extraction,
    build_proposal, memory_entry, memory_bank.
  - `cli` — CLI completa `video-intake` con comandos: doctor, inspect, extract,
    batch, status, cancel, artifacts, export, cleanup, config validate, self-test,
    models (list/install/verify/remove). Modo interactivo y no interactivo, JSON output.

- **CLI standalone** `scripts/standalone_hermes.sh` — Script de integración con Hermes
  Agent para uso desde otras herramientas.

- **Scripts de operación**:
  - `bootstrap.sh` — Instalación completa del entorno (deps del sistema, venv, paquete).
  - `doctor.sh` — Diagnóstico de salud del entorno.
  - `install-system-deps.sh` — Instalación de dependencias del sistema (ffmpeg, tesseract).
  - `verify-install.sh` — Verificación de instalación completa.

- **Configuración** (4 archivos YAML):
  - `default.yaml` — Valor por defecto, balanceado.
  - `offline.yaml` — Sin descargas remotas, solo local.
  - `low-cost.yaml` — Sin modelos externos, Whisper tiny + Tesseract, recursos limitados.
  - `production.yaml` — Políticas estrictas, retención, escaneo de seguridad, producción.

- **Integración Hermes Agent**:
  - `adapters/hermes/plugin.yaml` — Definición del plugin con 6 tools registradas.
  - `adapters/hermes/install.sh` — Instalador del plugin.
  - `adapters/hermes/uninstall.sh` — Desinstalador del plugin.
  - `adapters/hermes/README.md` — Documentación del plugin.
  - `adapters/hermes/config.example.yaml` — Configuración de ejemplo.

- **Adapters para otros hosts**:
  - `adapters/opencode/SKILL.md` — Skill portable para OpenCode.
  - `adapters/claude-code/SKILL.md` — Skill portable para Claude Code.

- **Skill portable**:
  - `skill/SKILL.md` — Skill de referencia para cualquier entorno compatible con
    SKILL.md.

- **Documentación**:
  - `README.md` — Descripción del proyecto, instalación, uso, seguridad, enlaces.
  - `docs/architecture.md` — Arquitectura del sistema, capas, módulos, flujo de trabajo.
  - `docs/installation.md` — Instalación local, con modelos, en Hermes, en otros hosts,
    configuración, actualización, desinstalación, troubleshooting.
  - `docs/configuration.md` — Configuración por YAML y variables de entorno, precedencia,
    perfiles, gestión de modelos, migración.
  - `docs/security-model.md` — Principios de seguridad, amenazas mitigadas, controles de
    respuesta, secretos, retención, auditoría.
  - `docs/supported-sources.md` — Fuentes soportadas (YouTube, Facebook, Instagram, TikTok,
    archivos locales), métodos de adquisición, extensibilidad.
  - `docs/portability.md` — Matriz de compatibilidad por host, capacidades de cada adaptador,
    fallbacks, requisitos, limitaciones reales, cómo añadir nuevos hosts.
  - `docs/memory-integration.md` — Interfaz MemoryProvider, implementación local, integración
    con Hermes, fallback para hosts sin memoria, confirmación explícita, exportación manual.
  - `docs/asset-generation.md` — Generación de activos (tools, skills, agentes, plugins,
    plantillas, documentos, workflows, knowledge packs) a partir de contenido extraído.
  - `docs/troubleshooting.md` — Solución de problemas comunes (comando no encontrado,
    ffmpeg/tesseract ausentes, modelo no encontrado, error de transcripción, URL no funciona,
    OCR no detecta texto, logs y depuración, reports de error).
  - `docs/development.md` — Desarrollo del proyecto: entorno, estructura, añadir módulos,
    añadir fuentes, JSON Schema, seguridad, pruebas de contrato, pruebas de integración.
  - `docs/adr/001-python-cli-core.md` — ADR sobre elección de Python/CLI como núcleo.
  - `docs/adr/README.md` — Índice de ADRs.
  - `SECURITY.md` — Política de divulgación responsable de vulnerabilidades.
  - `CONTRIBUTING.md` — Guía de contribución: bugs, features, PRs, convenciones de código,
    pruebas, convención de commits, ramas, versionado, ética y seguridad.
  - `CODE_OF_CONDUCT.md` — Código de conducta basado en Contributor Covenant v2.1.

- **GitHub Actions**:
  - `.github/workflows/ci.yml` — CI completo: lint, type-check, unit tests (matrix 3.11-3.13),
    security scan (gitleaks), build verification, integration tests, docs check, release build.
  - `.github/workflows/release.yml` — Release: test, build, SBOM, publish a PyPI y GHCR.
  - `.github/workflows/security.yml` — Análisis de seguridad continua: static analysis (ruff,
    bandit), secret scanning (gitleaks), dependency review, vulnerability audit (pip-audit),
    build verification.
  - `.github/pull_request_template.md` — Plantilla de PR.

- **Tests**:
  - `tests/contract/test_core_contracts.py` — Pruebas de contrato para APIs públicas de los
    módulos core.

- **Test kit**:
  - `packages/video_intake_testkit/__init__.py` — Fixtures y helpers para pruebas:
    `TestFixtures` (sample files, dicts de prueba para source, transcript, ocr, scene,
    keyframe, job, build_proposal, memory_entry, context) y `TestHelpers` (assertions,
    creación de archivos de prueba temporal con FFmpeg).

- **Otros**:
  - `LICENSE` — Apache License 2.0.
  - `.gitignore` — Exclusion de logs, venvs, build, cache, secrets.
  - `.editorconfig` — Configuración de editor: UTF-8, LF, indentación.
  - `Makefile` — Tareas comunes: install, dev, test (unit/contract/integration/e2e/security),
    lint, format, type-check, docs, clean, clean-test, self-test, doctor, help.

### Changed (cambiado)

- (esta es la primera versión, no hay cambios previos)

### Deprecated (deprecado)

- (no hay funcionalidades deprecadas en esta versión)

### Removed (eliminado)

- (no hay funcionalidades eliminadas en esta versión)

### Fixed (corregido)

- (no hay bugs corregidos en esta versión, es la primera release)

### Security (seguridad)

- Protección SSRF para acceso a recursos internos y de metadatos de nube.
- Validación MIME de archivos descargados.
- Protección contra prompt injection en transcripciones, subtítulos, OCR.
- Sanitización de nombres de archivos y rutas.
- Límites de tamaño, duración, concurrencia y timeouts.
- Documentación de seguridad en `SECURITY.md` y `docs/security-model.md`.

### Known limitations (limitaciones conocidas)

- Los vídeos remotos requieren conexión a internet.
- La disponibilidad de fuentes remotas depende de las políticas de las plataformas.
- Los modelos de IA locales requieren instalación explímara del usuario.
- La memoria nativa solo está disponible si la plataforma host la expone.
- Los hooks de detección pueden no estar disponibles en todas las versiones de Hermes.
- Los adaptadores para AGY y Codex están documentados en el futuro pero sin implementación
  completa en esta versión (SKILL.md portable sí está disponible).
