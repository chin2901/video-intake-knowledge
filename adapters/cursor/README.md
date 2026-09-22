# Cursor Adapter: video-intake-knowledge

Integra la skill universal `video-intake-knowledge` en el entorno **Cursor AI**.

## Instalación

```bash
# Global para el usuario:
bash adapters/cursor/install.sh

# O para un espacio de trabajo específico:
bash adapters/cursor/install.sh /ruta/al/proyecto
```

## Características
- Vinculación directa con el estándar canónico `SKILL.md`.
- Reglas operativas optimizadas (`.cursorrules`) con el protocolo de 2 fases:
  - **Fase 1**: Menú de extracción (capas 1 a 6).
  - **Fase 2**: Enrutamiento de conocimiento (mensajes, contexto, banco de ideas, scaffolding con `video-intake proposals --scaffold`).
- Aislamiento estricto de memoria en `~/.video-intake/`.
