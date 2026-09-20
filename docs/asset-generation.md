# Generación de activos a partir de vídeos extraídos

## Resumen

Cuando el usuario elige "analizar qué se puede construir con este conocimiento"
después de una extracción, el sistema ejecuta un análisis de viabilidad y
produce propuestas estructuradas para crear activos: tools, skills, agentes,
plugins, plantillas, documentos, workflows o knowledge packs.

## Flujo de generación de activos

### 1. Análisis de viabilidad

El sistema analiza el contenido extraído (transcripción, contexto de audio,
contexto visual, conocimiento extraído) y produce una salida estructurada con
propuestas reales y accionables.

Cada propuesta incluye:

- **Nombre propuesto** — Nombre sugerido para el activo.
- **Tipo** — tool, skill, agente, plugin, plantilla, documento, workflow, knowledge pack.
- **Objetivo** — Qué hace el activo.
- **Evidencia** — Qué parte del vídeo justifica la creación.
- **Fiabilidad** — Qué parte es conocimiento fiable vs. requiere validación.
- **Dependencias** — Qué necesita el activo.
- **Herramientas existentes** — Qué se puede reutilizar.
- **Riesgos** — Qué puede fallar o requerir atención.
- **Autonomía recomendada** — Nivel de autonomía sugerido.
- **Pruebas necesarias** — Qué probar.
- **Archivos a crear** — Lista de archivos que se generarían.
- **Compatibilidad por host** — En qué hosts funcionaría.
- **Recomendación** — Crear / no crear / crear como borrador.
- **Motivo** — Razón de la recomendación.

### 2. Reglas de decisión

#### Crear una SKILL si el vídeo aporta:

- Procedimiento repetible.
- Checklist o metodología.
- Buenas prácticas.
- Proceso operativo.
- Conocimiento de dominio estructurado.

#### Crear una TOOL si se necesita:

- Una operación determinista.
- Integración con API.
- Cálculo validado.
- Parser o transformación estructurada.
- Acceso controlado a un recurso.

#### Crear un AGENTE solo si hay:

- Responsabilidad persistente y distinta.
- Objetivos claros.
- Herramientas específicas.
- Límites explícitos.
- Permisos definidos.
- Memoria o estado justificado.
- Frecuencia de uso suficiente.
- Criterios de éxito verificables.

#### Crear un PLUGIN solo si:

- Hace falta interceptar eventos del host.
- Hay que registrar hooks.
- Hay que añadir tools nativas.
- Hay que integrar un lifecycle específico.

#### Crear un KNOWLEDGE PACK o documento si:

- El conocimiento es útil.
- Pero no existe todavía un procedimiento estable para automatizar.

### 3. Pre-creación

Antes de crear cualquier activo, se muestra:

- Lista completa de archivos a crear.
- Cambios previstos.
- Permisos requeridos.
- Herramientas que se usarían.
- Riesgos.
- Plan de pruebas.
- Método de instalación.
- Método de desinstalación o reversión.

Solo se crea tras confirmación explícita del usuario.

### 4. Primera versión: borrador

Todo activo generado inicia como borrador. Debe pasar por:

- Pruebas básicas.
- Análisis de seguridad.
- Revisión humana.

Antes de ser activado por defecto.

## Ejemplo de propuesta

```
== Propuesta de build ==

1. SKILL: video-process-checklist
   Tipo: skill
   Objetivo: Checklist de verificación para procesar vídeos correctamente.
   Evidencia: El vídeo explicó los pasos de inspección, extracción y validación.
   Fiabilidad: Alto (procedimiento explícito en el vídeo).
   Dependencias: Ninguna.
   Herramientas existentes: video-intake doctor, video-intake inspect.
   Riesgos: Ninguno significativo.
   Pruebas: Ejecutar con 3 vídeos de prueba.
   Archivos: skill/video-process-checklist/SKILL.md
   Compatibilidad: Todos los hosts que soporten SKILL.md.
   Recomendación: CREAR
   Motivo: Procedimiento repetible y explícito.

2. TOOL: video-resolution-picker
   Tipo: tool
   Objetivo: Seleccionar la mejor resolución disponible para un vídeo.
   Evidencia: El vídeo mostró cómo elegir resolución según el uso.
   Fiabilidad: Alto (reglas deterministas).
   Dependencias: FFmpeg, yt-dlp.
   Riesgos: Ninguno.
   Pruebas: Probar con vídeos de distintas resoluciones.
   Archivos: tools/video_resolution_picker.py
   Compatibilidad: Todos los hosts.
   Recomendación: CREAR COMO BORRADOR
   Motivo: Operación determinista, útil pero no crítica.
```

## Sin duplicación

Antes de proponer creación, el sistema inspecciona las skills, tools, plugins
y agentes existentes en el entorno y detecta solapamientos. No se propone crear
algo que ya existe.

## Compatibilidad

Cada propuesta incluye información de compatibilidad por host, para que el
usuario sepa en qué entornos funcionaría el activo generado.
