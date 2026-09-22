---
name: video-intake-knowledge
description: Claude Code integration manifest for universal video intake, transcription, and knowledge routing.
version: 1.0.0
canonical: ../../SKILL.md
---

# Video Intake Knowledge — Claude Code Skill Manifest

Este manifiesto integra la skill universal `video-intake-knowledge` en el entorno **Claude Code**.

## Especificación Canónica
La especificación operativa autoritativa reside en el Single Source of Truth (SSoT):
👉 **[SKILL.md](../../SKILL.md)**

## Flujo Operativo en Claude Code
1. **Detección Automática:** Cuando el usuario provee una URL (YouTube, Facebook, Instagram, TikTok) o archivo local (.mp4, .mov, etc.).
2. **Fase 1 (Menú de Extracción):** Consultar qué capas extraer (1: Vídeo, 2: Audio, 3: Transcripción con timestamps, 4: Contexto de audio, 5: Contexto visual OCR, 6: Todo).
   - Comando: `video-intake extract "<URL>" --select <CAPAS>` o `video-intake interactive "<URL>"`
3. **Fase 2 (Enrutamiento de Conocimiento):** Consultar destino:
   - [1] Mostrar como mensaje en la sesión de Claude Code
   - [2] Inyectar como memoria de trabajo compacta en la sesión
   - [3] Guardar en banco de memoria existente en `~/.video-intake/`
   - [4] Crear un nuevo banco de memoria dedicado en `~/.video-intake/`
   - [5] Generar andamiaje funcional con `video-intake proposals --scaffold {skill,tool,agent,all}`
   - [6] Conservar únicamente artefactos locales en `artifacts/`

## Aislamiento de Memoria
Persistencia aislada en `~/.video-intake/memory.db`. Cero bases de datos en el repositorio Git.
