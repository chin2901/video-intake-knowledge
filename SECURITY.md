# Security Policy de video-intake-knowledge

## Política de divulgación responsable de vulnerabilidades

Si descubres una vulnerabilidad en video-intake-knowledge, te rogamos que la
reportes de forma responsable siguiendo esta política.

## Cómo reportar

**No reveles públicamente la vulnerabilidad** hasta que hayamos tenido la
oportunidad de corregirla.

Métodos de reporte:

1. **Proyecto GitHub** — Abre un issue en
   `https://github.com/aibos/video-intake-knowledge/issues`
   con la etiqueta `security`. (Público, pero la etiqueta indica que es un
   issue de seguridad.)

2. **Correo directo** — `security@aibos.local` (si está configurado).
   Este método es preferible para vulnerabilidades críticas.

3. **Contacto privado** — Si tienes acceso al mantenedor, contacta
   directamente por los canales privados acordados.

## Qué incluir en el reporte

- Descripción de la vulnerabilidad.
- Pasos para reproducirla.
- Impacto potencial.
- Versiones afectadas.
- Cualquier mitigación conocida.
- Si has descubierto la vulnerabilidad de forma independiente o a través de
  otro medio.

## Lo que no hacemos

- No ofrecemos recompensas por bugs (bug bounty program).
- No garantizamos respuesta inmediata (dependemos de voluntarios/mantenedores).
- No aceptamos reportes de vulnerabilidades en dependencias de terceros
  directamente a través de este proyecto (reporta esas vulnerabilidades a los
  mantenedores de la dependencia afectada).

## Proceso interno

1. Recibimos el reporte.
2. Lo confirmamos y avaliamos.
3. Creamos un fix y lo revisamos.
4. Hacemos release de la versión corregida.
5. Comunicamos el fix y damos las gracias al reporter (si el reporter lo permite).

## Qué se considera vulnerabilidad relevante

- SSRF: que un atacante pueda hacer que el sistema acceda a recursos internos.
- Prompt injection: que contenido de vídeo/transcripción pueda manipular al agente.
- RCE: ejecución remota de código a través de archivos procesados.
- Acceso no autorizado a recursos del sistema.
- Fuga de información sensible (memory banks, logs, etc.).
- Buffer overflows, corrupción de memoria en dependencias nativas.

## Versiones soportadas

Las versiones del projecto con soporte de seguridad son las dos versiones
mayores actuales. Las versiones anteriores pueden tener vulnerabilidades sin
parche.

Para ver las versiones actuales, ver `CHANGELOG.md` y las etiquetas en el
repositorio.

## Gracias

Gracias por ayudar a hacer el proyecto más seguro.
