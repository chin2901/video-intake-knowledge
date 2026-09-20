# Fuentes soportadas por video-intake-knowledge

## Resumen

El sistema soporta adquisición de vídeos desde múltiples plataformas y archivos
locales. La lista de fuentes soportadas es:

| Fuente | Tipo | Método de adquisición |
|--------|------|----------------------|
| YouTube | Remota | yt-dlp + captions |
| youtu.be | Remota | yt-dlp (short URL) |
| YouTube Shorts | Remota | yt-dlp |
| Facebook Video | Remota | yt-dlp + captions |
| Facebook Watch | Remota | yt-dlp |
| Instagram Reels | Remota | yt-dlp |
| Instagram Video | Remota | yt-dlp |
| TikTok | Remota | yt-dlp (si está disponible) |
| Archivos locales | Local | ffprobe + lectura directa |

## Plataformas específicas

### YouTube

Soporta:
- `youtube.com/watch?v=VIDEO_ID`
- `youtu.be/VIDEO_ID`
- `youtube.com/shorts/VIDEO_ID`
- Enlaces compartidos compatibles con yt-dlp

Qué se puede extraer:
- Vídeo completo (cualquier resolución disponible)
- Audio (cualquier calidad disponible)
- Subtítulos oficiales (automáticos o generados por la comunidad)
- Metadatos (título, describición, duración, etc.)

Limitaciones:
- Los vídeos privados, eliminados o con restricciones geográficas no son accesibles.
- No se implementan mecanismos para eludir DRM ni restricciones de plataforma.

### Facebook

Soporta:
- `facebook.com/watch/...`
- `facebook.com/share/v/...`
- Vídeos de perfil y páginas públicas

Qué se puede extraer:
- Vídeo completo (si es público)
- Audio
- Subtítulos (si están disponibles y son accesibles)

Limitaciones:
- Facebook tiene protecciones anti-bot que pueden bloquear la descarga.
- Los vídeos privados o con restricciones no son accesibles.
- La disponibilidad depende de la política de Facebook en cada momento.

### Instagram

Soporta:
- Reels (`instagram.com/reel/...`)
- Vídeos de perfil (`instagram.com/p/...`, `instagram.com/tv/...`)

Qué se puede extraer:
- Vídeo completo (si es público)
- Audio

Limitaciones:
- Los vídeos privados no son accesibles.
- Algunos vídeos pueden requerir autenticación que no se implementa.
- La disponibilidad depende de la política de Instagram.

### TikTok

Soporta:
- `tiktok.com/@user/video/ID`
- Enlaces compartidos compatibles

Qué se puede extraer:
- Vídeo completo (si está disponible públicamente)
- Audio

Limitaciones:
- Algunos vídeos pueden estar restringidos geográfica o privadamente.
- TikTok cambia frecuentemente sus protecciones anti-bot.
- No se implementan mecanismos para eludir estas protecciones.

### Archivos locales

Soporta formatos:
- MP4
- MOV
- MKV
- WebM
- AVI
- M4V
- MPEG
- MPG
- FLV
- WMV

Qué se puede extraer:
- Audio (vía FFmpeg)
- Fotogramas (vía FFmpeg)
- Subtítulos embebidos (si existen)
- Metadatos (vía ffprobe)

Validación:
- Se verifica la extensión y el tipo MIME real.
- Se crea un hash SHA-256 para deduplicación y trazabilidad.
- Se valida que el archivo sea legítimo (no un symlink malicioso, no un archivo
  que contenga scripts, etc.).

## Fuentes no soportadas

Estas fuentes no están soportadas y el sistema no debe intentar acceder a ellas:

- Vídeos protegidos por DRM (Netflix, Disney+, etc.)
- Vídeos detrás de paywall
- Vídeos con restricciones de edad no autenticadas
- Vídeos privados que requieren autenticación
- Vídeos en plataformas no listadas arriba

Si el usuario intenta procesar una fuente no soportada, el sistema informa del
motivo y ofrece alternativas seguras (adjuntar el archivo local, proporcionar
subtítulos, usar una URL pública).

## Extensibilidad

La arquitectura de adquisición es modular. Se puede añadir soporte para nuevas
fuentes implementando las interfaces:

- `SourceInspector` — inspeccionar metadatos sin descargar.
- `SourceResolver` — resolver la URL real.
- `CaptionProvider` — obtener subtítulos.
- `VideoDownloader` — descargar el vídeo.
- `AudioExtractor` — extraer el audio.

Cada nueva fuente se declara en `config.default.yaml` bajo `acquisition.enabled_sources`
y se documenta en este archivo.
