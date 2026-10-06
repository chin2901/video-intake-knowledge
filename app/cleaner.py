import os
import time
import shutil
import logging
from pathlib import Path

logger = logging.getLogger('video_cleaner')
STORAGE_DIR = Path(os.getenv('STORAGE_DIR', '/app/storage'))
TTL_SECONDS = int(os.getenv('FILE_TTL_SECONDS', '1800'))  # 30 minutos
MIN_FREE_DISK_GB = float(os.getenv('MIN_FREE_DISK_GB', '20.0'))

def check_disk_safety() -> tuple[bool, float]:
    """Devuelve (is_safe, free_gb). Si el espacio libre es menor a MIN_FREE_DISK_GB, is_safe es False."""
    try:
        usage = shutil.disk_usage(STORAGE_DIR if STORAGE_DIR.exists() else '/')
        free_gb = usage.free / (1024 ** 3)
        return free_gb >= MIN_FREE_DISK_GB, round(free_gb, 2)
    except Exception as e:
        logger.error(f'Error al verificar disco: {e}')
        return True, 999.0

def purge_expired_files():
    """Elimina archivos con mas de TTL_SECONDS o purga completa si falta espacio."""
    now = time.time()
    is_safe, free_gb = check_disk_safety()
    
    if not STORAGE_DIR.exists():
        return

    for item in STORAGE_DIR.iterdir():
        if not item.is_file():
            continue
        try:
            mtime = item.stat().st_mtime
            age = now - mtime
            # Si el disco esta en zona de riesgo (< MIN_FREE_DISK_GB), purga agresiva (> 5 min)
            threshold = 300 if not is_safe else TTL_SECONDS
            if age > threshold:
                item.unlink(missing_ok=True)
                logger.info(f'Archivo purgado ({age/60:.1f} min): {item.name}')
        except Exception as e:
            logger.warning(f'No se pudo purgar {item.name}: {e}')

async def start_cleaner_loop():
    """Worker asincrono recurrente para limpieza cada 60s."""
    import asyncio
    while True:
        try:
            purge_expired_files()
        except Exception as e:
            logger.error(f'Excepcion en cleaner loop: {e}')
        await asyncio.sleep(60)
