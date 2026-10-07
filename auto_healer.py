#!/usr/bin/env python3
"""
Auto-Healer Inteligente con agy
Orquesta la auto-corrección de extractores de vídeo, validación con Pytest y push a GitHub.
"""

import os
import sys
import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path('/home/ubuntu/video-intake-web')
LOG_FILE = BASE_DIR / 'auto_heal.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(str(LOG_FILE)),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('auto_healer')

def run_cmd(cmd: str, check=True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, shell=True, cwd=str(BASE_DIR), text=True, capture_output=True, check=check)

def test_url_fixed(url: str) -> bool:
    try:
        import urllib.request
        data = json.dumps({'url': url}).encode('utf-8')
        req = urllib.request.Request('http://127.0.0.1:8090/api/info', data=data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except Exception as e:
        logger.warning(f'test_url_fixed ({url}) devolvio error: {e}')
        return False

def run_test_suite() -> bool:
    logger.info('Ejecutando suite de pruebas de aceptacion (Pytest)...')
    res = subprocess.run('pytest -v stress_tests/', shell=True, cwd=str(BASE_DIR), text=True, capture_output=True)
    if res.returncode == 0:
        logger.info('✓ Suite de pruebas APROBADA (100% PASS)')
        return True
    else:
        logger.warning(f'✗ Suite de pruebas FALLÓ (code {res.returncode}):\n{res.stdout}\n{res.stderr}')
        return False

def git_commit_and_push(platform: str, reason: str):
    logger.info('Sincronizando cambios con GitHub...')
    try:
        run_cmd('git add app/ requirements.txt update.sh auto_healer.py sentinel_prober.py Dockerfile docker-compose.yml stress_tests/ .gitignore || true')
        diff_res = subprocess.run('git diff --cached --quiet', shell=True, cwd=str(BASE_DIR))
        if diff_res.returncode == 0:
            logger.info('No hay cambios pendientes en el árbol de trabajo para commitear.')
            return True
        commit_msg = f'fix(extractor): autonomous auto-heal for {platform} - {reason}'
        run_cmd(f'git commit -m "{commit_msg}"')
        run_cmd('git push origin main:web-hub')
        logger.info(f'✓ Cambios publicados exitosamente en GitHub: {commit_msg}')
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f'Error en git push: {e.stderr}')
        return False

def heal_incident(incident: dict):
    platform = incident.get('platform', 'Desconocido')
    url = incident.get('url', '')
    detail = incident.get('detail', '')
    
    logger.info(f'=== INICIANDO PROTOCOLO DE AUTO-CURACION PARA [{platform}] ===')
    logger.info(f'URL afectada: {url}')
    logger.info(f'Error detectado: {detail[:200]}')

    # FASE 1: Intento rapido de actualizacion de yt-dlp
    logger.info('Fase 1: Actualizando yt-dlp dentro del contenedor...')
    try:
        run_cmd('docker exec video-intake-web pip install --upgrade --no-cache-dir yt-dlp', check=False)
        run_cmd('docker compose restart video-web', check=False)
        run_cmd('sleep 3', check=False)
        
        if test_url_fixed(url) and run_test_suite():
            logger.info('✓ Incidente resuelto mediante actualizacion de yt-dlp.')
            git_commit_and_push(platform, 'updated yt-dlp engine')
            return True
    except Exception as e:
        logger.warning(f'Fase 1 no resolvio el problema: {e}')

    # FASE 2: Intervencion quirurgica de agy
    logger.info(f'Fase 2: Despertando a agy para analisis y modificacion de codigo...')
    prompt = f'''ALERTA AUTONOMA DE PRODUCCION:
El extractor de la plataforma {platform} ha fallado con el siguiente error:
{detail}
URL de prueba: {url}

Tu mision en /home/ubuntu/video-intake-web:
1. Inspecciona app/extractor.py y analiza la causa del fallo.
2. Modifica app/extractor.py para adaptar las opciones de yt-dlp (como extractor_args, headers, formatos o bypasses) para que {url} vuelva a funcionar.
3. Reinicia el contenedor con: docker compose restart video-web
4. Verifica que la URL funcione llamando a la API local http://127.0.0.1:8090/api/info con curl.
'''
    try:
        # Invocacion a agyw en modo autonomo
        cmd = f'''/home/ubuntu/.local/bin/agyw --dangerously-skip-permissions -p {json.dumps(prompt)}'''
        res = subprocess.run(cmd, shell=True, cwd=str(BASE_DIR), text=True, capture_output=True, timeout=300)
        logger.info(f'Salida de agy:\n{res.stdout}')
        
        # FASE 3: Gate de Aceptacion Estricto
        if test_url_fixed(url) and run_test_suite():
            logger.info('✓ Reparacion de agy verificada empíricamente con exito.')
            git_commit_and_push(platform, 'repaired extractor logic by agy')
            return True
        else:
            logger.error('✗ Las pruebas de verificacion fallaron tras la modificacion de agy. Ejecutando ROLLBACK...')
            run_cmd('git checkout -- app/extractor.py', check=False)
            run_cmd('docker compose restart video-web', check=False)
            return False
            
    except subprocess.TimeoutExpired:
        logger.error('Timeout superado en ejecucion de agy. Revertiendo cambios...')
        run_cmd('git checkout -- app/extractor.py', check=False)
        return False
    except Exception as e:
        logger.error(f'Error durante invocacion de agy: {e}')
        run_cmd('git checkout -- app/extractor.py', check=False)
        return False

if __name__ == '__main__':
    # Test manual
    test_incident = {
        'platform': 'ManualCheck',
        'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        'detail': 'Test trigger'
    }
    heal_incident(test_incident)
