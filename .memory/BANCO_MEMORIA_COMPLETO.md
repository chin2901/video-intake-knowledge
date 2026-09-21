# Banco de Memoria: video-intake-knowledge
## Versión: 0.1.0
## Ubicación: /srv/video-intake-knowledge/.memory/
## Última actualización: 21 septiembre 2026

---

## 1. RESUMEN EJECUTIVO

**video-intake-knowledge** es un sistema de extracción de contenido audiovisual diseñado para detectar (detectar), adquirir (adquirir), analizar (analizar) y convertir vídeos en conocimiento utilizable dentro de agentes de IA.

El proyecto es independiente de AibOS, AiboT, OpenCode, Claude Code y Codex, con su propio banco de memoria dedicado.

---

## 2. HISTORIA DEL PROYECTO

### 2.1 Orígenes (domingo 20 septiembre 2026)

El proyecto fue iniciado por el usuario con los siguientes requisitos:

- Repositorio GitHub de calidad producción
- Nombre: video-intake-knowledge (o variante profesional si no disponible)
- Licencia permisiva: Apache-2.0 o MIT
- Prioridad absoluta: Hermes Agent
- Compatible con: AGY, OpenCode, Claude Code, Codex y otros entornos compatibles con SKILL.md
- Sin demos, prototipos ni pseudocódigo - todo real, funcional, probado, documentado

### 2.2 Sesión Inicial (domingo 20 septiembre 2026)

**Objetivos:**
- Crear estructura completa del proyecto
- Configurar git y remote
- Crear archivos esenciales (README, LICENSE, pyproject.toml, etc.)
- Crear adaptadores para múltiples entornos

**Resultado:**
- Estructura base creada con 117 archivos
- 17 módulos core bajo packages/video_intake_core/
- Adapters para Hermes, AGY, OpenCode, Claude Code, Codex configurados
- Git remote configurado: https://github.com/chin2901/video-intake-knowledge.git
- Problemas de instalación: License classifier error (PEP-639)

### 2.3 Sesión de Corrección (lunes 21 septiembre 2026)

**Problema inicial:** Al intentar instalar y usar el paquete, se encontraron múltiples errores de importación:

```
ImportError: No module named 'video_intake_core.utils.validation'
ImportError: No module named 'video_intake_core.schemas.source'
ImportError: No module named 'video_intake_core.schemas.job'
ImportError: cannot import name 'sanitize_filename' from 'video_intake_core.utils'
ImportError: cannot import name 'detect_video_sources' from 'video_intake_core.acquisition'
ImportError: cannot import name 'detect_mime' from 'video_intake_core.security'
ImportError: cannot import name 'SSrfProtection' from 'video_intake_core.security'
ImportError: cannot import name 'PromptInjectionProtection' from 'video_intake_core.security'
ImportError: cannot import name 'list_artifacts' from 'video_intake_core.jobs'
```

**Acciones correctivas:**
1. Crear submódulos faltantes de utils (validation.py, fs.py, text.py)
2. Crear schemas/source.py con Source, SourceType, ResolvedURL
3. Crear schemas/job.py con Job, JobStatus
4. Crear cli/__main__.py para ejecución como módulo
5. Agregar alias detect_video_sources en acquisition
6. Agregar detect_mime, is_safe_mime a security
7. Crear clases SSrfProtection y PromptInjectionProtection en security
8. Eliminar imports de list_artifacts inexistente
9. Reestructurar utils/__init__.py para re-exportar desde submódulos
10. Evitar circular imports en security usando importación directa

**Resultado:**
- CLI funcional: `python3 -m video_intake_core.cli --help` funciona correctamente
- 33 tests de seguridad recolectados exitosamente
- 8 commits en el repositorio
- Banco de memoria independiente creado y registrado

---

## 3. ARQUITECTURA DEL PROYECTO

### 3.1 Estructura de directorios

```
/srv/video-intake-knowledge/
├── packages/
│   └── video_intake_core/           # Paquete principal
│       ├── acquisition/             # Detección y resolución de fuentes
│       ├── security/                # Protección SSRF, sanitización
│       ├── schemas/                 # Modelos de datos + JSON schemas
│       ├── utils/                   # Utilidades (submódulos: validation, fs, text)
│       ├── artifacts/              # Gestión de artefactos
│       ├── audio/                  # Contexto de audio
│       ├── cli/                    # Interfaz de línea de comandos
│       ├── context/                # Contexto de vídeo
│       ├── inspection/             # Inspección de metadatos
│       ├── jobs/                   # Gestión de jobs
│       ├── memory/                 # Persistencia de memoria
│       ├── ocr/                    # Reconocimiento óptico de caracteres
│       ├── policies/               # Resolución de políticas
│       ├── storage/                # Almacenamiento
│       ├── transcription/          # Transcripción
│       └── visual/                 # Contexto visual
├── adapters/                        # Adaptadores para entornos
│   ├── hermes/                      # Adaptador Hermes Agent
│   ├── agy/                         # Adaptador AGY
│   ├── opencode/                   # Adaptador OpenCode
│   ├── claude-code/                # Adaptador Claude Code
│   ├── codex/                      # Adaptador Codex
│   └── generic-agent-skills/       # Adaptador genérico
├── .memory/                         # Banco de memoria independiente
├── .github/                         # Workflows GitHub
├── docs/                            # Documentación
├── tests/                           # Tests (unit, security, integration, e2e)
├── LICENSE                          # Apache-2.0
├── pyproject.toml                   # Configuración del paquete
├── README.md                        # Documentación principal
└── .gitignore                       # Ignorar archivos
```

### 3.2 Módulos core (17)

1. **acquisition**: Detección de fuentes de video y resolución de URLs
   - Funciones: detect_source_type, detect_source, resolve_url
   - Extracción: extract_video_id, is_video_url, extract_all_video_urls
   - Utilidades: generate_safe_filename, create_source_id
   - Patterns: YOUTUBE_PATTERNS, FACEBOOK_PATTERNS, INSTAGRAM_PATTERNS, TIKTOK_PATTERNS

2. **security**: Protección y validación
   - SSRF: validate_video_url, validate_local_file
   - Sanitización: sanitize_for_prompt, redact_sensitive_data
   - Detección: detect_mime, is_safe_mime
   - Clases: SSrfProtection, PromptInjectionProtection
   - Constants: SSRF_BLOCKED_HOSTS

3. **schemas**: Modelos de datos
   - source.py: Source, SourceType, ResolvedURL
   - job.py: Job, JobStatus
   - JSON schemas para validación

4. **utils**: Utilidades
   - validation.py: is_safe_url, validate_url, sanitize_for_prompt, redact_sensitive_data
   - fs.py: sanitize_filename, sanitize_path, is_video_file_ext, compute_sha256
   - text.py: slugify, parse_duration, sizeof_fmt

5. **cli**: Interfaz de línea de comandos
   - Comandos: doctor, inspect, extract, batch, status, cancel, artifacts, export, cleanup, config, self-test, models
   - Opciones: --version, --json, --verbose, --config, --log-level, --user-id

6-17. Módulos adicionales:
   - artifacts: Gestión de artefactos de los jobs
   - audio: Extracción de contexto de audio
   - context: Contexto general del vídeo
   - inspection: Inspección de metadatos
   - jobs: JobManager y funciones auxiliares
   - memory: Persistencia de memoria (LocalSQLiteMemoryProvider)
   - ocr: Reconocimiento óptico de caracteres
   - policies: Resolución de políticas
   - storage: Almacenamiento
   - transcription: Transcripción
   - visual: Contexto visual

### 3.3 Adapters

**Hermes Agent (prioridad):**
- plugin/register.py: Registro del plugin
- tools/video_intake_harness.py: Herramientas de integración
- hooks/hook_video_intake.sh: Hooks de integración
- skill/SKILL.md: Skill para Hermes

**AGY:**
- SKILL.md: Skill para AGY
- config.example.yaml: Configuración ejemplo

**OpenCode:**
- SKILL.md: Skill para OpenCode

**Claude Code:**
- SKILL.md: Skill para Claude Code
- install.sh: Script de instalación

**Codex:**
- SKILL.md: Skill para Codex
- install.sh: Script de instalación
- uninstall.sh: Script de desinstalación

**Generic-agent-skills:**
- SKILL.md: Skill para entornos genéricos

---

## 4. PROBLEMAS Y SOLUCIONES

### 4.1 Problemas de instalación inicial

**Problema:** license classifiers superseded by license expressions (PEP-639)
**Causa:** Configuración incorrecta en pyproject.toml
**Solución:** Cambiar a license expressions en lugar de classifiers

### 4.2 Problemas de imports (sesión 21 sept 2026)

**Problema 1:** ModuleNotFoundError: No module named 'video_intake_core.utils.validation'
- **Análisis:** El módulo utils había sido reestructurado conceptualmente pero los submódulos no existían
- **Solución:** Crear submódulos validation.py, fs.py, text.py y actualizar __init__.py

**Problema 2:** ModuleNotFoundError: No module named 'video_intake_core.schemas.source'
- **Análisis:** acquisition importaba de schemas.source pero el archivo no existía
- **Solución:** Crear schemas/source.py

**Problema 3:** ModuleNotFoundError: No module named 'video_intake_core.schemas.job'
- **Análisis:** jobs importaba de schemas.job pero el archivo no existía
- **Solución:** Crear schemas/job.py

**Problema 4:** No module named 'video_intake_core.cli.__main__'
- **Análisis:** Python necesita __main__.py para ejecutar paquetes con -m
- **Solución:** Crear cli/__main__.py

**Problema 5:** ImportError: cannot import name 'list_artifacts' from 'video_intake_core.jobs'
- **Análisis:** CLI intentaba importar función inexistente
- **Solución:** Eliminar import

**Problema 6:** ImportError: cannot import name 'detect_video_sources' from acquisition
- **Análisis:** Nombre incompatible entre CLI y módulo
- **Solución:** Agregar alias detect_video_sources = detect_source

**Problema 7:** Circular imports entre security y utils
- **Análisis:** security usaba importación relativa que creaba circularidad
- **Solución:** Cambiar a importación directa desde video_intake_core.utils

**Problema 8:** Tests necesitaban detect_mime, is_safe_mime
- **Solución:** Agregar estas funciones a security

**Problema 9:** Tests necesitaban SSrfProtection, PromptInjectionProtection
- **Solución:** Crear estas clases en security

### 4.3 Limitaciones ambientales

**Problema:** Tiempos de ejecución excesivos
**Síntoma:** Timeout frecuente (exit code 124)
**Causa:** El servidor tiene tiempos de importación de Python lentos
**Impacto:**
- python3 -c "import video_intake_core" tarda ~5s
- pytest --collect-only tarda ~38-40s
- CLI commands blocked by timeout in this environment
- Tests cannot run fully in this environment

**Trabajo alrededor:**
- Usar timeout más largo para comandos
- Ejecutar con --collect-only para validar estructura sin ejecutar
- CLI --help funciona porque es rápido

### 4.4 Problemas conocidos pendientes

1. **Tests de seguridad no ejecutados:** 33 tests recolectados pero no ejecutados por timeout ambiental
2. **CLI commands completos no verificados:** Solo --help verificado, otros comandos (doctor, inspect, extract) no se pueden ejecutar completamente
3. **Documentación ADR:** Puede necesitar completarse
4. **Ejemplos de uso:** No verificados en esta sesión

---

## 5. DECISIONES DE DISEÑO

### 5.1 Separación de utils en submódulos
**Decisión:** Dividir utils en tres submódulos: validation, fs, text
**Justificación:** Mejor organización, separación de responsabilidades
**Implementación:** 
- validation.py: URL y prompt sanitization
- fs.py: File system operations
- text.py: Text formatting
- __init__.py: Re-export desde submódulos

### 5.2 Importación directa en security
**Decisión:** Usar importación directa en lugar de relativa
**Justificación:** Evitar circular imports entre security y utils
**Implementación:** `from video_intake_core.utils import (...)` en lugar de `from . import (...)`

### 5.3 Aliases para compatibilidad
**Decisión:** Crear alias detect_video_sources = detect_source
**Justificación:** CLI esperaba nombre diferente al existente en módulo
**Implementación:** Alias en acquisition/__init__.py

### 5.4 Banco de memoria independiente
**Decisión:** Crear .memory/ separado del sistema AibOS/AiboT
**Justificación:** El usuario solicitó independencia de otros sistemas
**Implementación:** 
- Estrutura completa con metadata.json, bank/, scripts/
- memory_manager.py con comandos init, status, update
- Registrado en Hindsight como memoria del proyecto

### 5.5 CLI como módulo ejecutable
**Decisión:** Soportar ejecución con `python3 -m video_intake_core.cli`
**Justificación:** Estándar Python para ejecutar paquetes
**Implementación:** cli/__main__.py con entry point

---

## 6. ESTADO ACTUAL (21 septiembre 2026, 03:41 UTC+2)

### 6.1 Repositorio

- **Commits:** 8 totales
- **Branch:** master
- **Remote:** https://github.com/chin2901/video-intake-knowledge.git
- **Archivos:** 117 totales
- **Estado:** Limpio (no hay archivos pendientes de commit)

### 6.2 Paquete instalado

- **Nombre:** video-intake-knowledge
- **Versión:** 0.1.0
- **Ubicación:** /home/aibos/.local/lib/python3.14/site-packages
- **Dependencias:** click, jsonschema, moviepy, Pillow, python-multipart, pyyaml, rich, tqdm

### 6.3 CLI

**Comando:** `python3 -m video_intake_core.cli` o `video-intake`

**Opciones:**
- --version: Mostrar versión
- --json: Salida JSON para integración
- --verbose, -v: Modo verboso
- --config CONFIG: Archivo de configuración YAML
- --log-level {debug,info,warning,error}: Nivel de log
- --user-id USER_ID: ID del usuario para correlación

**Comandos (12):**
1. doctor: Comprobar salud del entorno
2. inspect: Mostrar metadatos de una fuente
3. extract: Extraer contenido de una fuente
4. batch: Procesar un manifiesto de lote
5. status: Mostrar estado de un job
6. cancel: Cancelar un job en ejecución
7. artifacts: Lista los artefactos de un job
8. export: Exporta resultados de un job
9. cleanup: Limpia artefactos antiguos
10. config: Gestiona la configuración
11. self-test: Ejecuta pruebas de auto-diagnóstico
12. models: Gestiona modelos de transcripción

### 6.4 Tests

**Security tests:** 33 tests en 5 clases
- TestSSRFProtection: 6 tests
- TestFilenameSanitization: 7 tests
- TestSensitiveDataRedaction: 7 tests
- TestMimeDetection: 8 tests
- TestPromptInjectionProtection: 5 tests

**Estado:** Recolectados exitosamente, no ejecutados (timeout ambiental)

**Otras suites:** unit (test_cli.py con 29 tests), integration, e2e, contract

---

## 7. BANCO DE MEMORIA LOCAL

**Ubicación:** /srv/video-intake-knowledge/.memory/

**Estructura:**
```
.memory/
├── README.md
├── metadata.json
├── bank/
│   ├── project_context.json
│   ├── architecture_decisions.json
│   ├── integration_notes.json
│   └── known_issues.json
└── scripts/
    └── memory_manager.py
```

**Script memory_manager.py:**
- `python3 .memory/scripts/memory_manager.py init`: Inicializa el banco
- `python3 .memory/scripts/memory_manager.py status`: Muestra estado
- `python3 .memory/scripts/memory_manager.py update`: Actualiza timestamp

**Independencia:**
- from_aibos: true
- from_agy: true
- from_opencode: true

**Registro en Hindsight:** Sí - memoria del proyecto registrada

---

## 8. LECCIONES APRENDIDAS

### 8.1 Sobre desarrollo en este entorno

1. Los tiempos de importación de Python son lentos (~30-40 segundos)
2. Los tests de pytest tardan mucho en recolectar (~38-40 segundos)
3. Es preferible verificar recolección de tests antes de ejecución completa
4. CLI --help es una verificación rápida útil

### 8.2 Sobre estructura del paquete

1. La separación en submódulos (validation, fs, text) fue buena decisión
2. Los imports circulares pueden ser problemáticos - usar importación directa
3. Los aliases para compatibilidad resuelven problemas de nombres

### 8.3 Sobre el proyecto

1. La independencia de AibOS/AiboT fue lograda
2. El banco de memoria separado funciona correctamente
3. Los adapters para múltiples entornos están estructurados

---

## 9. PRÓXIMOS PASOS

### Prioridad 1: Verificación
- [ ] Ejecutar 33 tests de seguridad completamente
- [ ] Verificar CLI commands (doctor, inspect, extract)
- [ ] Verificar CLI commands (batch, status, cancel, export, cleanup, config, self-test, models)

### Prioridad 2: Documentación
- [ ] Completar ADR (Architecture Decision Records)
- [ ] Verificar ejemplos de uso

### Prioridad 3: Publicación
- [ ] Hacer push a GitHub
- [ ] Crear release si es necesario
- [ ] Publicar en PyPI si es necesario

### Prioridad 4: Mejoras
- [ ] Revisar documentación existente
- [ ] Mejorar tests si es necesario
- [ ] Agregar más funcionalidad según necesidades

---

## 10. CONTACTO Y RECURSOS

**Repositorio:** https://github.com/chin2901/video-intake-knowledge
**Directorio:** /srv/video-intake-knowledge/
**CLI:** `python3 -m video_intake_core.cli` o `video-intake`
**Banco de memoria:** /srv/video-intake-knowledge/.memory/
**Gestión del banco:** `python3 .memory/scripts/memory_manager.py <init|status|update>`

**Lenguaje de salida:** Español (castellano peninsular)
**Modelo preferido:** Gratuito (solar-pro4:free, nvidia/nemotron-3.5-lightning:free)
**Plataforma:** Hermes Agent (perfil default)