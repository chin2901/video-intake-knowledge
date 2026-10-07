#!/usr/bin/env python3
"""
Sentinel Prober - Monitor Proactivo de Fuentes Multimedia
Comprueba periódicamente la salud de los extractores de vídeo en YouTube, TikTok, etc.
"""

import sys
import json
import logging
import urllib.request
import urllib.error
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/home/ubuntu/video-intake-web/sentinel.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('sentinel')

API_URL = 'http://127.0.0.1:8090/api/info'

TEST_TARGETS = [
    {
        'platform': 'YouTube',
        'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
    },
    {
        'platform': 'SoundCloud',
        'url': 'https://soundcloud.com/octobersveryown/drake-gods-plan'
    }
]

def probe_url(target: dict) -> dict:
    url = target['url']
    platform = target['platform']
    data = json.dumps({'url': url}).encode('utf-8')
    req = urllib.request.Request(
        API_URL,
        data=data,
        headers={'Content-Type': 'application/json'}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status == 200:
                result = json.loads(resp.read().decode('utf-8'))
                logger.info(f'✓ [{platform}] Extractor operativo: "{result.get("title", "")[:40]}"')
                return {'platform': platform, 'status': 'ok'}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8', errors='ignore')
        logger.error(f'✗ [{platform}] Fallo HTTP {e.code}: {err_body}')
        return {'platform': platform, 'status': 'error', 'code': e.code, 'detail': err_body, 'url': url}
    except Exception as e:
        logger.error(f'✗ [{platform}] Error de conexion o timeout: {str(e)}')
        return {'platform': platform, 'status': 'error', 'code': 0, 'detail': str(e), 'url': url}

def run_probe():
    logger.info('=== Iniciando ronda de inspeccion de centinela ===')
    failures = []
    for target in TEST_TARGETS:
        res = probe_url(target)
        if res['status'] != 'ok':
            failures.append(res)
    
    if not failures:
        logger.info('=== Todos los extractores responden nominalmente (0 incidencias) ===')
        return 0
    
    logger.warning(f'=== Detectadas {len(failures)} incidencias. Invocando Auto-Healer... ===')
    
    # Invocar Auto-Healer pasando el reporte de fallos
    from auto_healer import heal_incident
    for failure in failures:
        heal_incident(failure)
    return len(failures)

if __name__ == '__main__':
    exit(run_probe())
