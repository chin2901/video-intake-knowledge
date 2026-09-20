# =============================================================================
# ady/README.md — Adaptador AGY para video-intake-knowledge
# ==========================================
#
# Este directorio contiene adaptadores de integración para el entorno AGY.
#
# AGY es un entorno de agentes de IA. Este adaptador proporciona:
# - SKILL.md portable compatible con SKILL.md
# - Scripts de instalación/desinstalación
# - Ejemplos de uso
#
# =============================================================================

# Contenido

- `SKILL.md` — Skill portable para AGY (compatível con Agent Skills / SKILL.md)
- `install.sh` — Script de instalación para AGY
- `uninstall.sh` — Script de desinstalación para AGY
- `README.md` — Esta documentación
- `config.example.yaml` — Configuración de ejemplo

# Instalación

```bash
cd adapters/agy
bash install.sh
```

# Uso

Después de instalar, las herramientas de video-intake-knowledge están
disponibles en la línea de comandos y se pueden integrar con el flujo de
trabajo de AGY según las capacidades del host.

# Configuración

Edita `config.example.yaml` para ajustar políticas de transcripción,
extracción visual, almacenamiento y memoria según las capacidades de tu
entorno AGY.

# Ver también

- skill/SKILL.md — Skill portable genérico
- docs/portability.md — Matriz de compatibilidad por host
- config/default.yaml — Configuración por defecto
