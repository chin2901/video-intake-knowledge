# Modelo de seguridad de video-intake-knowledge

## Principios

1. **Todo contenido extraído es datos no confiables.** Nunca se inyecta como
   instrucciones al modelo.
2. **El usuario domina sus datos.** El sistema no decide qué conservar.
3. **La seguridad es por capas.** Validación de entrada, protección en ejecución,
   y escaneo de salida.
4. **No se esconde nada.** Los errores, warnings y limitaciones se reportan
   explícitamente.

## Amenazas mitigadas

### Prompt injection

Un atacante puede incrustar instrucciones en un vídeo (transcripción, subtítulos,
OCR de texto en pantalla) que, si se tratan como confiables, pueden manipular
al agente.

**Mitigaciones:**
- Los textos extraídos se marcan como datos, no como instrucciones.
- Se detectan patrones comunes de inyección (instrucciones disfrazadas de
  contenido, encabezados que imitan comandos del sistema).
- `security.prompt_injection_protection` puede activarse/desactivarse.
- Los análisis de build proposal nunca ejecutan contenido sin validación humana.

### SSRF (Server-Side Request Forgery)

Un atacante puede provocar que el sistema acceda a URLs internas (169.254.169.254
para metadatos de AWS, 10.x.x.x, 192.168.x.x, 172.16-31.x.x) si se puede controlar
la URL de entrada.

**Mitigaciones:**
- `security.ssrf_protection` bloquea accesos a rangos de IP privados y de
  metadatos de nube.
- `security.allowed_domains` permite restringir a dominios específicos.
- La validación de URL verifica el origen antes de cualquier redirección.

### Archivos maliciosos

Un archivo adjunto puede ser ejecutable, puede contener scripts, o puede tener
un tipo MIME que no coincide con la extensión.

**Mitigaciones:**
- Se detecta el tipo MIME real del archivo descargado.
- `security.is_safe_mime()` verifica que el tipo sea el esperado.
- Las extensiones se validan antes de procesar.
- `security.scan_downloaded_files` permite escanear con ClamAV si está disponible.
- Los archivos sospechosos se aíslan en `quarantine/`.

### Límites de recursos

Un vídeo muy grande o una cantidad excesiva de vídeos puede agotar recursos.

**Mitigaciones:**
- `limits.max_video_duration_minutes`
- `limits.max_download_size_mb`
- `limits.max_batch_items`
- `limits.max_parallel_jobs`
- `limits.timeout_seconds`

### Nombres de archivo maliciosos

Un archivo puede tener un nombre diseñado para explotar vulnerabilidades en
el manejo de rutas.

**Mitigaciones:**
- `security.sanitize_filenames` elimina caracteres peligrosos.
- Las rutas se validan para evitar traversal (`../`).

### Datos sensibles

Una transcripción puede contener información confidencial (números, correos,
contraseñas).

**Mitigaciones:**
- `security.redact_sensitive_data` puede activarse para redactar patrones
  comunes de datos sensibles.
- Los logs no incluyen contenido sensible.

## Controles de respuesta

Cuando un vídeo no es accesible de forma legítima, el sistema informa con
claridad:

- Motivo del fallo.
- Alternativas seguras (adjuntar archivo local, proporcionar subtítulos,
  usar URL pública, configurar credenciales legítimas).

No se implementan mecanismos para eludir DRM, paywalls, controles de edad,
autenticación, protecciones anti-bot o restricciones geográficas.

## Secretos

Los secretos se obtienen exclusivamente de:
- Variables de entorno.
- Mecanismos de secretos del host.
- Archivos locales explícitamente excluidos de Git.

Nunca se guardan secretos dentro del repositorio.

## Retención y privacidad

- Los artefactos se conservan según `config.storage.artifact_retention_days`.
- La memoria requiere confirmación explícita del usuario.
- El sistema no envía datos a terceros sin que el usuario lo autorice.
- Los logs no incluyen contenido sensible por defecto.

## Auditoría

- Cada job genera registros en `logs/` con timestamps.
- El manifest registra herramientas, versiones y parámetros.
- Los hashes SHA-256 permiten verificar la integridad de los artefactos.
- `video-intake doctor` verifica la configuración de seguridad.
