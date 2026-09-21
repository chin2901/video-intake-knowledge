# SKILL: Video Intake Knowledge (`SKILL.md`)

> **Habilidad Portable Multi-Entorno** para la ingesta, análisis, transcripción y enrutamiento de conocimiento de vídeos.  
> Compatible de forma nativa con **Hermes Agent, AGY, OpenCode, Claude Code, Codex, Cursor** y cualquier entorno compatible con `SKILL.md`.

---

## 1. Naturaleza del Repositorio: ¿Qué es?
Este repositorio es una **Skill / Habilidad Universal estandarizada (`SKILL.md`)** dotada de un motor de ejecución CLI y scripts utilitarios locales directos (`scripts/` y `video-intake`).  
- **Por qué una Skill:** Es el estándar agnóstico reconocido transversalmente por todos los entornos de agentes.
- **Sin sobreingeniería:** Sigue el principio "Menos es Más" de Tony. Sin tablas intermedias, sin bases de datos pre-empaquetadas dentro de Git, sin dependencias innecesarias de servicios de pago.
- **Cero bancos de memoria en Git:** El repositorio de GitHub está 100% libre de bases de datos SQLite o carpetas `.memory/`. Los bancos de memoria de ideas o de proyectos pertenecen al usuario y se almacenan externamente en `~/.video-intake/memory/` o en la memoria nativa del entorno anfitrión (Hermes host memory, etc.).

---

## 2. Activación y Fuentes Soportadas

Esta habilidad se activa automáticamente en cualquier sesión (en curso o nueva) cuando el usuario proporcione:
- Enlaces de **YouTube** (incluyendo `youtu.be`, Shorts, directos).
- Enlaces de vídeos o Reels de **Facebook** (`facebook.com/watch`, `reel`, etc.).
- Enlaces de **Instagram** Reels o posts de vídeo (`instagram.com/reel`, `/p/`).
- Enlaces de **TikTok** (`tiktok.com/@.../video/...`, `vm.tiktok.com`).
- Archivos locales de vídeo (**MP4, MOV, MKV, WebM, AVI, M4V**).

---

## 3. Protocolo Operativo del Agente (Orquestación en 2 Fases)

Cuando el agente detecte una o varias fuentes de vídeo, **DEBE** seguir obligatoriamente este flujo conversacional:

### FASE 1: Preguntar qué extraer del vídeo
Preguntar al usuario qué elementos necesita procesar de los vídeos proporcionados (puede seleccionar uno, varios o todos):
```text
¿Qué necesitas extraer del vídeo?
  [1] Descarga del vídeo de manera local
  [2] Descarga del audio del vídeo de manera local
  [3] Transcripción de audio (con timestamps)
  [4] Contexto basado en audio (resumen, puntos clave y tópicos)
  [5] Contexto extraído de manera visual (fotogramas y OCR para diagramas, esquemas, flujos de trabajo o animaciones)
  [6] Todo lo anterior (1, 2, 3, 4 y 5)

(Indica una opción, varias separadas por coma como '1, 3, 5', o '6' para todo)
```

### FASE 2: Ejecución autónoma con herramientas locales
Una vez recibida la selección, el agente ejecuta el trabajo utilizando las herramientas y scripts locales del repositorio:
- **Prioridad 1:** Subtítulos oficiales de la plataforma y extracción nativa de audio/vídeo vía `yt-dlp` y `ffmpeg` (0 coste, 0 GPU, máxima velocidad y precisión).
- **Prioridad 2:** Transcripción local mediante Whisper (o modelos rápidos locales si están disponibles).
- **Prioridad 3:** Extracción de fotogramas clave y OCR local con `tesseract` para diagramas y esquemas visuales.
- **Comando de ejecución recomendado:**
  ```bash
  python3 scripts/extract.py "<URL_O_ARCHIVO>" -s <SELECCION>
  # o modo interactivo completo:
  python3 scripts/interactive.py "<URL_O_ARCHIVO>"
  ```

### FASE 3: Preguntar destino / enrutamiento del conocimiento
Una vez completada la extracción y generados los artefactos en `artifacts/<job-id>/`, el agente **DEBE** preguntar al usuario el destino de los resultados:
```text
Extracción completada con éxito. ¿Qué deseas hacer con el conocimiento extraído?
  [1] Aplicarlo como mensaje a la sesión en curso (mostrar en el chat)
  [2] Añadirlo al contexto de la sesión en curso (como memoria de trabajo compacta)
  [3] Añadirlo a un banco de memoria existente (ej. Banco de Ideas)
  [4] Crear un nuevo banco de memoria para añadirlo
  [5] Crear una herramienta, tool, skill o agente con el conocimiento extraído
  [6] Conservar únicamente los artefactos locales en disco
```

#### Comportamiento según la opción elegida:
- **Si elige [3] (Banco de memoria existente):**
  El sistema lista los bancos disponibles en `~/.video-intake/memory/` (ej. `banco-de-ideas`, `trading`, `arquitectura`) o la memoria del host y guarda la entrada.
- **Si elige [4] (Crear nuevo banco de memoria):**
  Solicita el nombre del nuevo banco y lo crea de forma limpia en el directorio de usuario (nunca dentro del repo Git).
- **Si elige [5] (Crear tool, skill o agente):**
  El sistema analiza el contenido (procedimientos, scripts, diagramas de flujo) y presenta **propuestas reales y viables** de lo que se puede construir:
  - **SKILL:** Si el vídeo explica un procedimiento repetible, checklist o metodología operativa.
  - **TOOL:** Si el vídeo describe una función determinista, cálculo, parser o script concreto.
  - **AGENTE:** Si el vídeo define un rol autónomo persistente con responsabilidades claras y herramientas específicas.
  *El sistema solo procede a crear el código tras la aprobación explícita de la propuesta por parte del usuario.*

---

## 4. Instalación Rápida

### En cualquier entorno (Linux / macOS):
```bash
git clone https://github.com/aibos/video-intake-knowledge
cd video-intake-knowledge
./install.sh
```

### Integración directa con plataformas específicas:
```bash
./install.sh --hermes       # Instala skill y plugin en Hermes Agent
./install.sh --agy          # Instala skill en AGY
./install.sh --claude-code  # Instala skill en Claude Code
./install.sh --opencode     # Instala skill en OpenCode
./install.sh --codex        # Instala skill en Codex
./install.sh --all          # Vincula con todos los entornos detectados
```

---

## 5. Referencia de Comandos CLI

El comando `video-intake` y los scripts utilitarios en `scripts/` proporcionan control total:

```bash
# Diagnóstico del sistema y dependencias
video-intake doctor
# o directamente:
./scripts/doctor.sh

# Inspección previa de un vídeo sin descargar
video-intake inspect "https://www.youtube.com/watch?v=EJEMPLO"

# Extracción directa por CLI
video-intake extract "https://www.youtube.com/watch?v=EJEMPLO" --select 1,2,3,4,5
# o mediante script directo:
python3 scripts/extract.py "https://www.youtube.com/watch?v=EJEMPLO" -s 6

# Orquestador interactivo en dos fases
python3 scripts/interactive.py

# Ver estado de trabajos y artefactos
video-intake status <JOB_ID>
video-intake artifacts <JOB_ID>
video-intake export <JOB_ID> --format markdown
```

---

## 6. Estructura de Artefactos Generados

Cada extracción se aísla en `artifacts/<job-id>/` (ignorado en Git):
```text
artifacts/<job-id>/
├── artifacts_manifest.json    # Manifiesto estructurado del trabajo
├── <video_title>.mp4          # Archivo de vídeo local (si se seleccionó 1)
├── <audio_title>.mp3          # Pista de audio extraída (si se seleccionó 2)
├── transcript.md              # Transcripción con timestamps (si se seleccionó 3)
├── audio_context.md           # Resumen y tópicos clave (si se seleccionó 4)
├── visual_context.md          # Diagramas y texto OCR (si se seleccionó 5)
└── frames/                    # Fotogramas clave analizados
```

---

## 7. Garantías de Seguridad y Robustez
- **Validación SSRF nativa:** Bloqueo en tiempo de validación de direcciones privadas (RFC 1918, loopback, CGNAT) sin cálculo previo masivo en memoria.
- **Sanitización de nombres de archivo:** Prevención de ataques de path traversal (`../../`).
- **Protección contra Prompt Injection:** Detección y neutralización de directivas hostiles incrustadas en subtítulos o texto extraído por OCR.
- **Aislamiento de estado:** Todo dato generado es temporal o reside en la memoria exterior del usuario, preservando la limpieza del código fuente.
