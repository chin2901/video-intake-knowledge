# Solución de problemas de video-intake-knowledge

## Problemas comunes

### Comando `video-intake` no encontrado

**Causa:** El paquete no está instalado o el entorno virtual no está activado.

**Solución:**
```bash
# Activar entorno virtual
source .venv/bin/activate  # o el que usaste

# O instalar globalmente
pip install -e .

# Verificar instalación
video-intake doctor
```

### `ffmpeg` no encontrado

**Causa:** FFmpeg no está instalado o no está en PATH.

**Solución:**
```bash
# Linux (Debian/Ubuntu)
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows (WSL)
sudo apt-get install ffmpeg
# o descargar desde https://ffmpeg.org/download.html
```

### `tesseract` no encontrado

**Causa:** Tesseract no está instalado o no está en PATH.

**Solución:**
```bash
# Linux (Debian/Ubuntu)
sudo apt-get install tesseract-ocr libtesseract-dev

# macOS
brew install tesseract

# Windows
# Descargar desde https://github.com/UB-Mannheim/tesseract/wiki
```

### Error de transcripción: "modelo no encontrado"

**Causa:** El modelo de Whisper no está descargado o no está en el path esperado.

**Solución:**
```bash
# Verificar modelos disponibles
video-intake models list

# Instalar modelo explícitamente
video-intake models install tiny
video-intake models install base
video-intake models install small

# Verificar instalación
video-intake models verify
```

### Error de OCR: "sin resultado" o "baja calidad"

**Causa:** El frame no tiene texto legible, o el OCR no pudo procesarlo.

**Solución:**
- Verificar que el frame se puede abrir como imagen.
- Probar con otros frames del mismo vídeo.
- Ajustar el preprocesado de OpenCV (umbral, escala de grises, etc.).
- Si el vídeo tiene diagramas complejos, el OCR puede no ser suficiente.
  Considerar usar un modelo de visión si está disponible y la política lo permite.

### URL de YouTube no funciona

**Causa:** La URL es inválida, el vídeo fue eliminado, o yt-dlp no puede
accesarlo por cambios en la plataforma.

**Solución:**
- Verificar que la URL es correcta.
- Probar con `video-intake inspect URL` para ver si el sistema puede acceder.
- Si el vídeo fue eliminado, no hay solución. Ofrecer adjuntar el archivo local.
- Si hay un problema con yt-dlp, verificar que está actualizado:
  ```bash
  pip install -U yt-dlp
  ```

### URL de Facebook no funciona

**Causa:** Facebook tiene protecciones anti-bot que pueden bloquear yt-dlp.
El vídeo puede ser privado o requerir autenticación.

**Solución:**
- Verificar que el vídeo es público.
- Si el vídeo requiere autenticación, adjuntar el archivo local o proveer
  subtítulos obtenidos legalmente.
- No se implementan mecanismos para eludir protecciones de Facebook.

### Vídeo demasiado grande / timeout

**Causa:** El vídeo excede los límites configurados o tarda demasiado en
procesarse.

**Solución:**
- Aumentar los límites en la configuración:
  ```yaml
  limits:
    max_video_duration_minutes: 600
    timeout_seconds: 3600
  ```
- O usar un archivo local en lugar de descargar.
- Verificar espacio disponible en disco.

### Error de memoria: "banco no encontrado"

**Causa:** El banco de memoria especificado no existe o no está disponible
en el host.

**Solución:**
- Listar bancos disponibles con `video-intake memory list-banks`.
- Crear un nuevo banco con `video-intake memory create-bank`.
- Si el host no soporta memoria nativa, exportar a archivo Markdown/JSON.

### No se detecta el vídeo en el mensaje

**Causa:** El sistema no detectó la URL de vídeo en el mensaje.

**Solución:**
- Verificar que la URL es de una plataforma soportada.
- Si se usó un enlace acortado o redirigido, verificar que el sistema puede
  resolverlo.
- Si el sistema no puede detectarlo automáticamente, invocar manualmente:
  ```bash
  video-intake inspect URL
  ```

## Logs y depuración

### Ver logs de un job

```bash
ls artifacts/<job-id>/logs/
cat artifacts/<job-id>/logs/*.log
```

### Modo debug

```bash
video-intake extract URL --select transcript --verbose
```

### Verificar configuración

```bash
video-intake config validate
```

### Verificar dependencias

```bash
video-intake doctor
```

## Reports de error

Si el problema no está en esta lista, reportar con:

1. Versión de video-intake-knowledge (`video-intake --version`).
2. Versión de Python (`python3 --version`).
3. Output de `video-intake doctor`.
4. El comando que se ejecutó y el error completo.
5. El tipo de fuente (URL, archivo local, etc.).
6. Si es posible, el archivo de log del job.

## Actualización de dependencias

Si hay problemas después de actualizar:

```bash
# Actualizar yt-dlp
pip install -U yt-dlp

# Actualizar openai-whisper
pip install -U openai-whisper

# Reinstalar el paquete
pip install -e .
```
