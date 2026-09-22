# Original User Request

## 2026-09-21T22:58:55Z

Equipo completo de ingeniería multi-agente (arquitectura de sistemas, optimización de rendimiento, QA y testing, seguridad informática y documentación técnica de élite).

Elevar el repositorio y skill universal `video-intake-knowledge` a un nivel de excelencia de ingeniería de clase mundial (estándar de proyectos de código abierto con +100.000 estrellas): máximo rendimiento, fluidez determinista, arquitectura limpia, seguridad blindada y experiencia conversacional de agentes impecable.

Working directory: /srv/video-intake-knowledge
Integrity mode: development

## Requirements

### R1. Motor de Ingesta y Extracción de Alto Rendimiento
Optimizar el núcleo de adquisición y extracción audiovisual (YouTube, Facebook, Instagram, TikTok y archivos locales). Implementar ejecución paralela de lotes (batch processing eficiente), streaming directo de metadatos con `ffprobe` e inspección instantánea (< 300ms), bajo consumo de CPU y memoria RAM, y fallbacks deterministas ante cambios de firmas o restricciones de plataformas remotas, priorizando siempre herramientas nativas (yt-dlp, ffmpeg) antes de requerir modelos de IA.

### R2. Experiencia de Agente Universal (SKILL.md) de Grado Top-Tier
Perfeccionar la especificación canónica `SKILL.md` y sus adaptadores para que la experiencia conversacional interactiva en 2 fases sea 100% fluida y natural en todos los entornos de agentes (Hermes Agent, AGY, Claude Code, OpenCode, Codex, Cursor):
- **Fase 1 (Menú de extracción)**: Consulta inmediata y clara al usuario sobre qué capas extraer (vídeo, audio, transcripción temporal con subtítulos, contexto de audio, contexto visual/OCR de diagramas o todo).
- **Fase 2 (Enrutamiento de conocimiento)**: Diálogo interactivo posterior para aplicar lo extraído a la sesión actual, inyectarlo como contexto de trabajo, enviarlo al banco de memoria de ideas externo del usuario, crear un nuevo banco dedicado, o idear y construir herramientas/skills/agentes mediante análisis inteligente y scaffolding automático.

### R3. Blindaje de Seguridad y Aislamiento Estricto de Memoria
Reforzar la arquitectura de seguridad con validación estricta de URLs contra SSRF (bloqueo determinista de rangos privados y loopback sin sobrecarga), prevención de ataques de path traversal, sanitización avanzada de prompts y subtítulos contra inyecciones indirectas, y garantía inviolable de que ningún banco de memoria ni base de datos SQLite se filtre al repositorio Git (aislamiento en espacio de usuario `~/.video-intake/memory.db`).

### R4. Calidad de Código, Tipado Estricto y Suite de Pruebas de Élite
Establecer un estándar de calidad impecable:
- Cobertura de pruebas unitarias, de integración, de contrato y de seguridad superior al 95%.
- Tipado estricto verificado sin advertencias ni errores.
- Análisis estático riguroso con `ruff` sin excepciones.
- Flujos de trabajo de CI/CD para GitHub Actions optimizados para testeo multi-plataforma y auditoría de seguridad.

### R5. Documentación y Experiencia de Desarrollador de Clase Mundial
Crear documentación técnica que compita con los repositorios más reconocidos del mundo: README estructurado y visualmente atractivo con badges informativos, diagramas de arquitectura en Mermaid, especificaciones formales de esquemas de datos, guías de inicio rápido y tutoriales prácticos de integración.

## Acceptance Criteria

### Rendimiento y Robustez
- [ ] Tiempo de inicio de la CLI y de inspección de fuentes locales inferior a 300ms.
- [ ] Procesamiento por lotes concurrente que escale eficientemente sin bloqueos de memoria.
- [ ] Tolerancia a fallos: degradación elegante cuando falten herramientas opcionales (tesseract u openai-whisper) sin interrumpir los flujos principales.

### Compatibilidad y Flujo de Agentes
- [ ] La especificación `SKILL.md` y el script `install.sh` se integran y verifican con éxito en los entornos soportados (Hermes, AGY, Claude Code, OpenCode, Codex).
- [ ] El comando `video-intake proposals --scaffold {skill,tool,agent}` genera andamiajes funcionales y sintácticamente válidos basados en el contenido extraído.

### Seguridad y Memoria
- [ ] Todas las pruebas de fuzzing y ataques simulados (SSRF, prompt injection, path traversal) son neutralizadas y superadas.
- [ ] El árbol de trabajo de Git permanece 100% libre de bases de datos SQLite, archivos `.memory/` o ficheros de caché.

### Verificación Automatizada
- [ ] Cobertura de tests global superior al 95% demostrada con informe automatizado de `pytest --cov`.
- [ ] 0 errores en `ruff check .` y 0 errores en análisis de tipado.
- [ ] Script de diagnóstico de salud (`video-intake doctor` y `./scripts/doctor.sh`) ejecutado con estado 100% Saludable (0 fallos).
