#!/bin/bash
# Script de actualizacion rapida de yt-dlp y dependencias
echo 'Actualizando yt-dlp dentro del contenedor...'
docker exec -it video-intake-web pip install --upgrade --no-cache-dir yt-dlp
docker compose restart video-web
echo 'Listo! Version actual:'
docker exec video-intake-web yt-dlp --version
