---
name: video-intake-knowledge
description: Codex agent skill for automated video detection, transcription, multi-layer extraction, and knowledge scaffolding.
version: 1.0.0
---

# SKILL: Video Intake Knowledge for OpenAI Codex

> Skill universal de ingesta, extracción y estructuración de conocimiento audiovisual optimizada para entornos OpenAI Codex y Codex CLI.

## 1. Activación
Se activa automáticamente cuando el usuario proporciona URLs o archivos locales de vídeo:
- YouTube, Shorts, directos
- Facebook Video / Reels
- Instagram Reels / Posts
- TikTok
- Archivos locales (MP4, MOV, MKV, WebM, AVI, M4V)

## 2. Protocolo de Ejecución en 2 Fases

### FASE 1: Menú interactivo de extracción
Presentar al usuario las opciones de extracción:
```text
¿Qué necesitas extraer del vídeo?
  [1] Descarga del vídeo de manera local
  [2] Descarga del audio del vídeo de manera local
  [3] Transcripción de audio (con timestamps)
  [4] Contexto basado en audio (resumen, puntos clave y tópicos)
  [5] Contexto extraído de manera visual (fotogramas y OCR para diagramas y esquemas)
  [6] Todo lo anterior (1, 2, 3, 4 y 5)
```

**Ejecución:**
```bash
video-intake extract "<URL_O_ARCHIVO>" --select <SELECCION>
# O modo interactivo integral:
video-intake interactive "<URL_O_ARCHIVO>"
```

### FASE 2: Enrutamiento de Conocimiento y Scaffolding
Tras completar la extracción en `artifacts/<job-id>/`:
```text
¿Qué deseas hacer con el conocimiento extraído?
  [1] Aplicarlo como mensaje a la sesión en curso
  [2] Añadirlo al contexto de la sesión en curso (memoria de trabajo)
  [3] Añadirlo a un banco de memoria existente en ~/.video-intake/
  [4] Crear un nuevo banco de memoria dedicado en ~/.video-intake/
  [5] Idear y construir herramientas/skills/agentes mediante análisis inteligente y scaffolding automático
  [6] Conservar únicamente los artefactos locales en disco
```

Si se selecciona [5]:
```bash
video-intake proposals --scaffold {skill,tool,agent,all}
```

## 3. Comandos Principales
```bash
video-intake doctor
video-intake inspect "<URL_O_ARCHIVO>"
video-intake extract "<URL_O_ARCHIVO>" --select 1,3,5
video-intake proposals --scaffold all
video-intake status <JOB_ID>
video-intake memory list
```

## 4. Aislamiento de Memoria
Toda persistencia se gestiona externamente en `~/.video-intake/` (`memory.db`). El repositorio de trabajo se mantiene 100% limpio.
