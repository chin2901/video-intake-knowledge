# Video Intake Web Hub 🎬

Servicio web autónomo y ligero desplegado en la VM de Oracle (Ubuntu ARM64) y expuesto al público mediante Cloudflare Tunnel bajo el dominio `video.encinaresgroup.com`.

---

## 🚀 Arquitectura del Sistema

- **Frontend:** HTML5 + Tailwind CSS + FontAwesome + Plus Jakarta Sans (Zero-Install, Zero-Dependencies).
- **Backend:** FastAPI + yt-dlp + ffmpeg en contenedor Python 3.11 ARM64.
- **Conectividad:** Cloudflare Tunnel con protocolo QUIC cifrado punto a punto hacia Madrid (mad05 / mad06), sin puertos WAN abiertos.
- **Endpoints:**
  - `GET /`: Aplicación web moderna.
  - `POST /api/info`: Metadatos rápidos en <1s.
  - `POST /api/process`: Generación de Vídeo MP4, Audio MP3 o Resumen Markdown.
  - `GET /api/download/{filename}`: Entrega de archivo con auto-purga inmediata post-descarga.
  - `GET /api/health`: Monitorización de salud y espacio en disco.

---

## 🛡️ Política de Almacenamiento Zero-Bloat

1. **Auto-purga inmediata:** En cuanto el usuario completa la descarga de un archivo, este se elimina automáticamente del disco.
2. **Worker recurrente:** Limpieza automática cada 60 segundos de cualquier archivo residual que supere los 30 minutos de vida.
3. **Cortafuegos de disco:** Si el espacio libre de la VM cae por debajo de 20 GB, el sistema rechaza nuevas descargas hasta que se libere espacio.
4. **Extracción selectiva:** Las descargas de solo audio o markdown nunca bajan el flujo de vídeo a disco.

---

## 🛠️ Comandos de Operación

- **Ver estado:**
  ```bash
  cd ~/video-intake-web
  docker compose ps
  ```

- **Ver logs en tiempo real:**
  ```bash
  docker logs -f video-intake-web
  docker logs -f video-cloudflared
  ```

- **Reiniciar servicio:**
  ```bash
  docker compose restart
  ```

- **Actualizar yt-dlp:**
  ```bash
  ./update.sh
  ```

---

## 🤖 Antigravity CLI (`agy`) en la VM

La máquina dispone de `agy` nativo para Linux ARM64 en `/home/ubuntu/.local/bin/agy` con la skill de `video-intake` enlazada. Puedes ejecutar:
```bash
agy
```
para interactuar con el agente en terminal en cualquier momento.
