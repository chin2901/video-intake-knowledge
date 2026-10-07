import os
import re
import uuid
import logging
import asyncio
from pathlib import Path
import yt_dlp

logger = logging.getLogger('video_extractor')
STORAGE_DIR = Path(os.getenv('STORAGE_DIR', '/app/storage'))

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'

BASE_YDL_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'no_check_certificate': True,
    'geo_bypass': True,
    'socket_timeout': 15,
    'http_headers': {
        'User-Agent': USER_AGENT,
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
    },
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'ios', 'web'],
        }
    }
}

def sanitize_filename(name: str) -> str:
    clean = re.sub(r'[^\w\-_.]', '_', name)
    return re.sub(r'_+', '_', clean).strip('_')

def run_sync_info(url: str) -> dict:
    opts = {
        **BASE_YDL_OPTS,
        'skip_download': True,
        'extract_flat': False,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            'title': info.get('title', 'Video sin titulo'),
            'duration': info.get('duration', 0),
            'uploader': info.get('uploader') or info.get('channel', 'Desconocido'),
            'thumbnail': info.get('thumbnail', ''),
            'description': (info.get('description') or '')[:500],
            'view_count': info.get('view_count', 0),
            'url': url
        }

async def extract_info(url: str) -> dict:
    return await asyncio.to_thread(run_sync_info, url)

def run_sync_download_video(url: str, task_id: str) -> Path:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    out_tmpl = str(STORAGE_DIR / f'{task_id}_%(title).40s.%(ext)s')
    opts = {
        **BASE_YDL_OPTS,
        'format': 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': out_tmpl,
        'merge_output_format': 'mp4',
        'max_filesize': 500 * 1024 * 1024,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    
    for f in STORAGE_DIR.glob(f'{task_id}_*'):
        if f.suffix in ['.mp4', '.mkv', '.webm']:
            clean_name = sanitize_filename(f.name)
            target = STORAGE_DIR / clean_name
            if f != target:
                f.rename(target)
                return target
            return f
    raise FileNotFoundError('No se encontro el archivo de video procesado')

async def download_video(url: str, task_id: str) -> Path:
    return await asyncio.to_thread(run_sync_download_video, url, task_id)

def run_sync_download_audio(url: str, task_id: str) -> Path:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    out_tmpl = str(STORAGE_DIR / f'{task_id}_%(title).40s.%(ext)s')
    opts = {
        **BASE_YDL_OPTS,
        'format': 'bestaudio/best',
        'outtmpl': out_tmpl,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    
    for f in STORAGE_DIR.glob(f'{task_id}_*.mp3'):
        clean_name = sanitize_filename(f.name)
        target = STORAGE_DIR / clean_name
        if f != target:
            f.rename(target)
            return target
        return f
    raise FileNotFoundError('No se encontro el archivo de audio procesado')

async def download_audio(url: str, task_id: str) -> Path:
    return await asyncio.to_thread(run_sync_download_audio, url, task_id)

def run_sync_generate_markdown(url: str, task_id: str) -> tuple[Path, str]:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    opts = {
        **BASE_YDL_OPTS,
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['es', 'en'],
        'subtitlesformat': 'vtt/srt/best',
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    
    title = info.get('title', 'Video sin titulo')
    uploader = info.get('uploader') or info.get('channel', 'Desconocido')
    duration = info.get('duration', 0)
    mins = duration // 60
    secs = duration % 60
    description = info.get('description', 'Sin descripcion disponible.')
    
    sub_text = "No se encontraron subtitulos o transcripcion automatica disponible en la fuente."
    try:
        sub_opts = {
            **BASE_YDL_OPTS,
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['es', 'en'],
            'outtmpl': str(STORAGE_DIR / f'{task_id}_sub'),
        }
        with yt_dlp.YoutubeDL(sub_opts) as ydl:
            ydl.download([url])
        
        for sub_file in STORAGE_DIR.glob(f'{task_id}_sub*'):
            raw = sub_file.read_text(encoding='utf-8', errors='ignore')
            lines = []
            for line in raw.splitlines():
                line = line.strip()
                if not line or '-->' in line or line.startswith('WEBVTT') or line.isdigit():
                    continue
                if not lines or lines[-1] != line:
                    lines.append(line)
            if lines:
                sub_text = '\n'.join(lines[:300])
            sub_file.unlink(missing_ok=True)
            break
    except Exception as e:
        logger.warning(f'Subtitulos no extraibles: {e}')

    md_content = f"""# Resumen de Conocimiento: {title}

- **Fuente:** [{url}]({url})
- **Autor / Canal:** {uploader}
- **Duracion:** {mins}m {secs}s
- **Fecha de Ingesta:** Ingestado via Video-Intake-Knowledge

---

## 📌 Descripcion y Contexto Original
{description}

---

## 📝 Transcripcion / Contenido Verbal
{sub_text}

---
*Generado automaticamente con Video Intake Knowledge — Zero-Install Web Service*
"""
    clean_title = sanitize_filename(title[:40])
    md_file = STORAGE_DIR / f'{task_id}_{clean_title}.md'
    md_file.write_text(md_content, encoding='utf-8')
    return md_file, md_content

async def generate_markdown(url: str, task_id: str) -> tuple[Path, str]:
    return await asyncio.to_thread(run_sync_generate_markdown, url, task_id)
