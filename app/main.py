import uuid
import asyncio
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from yt_dlp.utils import YoutubeDLError

from app.cleaner import start_cleaner_loop, check_disk_safety, STORAGE_DIR
from app.extractor import extract_info, download_video, download_audio, generate_markdown

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('video_api')

VALID_MODES = {'video', 'audio', 'markdown'}

HTML_FILE = Path(__file__).parent / 'templates' / 'index.html'

@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    cleaner_task = asyncio.create_task(start_cleaner_loop())
    yield
    cleaner_task.cancel()

app = FastAPI(title='Video Intake Knowledge Web', lifespan=lifespan)

class URLRequest(BaseModel):
    url: str

class ProcessRequest(BaseModel):
    url: str
    mode: str  # 'video', 'audio', 'markdown'

@app.get('/', response_class=HTMLResponse)
@app.head('/', response_class=HTMLResponse)
async def home():
    return HTMLResponse(content=HTML_FILE.read_text(encoding='utf-8'))

@app.get('/api/health')
async def health():
    is_safe, free_gb = check_disk_safety()
    return {
        'status': 'healthy' if is_safe else 'warning_disk_low',
        'free_disk_gb': free_gb,
        'storage_safe': is_safe
    }

@app.post('/api/info')
async def get_video_info(req: URLRequest):
    clean_url = req.url.strip() if req.url else ''
    if not clean_url:
        raise HTTPException(status_code=400, detail='La URL no puede estar vacia')
    if not (clean_url.startswith('http://') or clean_url.startswith('https://')):
        raise HTTPException(
            status_code=400, 
            detail=f"URL no valida: '{clean_url}'. Debe comenzar por http:// o https://"
        )

    try:
        info = await extract_info(clean_url)
        return info
    except HTTPException:
        raise
    except YoutubeDLError as e:
        logger.warning(f'Error de cliente en get_video_info ({clean_url}): {e}')
        raise HTTPException(status_code=400, detail=f'No se pudo procesar la URL: {str(e)}')
    except ValueError as e:
        logger.warning(f'Error de valor en get_video_info: {e}')
        raise HTTPException(status_code=400, detail=f'Parametro no valido: {str(e)}')
    except Exception as e:
        logger.error(f'Error inesperado en get_video_info: {e}', exc_info=True)
        raise HTTPException(status_code=500, detail=f'Error interno del servidor: {str(e)}')

async def remove_file_delayed(filepath: Path, delay: float = 0.5):
    await asyncio.sleep(delay)
    try:
        if filepath.exists():
            filepath.unlink()
            logger.info(f'Archivo post-descarga eliminado: {filepath.name}')
    except Exception as e:
        logger.warning(f'Error al auto-eliminar archivo {filepath}: {e}')

@app.post('/api/process')
async def process_video(req: ProcessRequest):
    if req.mode not in VALID_MODES:
        raise HTTPException(
            status_code=400, 
            detail=f"Modo no valido: '{req.mode}'. Debe ser 'video', 'audio' o 'markdown'."
        )

    clean_url = req.url.strip() if req.url else ''
    if not clean_url:
        raise HTTPException(status_code=400, detail='La URL no puede estar vacia')
    if not (clean_url.startswith('http://') or clean_url.startswith('https://')):
        raise HTTPException(
            status_code=400, 
            detail=f"URL no valida: '{clean_url}'. Debe comenzar por http:// o https://"
        )

    is_safe, free_gb = check_disk_safety()
    if not is_safe:
        raise HTTPException(
            status_code=507, 
            detail='Almacenamiento temporal en zona de seguridad. Espere unos minutos a la purga automatica.'
        )

    task_id = str(uuid.uuid4())[:8]
    md_text = None
    try:
        if req.mode == 'video':
            out_file = await download_video(clean_url, task_id)
        elif req.mode == 'audio':
            out_file = await download_audio(clean_url, task_id)
        elif req.mode == 'markdown':
            out_file, md_text = await generate_markdown(clean_url, task_id)

        resp = {
            'task_id': task_id,
            'filename': out_file.name,
            'download_url': f'/api/download/{out_file.name}',
            'mode': req.mode
        }
        if md_text:
            resp['markdown_content'] = md_text

        return resp
    except HTTPException:
        raise
    except YoutubeDLError as e:
        logger.warning(f'Error de cliente en process_video ({clean_url}): {e}')
        raise HTTPException(status_code=400, detail=f'No se pudo procesar la URL: {str(e)}')
    except ValueError as e:
        logger.warning(f'Error de valor en process_video: {e}')
        raise HTTPException(status_code=400, detail=f'Parametro no valido: {str(e)}')
    except Exception as e:
        logger.error(f'Error inesperado en process_video: {e}', exc_info=True)
        raise HTTPException(status_code=500, detail=f'Error procesando video: {str(e)}')

@app.get('/api/download/{filename}')
async def download_file(filename: str):
    safe_name = Path(filename).name
    file_path = STORAGE_DIR / safe_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail='Archivo expirado o no encontrado')

    asyncio.create_task(remove_file_delayed(file_path, delay=0.5))

    media_type = 'application/octet-stream'
    if safe_name.endswith('.mp4'):
        media_type = 'video/mp4'
    elif safe_name.endswith('.mp3'):
        media_type = 'audio/mpeg'
    elif safe_name.endswith('.md'):
        media_type = 'text/markdown; charset=utf-8'

    return FileResponse(
        path=file_path, 
        filename=safe_name, 
        media_type=media_type
    )
