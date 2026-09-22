---
name: video-intake-knowledge
description: AGY tool and skill for video acquisition, multi-layered extraction, and knowledge routing.
version: 1.0.0
---

[[tool:video-intake-knowledge]]

# Herramienta y Skill: video-intake-knowledge para AGY

Detectar, adquirir, analizar y convertir vídeos (YouTube, Facebook, Instagram, TikTok y archivos locales) en conocimiento estructurado y activos reutilizables para agentes de IA.

## 1. Comandos Disponibles

- `video-intake doctor` — Diagnóstico del entorno y herramientas nativas
- `video-intake inspect <url_o_archivo>` — Inspección instantánea (<300ms) de metadatos de vídeo
- `video-intake extract <url_o_archivo> --select <capas>` — Extracción directa por capas
- `video-intake interactive <url_o_archivo>` — Orquestador conversacional interactivo en 2 fases
- `video-intake batch <archivo_de_urls>` — Procesamiento concurrente por lotes
- `video-intake status <job_id>` — Estado de trabajos en ejecución
- `video-intake artifacts <job_id>` — Listado de artefactos generados
- `video-intake export <job_id> [--format markdown|json|html]` — Exportar resultados
- `video-intake proposals --scaffold {skill,tool,agent,all}` — Scaffolding dinámico de activos
- `video-intake memory {list,search,get,export,import}` — Gestión de memoria aislada

---

## 2. Protocolo Operativo en 2 Fases

Cuando el usuario proporcione un enlace o archivo de vídeo, el agente DEBE ejecutar el flujo conversacional en 2 fases:

### FASE 1: Menú interactivo de capas de extracción
Preguntar qué capas procesar del material detectado:
```text
¿Qué necesitas extraer del vídeo?
  [1] Descarga del vídeo de manera local
  [2] Descarga del audio del vídeo de manera local
  [3] Transcripción de audio (con timestamps)
  [4] Contexto basado en audio (resumen, puntos clave y tópicos)
  [5] Contexto extraído de manera visual (fotogramas y OCR para diagramas y esquemas)
  [6] Todo lo anterior (1, 2, 3, 4 y 5)
  [0] Cancelar
```

**Ejecución:**
```bash
video-intake extract "<URL_O_ARCHIVO>" --select <SELECCION>
```

---

### FASE 2: Enrutamiento inteligente de conocimiento
Una vez completada la extracción en `artifacts/<job-id>/`:
```text
Extracción completada con éxito. ¿Qué deseas hacer con el conocimiento extraído?
  [1] Aplicarlo como mensaje a la sesión en curso (mostrar en el chat)
  [2] Añadirlo al contexto de la sesión en curso (como memoria de trabajo compacta)
  [3] Añadirlo a un banco de memoria existente en ~/.video-intake/
  [4] Crear un nuevo banco de memoria dedicado en ~/.video-intake/
  [5] Idear y construir herramientas/skills/agentes mediante análisis inteligente y scaffolding automático
  [6] Conservar únicamente los artefactos locales en disco
```

Si el usuario elige **[5]**, ejecutar:
```bash
video-intake proposals --scaffold {skill,tool,agent,all} --output ./generated
```
- **SKILL:** Genera `SKILL.md` con checklist y procedimiento derivado del vídeo.
- **TOOL:** Genera `tool.py` ejecutable con CLI (`argparse`) y lógica extraída.
- **AGENTE:** Genera `agent.yaml` y prompt de sistema en `prompts/system.md`.

---

## 3. Seguridad y Aislamiento de Memoria
- Cero bases de datos en Git: Todo almacenamiento persistente reside estrictamente en `~/.video-intake/` (`memory.db`).
- Validación SSRF determinista contra loopback y rangos privados.
- Sanitización de subtítulos y OCR contra inyecciones de prompts en LLMs.
