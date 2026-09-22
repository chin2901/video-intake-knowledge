---
name: video-intake-knowledge
description: OpenCode integration manifest for universal video intake, transcription, and knowledge routing.
version: 1.0.0
canonical: ../../SKILL.md
---

# Video Intake Knowledge — OpenCode Skill Manifest

Este manifiesto integra la skill universal `video-intake-knowledge` en el entorno **OpenCode**.

## Especificación Canónica
La especificación operativa autoritativa reside en el Single Source of Truth (SSoT):
👉 **[SKILL.md](../../SKILL.md)**

## Flujo Operativo en OpenCode
1. **Detección Automática:** Detección de enlaces (YouTube, Facebook, Instagram, TikTok) y archivos de vídeo locales.
2. **Fase 1 (Menú de Extracción):** Preguntar capas a extraer:
   - [1] Vídeo local
   - [2] Audio local
   - [3] Transcripción con timestamps
   - [4] Contexto de audio (resumen y tópicos)
   - [5] Contexto visual y OCR de diagramas
   - [6] Todo lo anterior
   - Comando: `video-intake extract "<URL>" --select <CAPAS>` o `video-intake interactive "<URL>"`
3. **Fase 2 (Enrutamiento de Conocimiento):** Preguntar destino:
   - [1] Mostrar como mensaje en la sesión de OpenCode
   - [2] Inyectar como memoria de trabajo compacta en la sesión
   - [3] Guardar en banco de memoria existente en `~/.video-intake/`
   - [4] Crear un nuevo banco de memoria dedicado en `~/.video-intake/`
   - [5] Generar andamiaje funcional con `video-intake proposals --scaffold {skill,tool,agent,all}`
   - [6] Conservar únicamente artefactos locales en `artifacts/`

## Aislamiento de Memoria
Persistencia aislada en `~/.video-intake/memory.db`. Cero bases de datos en el repositorio Git.
