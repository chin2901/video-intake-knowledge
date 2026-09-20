# Contributing to video-intake-knowledge

¡Gracias por tu interés en contribuir! Este documento describe el proceso y
las convenciones para colaborar en el proyecto.

## Cómo puedo contribuir

### Reportar bugs

Los bugs se reportan abriendo un issue en:
`https://github.com/aibos/video-intake-knowledge/issues`

Incluye:
- Descripción del bug.
- Pasos para reproducirlo.
- Resultado esperado vs. resultado obtenido.
- Versión de video-intake-knowledge y Python.
- Output de `video-intake doctor`.
- Sistema operativo y versión.

### Request de características

Las features se solicitan abriendo un issue con la etiqueta `enhancement`.

Incluye:
- Descripción de la feature.
- Caso de uso.
- Alternativas consideradas.

### Contribuir código

1. Fork del repositorio.
2. Crea una rama: `git checkout -b feat/mi-feature`.
3. Haz tus cambios.
4. Añade o_actualiza pruebas.
5. Asegúrate de que todas las pruebas pasan.
6. Abre un pull request.

## Proceso de pull request

1. Abre un PR desde tu rama hacia `main`.
2. Usa la plantilla de PR (`.github/pull_request_template.md`).
3. Describe qué hace el PR y por qué.
4. Incluye pruebas relevantes.
5. Marca los checkboxes de la plantilla.
6. Espera review de un mantenedor.

## Convenciones de código

### Python

- PEP 8 para estilo.
- Type hints para todas las funciones públicas.
- Docstrings en Google style para funciones y clases públicas.
- Líneas máximas de 100 caracteres.
- Imports ordenados: stdlib, third-party, local.

### Shell scripts

- Bash 4+ compatible.
- set -euo pipefail al inicio.
- Variables en mayúsculas.
- Funciones con nombres descriptivos.
- Log de acciones importantes.
- Manejo de errores explícito.

### Markdown

- Encabezados en formato ATX (#, ##, etc.).
- Listas con bullet points o numbered.
- Code blocks con lenguaje especificado.
- Enlaces con texto descriptivo.

## Pruebas

El proyecto incluye varias capas de pruebas:

- **Unitarias** (`tests/unit/`) — Pruebas de módulos individuales.
- **De contrato** (`tests/contract/`) — Verifican la API pública de cada módulo.
- **De integración** (`tests/integration/`) — Prueban el sistema completo.
- **End-to-end** (`tests/e2e/`) — Prueban flujos completos con datos reales.
- **De seguridad** (`tests/security/`) — Prueban la protección contra amenazas.

Para ejecutar:

```bash
make test           # Todas las pruebas
make test-unit      # Solo unitarias
make test-contract  # Solo contrato
make test-integration  # Solo integración
pytest tests/ -v    # Todas con pytest directamente
```

## Convención de commits

Los commits siguen [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` — Nueva funcionalidad.
- `fix:` — Corrección de bug.
- `docs:` — Cambios en documentación.
- `style:` — Cambios de estilo sin cambios funcionales.
- `refactor:` — Refactorización sin cambios funcionales ni bug fixes.
- `test:` — Añadir o_actualizar pruebas.
- `chore:` — Tareas de mantenimiento.
- `ci:` — Cambios en CI/CD.
- `perf:` — Mejora de rendimiento.
- `security:` — Mejora de seguridad.

Ejemplo: `feat: añadir soporte para Instagram Reels`

## Ramas

- `main` — Rama principal, siempre estable.
- `develop` — Rama de desarrollo (opcional).
- `feat/<nombre>` — Para nuevas funcionalidades.
- `fix/<nombre>` — Para correcciones de bugs.
- `docs/<nombre>` — Para cambios de documentación.
- `chore/<nombre>` — Para tareas de mantenimiento.

## Versionado

El proyecto usa [SemVer](https://semver.org/):
- Major: cambios incompatimibles.
- Minor: nuevas funcionalidades backward-compatible.
- Patch: correcciones de bugs backward-compatible.

## Ética y seguridad

- No introducir nunca secretos, keys, tokens o contraseñas en el código.
- Respetar las políticas de las plataformas de vídeo (YouTube, Facebook, etc.).
- No implementar elusión de DRM, paywalls, autenticación, etc.
- Tratar todo contenido extraído como DATOS NO CONFIABLES.
- Reportar vulnerabilidades siguiendo `SECURITY.md`.

## Code of Conduct

Sigue `CODE_OF_CONDUCT.md`. Se espera respeto, inclusión y colaboración
constructiva de todos los colaboradores.

## Contacto

- Issues: `https://github.com/aibos/video-intake-knowledge/issues`
- Email: hermes@aibos.local (para asuntos importantes)
