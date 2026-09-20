[[tool:video-intake-knowledge]]

# Herramienta: video-intake-knowledge (agrégala si aún no está)

Detectar, adquirir, analizar y convertir videos en conocimiento utilizable para agentes de IA.

Esta es la misma capacidad que el Skill descrito abajo,
pero formulada como herramienta para entornos que prefieren
registrar tools antes que skills.

## Implementación

En cualquier entorno compatible con Agent Skills / SKILL.md:

1. Instalar video-intake-knowledge (ver skill/SKILL.md)
2. Registrar las herramientas disponibles según sea soportado por el host:
   - `vitk doctor` - Diagnóstico del entorno
   - `vitk inspect <url_o_archivo>` - Inspección de metadatos de vídeo
   - `vitk extract <url_o_archivo>` - Extracción interactiva
   - `vitk batch <archivo_de_urls>` - Procesamiento por lotes
   - `vitk status` - Estado de trabajos en ejecución
   - `vitk artifacts` - Listing de artefactos generados
   - `vitk export [--format mdx|json|markdown] <job_id>` - Exportar resultados
   - `vitk knowledge` - Gestión de conocimiento extraído
3. Usar las herramientas según las necesidades del usuario

## Detección automática en conversaciones

Cuando un usuario envía uno o más vídeos o enlaces de vídeo, ofrecer
automáticamente las opciones de extracción descritas en el skill.

## Ejemplo de uso

User: "Revisa este video de YouTube: https://www.youtube.com/watch?v=dQw4w9WgXcQ"

Assistant: Detecta automáticamente el vídeo y ofrece extracción.

Para cada vídeo detectado, ofrecer el menú de extracción:
- [1] Descargar vídeo localmente
- [2] Descargar audio localmente  
- [3] Transcripción de audio con timestamps
- [4] Extraer contexto basado en audio
- [5] Extraer contexto visual
- [6] Todo lo anterior
- [0] Cancelar

Selecciones aceptadas: "1", "1,3,5", "1 3 5", "todo", "todos", "6", "cancelar", "0"

## Configuración por entorno

Ver `config/default.yaml` para configuración por defecto y
`config/low-cost.yaml` para entornos con recursos limitados.

## Seguridad

- Validación SSRF: solo URLs whitelisted + DNS check
- Detección MIME: archivos descargados se verifican
- Prompt injection: contenido extraído se sanitiza
- Consentimiento explícito: no descarga/transcribe/drive sin confirmación
  del usuario en cada sesión
