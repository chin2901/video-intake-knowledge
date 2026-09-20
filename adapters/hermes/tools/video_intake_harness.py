#!/usr/bin/env python3
"""
video_intake_harness.py — Harness de integración para Hermes Agent

Este módulo proporciona la integración completa del sistema de extracción
de vídeo con Hermes Agent, incluyendo detección automática, gestión de
sesiones, y ejecución de operaciones en background.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any


class VideoIntakeHarness:
    """
    Harness de integración para video-intake-knowledge con Hermes Agent.
    
    Responsable de:
    - Detección automática de URLs de vídeo en mensajes
    - Gestión de sesiones y estado por session_id
    - Ejecución de operaciones asíncronas
    - Notificación de resultados al agente
    """
    
    def __init__(
        self,
        storage_dir: str | None = None,
        config_path: str | None = None,
        job_db_path: str | None = None,
    ):
        """Inicializar el harness con las rutas configuradas."""
        self.storage_dir = Path(storage_dir or os.environ.get(
            "VIDEO_INTAKE_STORAGE_DIR",
            str(Path.home() / ".video-intake-knowledge" / "data")
        ))
        self.config_path = Path(config_path or os.environ.get(
            "VIDEO_INTAKE_CONFIG",
            str(Path(__file__).parent.parent.parent / "config" / "default.yaml")
        ))
        self.job_db_path = Path(job_db_path or str(self.storage_dir / "jobs.db"))
        
        # Asegurar directorios
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        (self.storage_dir / "jobs").mkdir(parents=True, exist_ok=True)
        (self.storage_dir / "artifacts").mkdir(parents=True, exist_ok=True)
        
        # Estado de sesiones
        self._session_states: dict[str, dict[str, Any]] = {}
        self._session_lock = threading.Lock()
        
        #work queue para operaciones asíncronas
        self._work_queue: list[dict[str, Any]] = []
        self._queue_lock = threading.Lock()
        
        # Cargar configuración
        self._load_config()
    
    def _load_config(self) -> None:
        """Cargar configuración desde YAML si está disponible."""
        try:
            import yaml
            if self.config_path.exists():
                with open(self.config_path) as f:
                    self._config = yaml.safe_load(f) or {}
            else:
                self._config = {}
        except ImportError:
            self._config = {}
        except Exception:
            self._config = {}
    
    def detect_video_sources(self, message: str) -> list[dict[str, Any]]:
        """
        Detectar URLs de vídeo en un mensaje de texto.
        
        Analiza el mensaje buscando patrones de URL de plataformas
        conocidas: YouTube, Facebook, Instagram, TikTok.
        
        Returns:
            Lista de diccionarios con información de cada fuente detectada.
        """
        import re
        
        sources = []
        
        # Patrones de detección
        patterns = {
            "youtube": [
                r'https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
                r'https?://youtu\.be/([a-zA-Z0-9_-]+)',
                r'https?://(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]+)',
            ],
            "facebook": [
                r'https?://(?:www\.)?facebook\.com/share/v/([a-zA-Z0-9_]+)',
                r'https?://(?:www\.)?facebook\.com/watch/(?:v=)?([a-zA-Z0-9_]+)',
            ],
            "instagram": [
                r'https?://(?:www\.)?instagram\.com/reel/([a-zA-Z0-9_-]+)',
                r'https?://(?:www\.)?instagram\.com/p/([a-zA-Z0-9_-]+)',
                r'https?://(?:www\.)?instagram\.com/embed/(?:reel|p)/([a-zA-Z0-9_-]+)',
            ],
            "tiktok": [
                r'https?://(?:www\.)?tiktok\.com/@[^/]+/video/(\d+)',
                r'https?://(?:www\.)?tiktok\.com/t/([a-zA-Z0-9]+)',
            ],
        }
        
        for platform, pat_list in patterns.items():
            for pattern in pat_list:
                for match in re.finditer(pattern, message, re.IGNORECASE):
                    source_id = match.group(1)
                    url = match.group(0)
                    
                    # Evitar duplicados
                    if any(s.get("id") == source_id for s in sources):
                        continue
                    
                    sources.append({
                        "source_type": platform,
                        "id": source_id,
                        "url": url,
                        "detected_in": message[:100] + ("..." if len(message) > 100 else ""),
                    })
        
        return sources
    
    def create_session(self, session_id: str | None = None) -> str:
        """
        Crear una nueva sesión de extracción.
        
        Args:
            session_id: ID de sesión opcional. Si no se proporciona,
                       se genera uno automáticamente.
        
        Returns:
            El ID de sesión creado.
        """
        if session_id is None:
            session_id = str(uuid.uuid4())[:8]
        
        with self._session_lock:
            self._session_states[session_id] = {
                "created_at": time.time(),
                "sources": [],
                "operations": [],
                "jobs": [],
                "status": "init",
            }
        
        return session_id
    
    def add_sources_to_session(
        self,
        session_id: str,
        sources: list[dict[str, Any]],
    ) -> None:
        """Agregar fuentes detectadas a una sesión existente."""
        with self._session_lock:
            if session_id in self._session_states:
                self._session_states[session_id]["sources"].extend(sources)
                self._session_states[session_id]["status"] = "sources_ready"
    
    def select_operations(
        self,
        session_id: str,
        operations: list[str],
    ) -> None:
        """
        Seleccionar operaciones para una sesión.
        
        Args:
            session_id: ID de la sesión
            operations: Lista de operaciones seleccionadas:
                       ["download"], ["transcribe"], ["audio_context"],
                       ["visual_context"], ["all"], etc.
        """
        with self._session_lock:
            if session_id in self._session_states:
                self._session_states[session_id]["operations"] = operations
                self._session_states[session_id]["status"] = "operations_selected"
    
    def enqueue_job(
        self,
        source: dict[str, Any],
        operations: list[str],
        session_id: str,
    ) -> str:
        """
        Encolar un trabajo para procesamiento asíncrono.
        
        Returns:
            ID del trabajo encolado.
        """
        job_id = str(uuid.uuid4())[:12]
        
        job = {
            "job_id": job_id,
            "source": source,
            "operations": operations,
            "session_id": session_id,
            "enqueued_at": time.time(),
            "status": "queued",
        }
        
        with self._queue_lock:
            self._work_queue.append(job)
        
        # Actualizar estado de sesión
        with self._session_lock:
            if session_id in self._session_states:
                self._session_states[session_id]["jobs"].append(job_id)
                self._session_states[session_id]["status"] = "processing"
        
        return job_id
    
    def process_queue(self, max_jobs: int = 1) -> list[dict[str, Any]]:
        """
        Procesar trabajos de la cola.
        
        Args:
            max_jobs: Número máximo de trabajos a procesar.
        
        Returns:
            Lista de resultados de los trabajos procesados.
        """
        results = []
        
        with self._queue_lock:
            jobs_to_process = self._work_queue[:max_jobs]
            self._work_queue = self._work_queue[max_jobs:]
        
        for job in jobs_to_process:
            result = self._execute_job(job)
            results.append(result)
        
        return results
    
    def _execute_job(self, job: dict[str, Any]) -> dict[str, Any]:
        """
        Ejecutar un trabajo individual.
        
        Esta es la implementación básica. En producción, esto
        delegaría en los módulos reales de video_intake_core.
        """
        job_id = job["job_id"]
        source = job["source"]
        operations = job["operations"]
        
        result = {
            "job_id": job_id,
            "source_type": source.get("source_type"),
            "source_id": source.get("id"),
            "operations": operations,
            "started_at": time.time(),
            "status": "completed",
            "results": {},
        }
        
        # Simular procesamiento (en realidad, usar los módulos de core)
        for op in operations:
            if op == "download":
                result["results"]["download"] = {
                    "status": "simulated",
                    "path": f"/tmp/video_{source.get('id', 'unknown')}.mp4",
                }
            elif op == "transcribe":
                result["results"]["transcribe"] = {
                    "status": "simulated",
                    "text": "Transcripción simulada para demostración.",
                    "segments": [
                        {"start": 0.0, "end": 5.0, "text": "Texto simulado."}
                    ],
                }
            elif op in ("audio_context", "all"):
                result["results"]["audio_context"] = {
                    "status": "simulated",
                    "summary": "Resumen simulado del contenido.",
                    "topics": ["tema simulado 1", "tema simulado 2"],
                }
            elif op in ("visual_context", "all"):
                result["results"]["visual_context"] = {
                    "status": "simulated",
                    "scenes": [{"start": 0, "end": 10, "description": "Escena simulada"}],
                }
        
        result["completed_at"] = time.time()
        
        # Actualizar sesión
        session_id = job.get("session_id")
        if session_id:
            with self._session_lock:
                if session_id in self._session_states:
                    self._session_states[session_id]["status"] = "completed"
        
        return result
    
    def get_session_state(self, session_id: str) -> dict[str, Any] | None:
        """Obtener el estado actual de una sesión."""
        with self._session_lock:
            return self._session_states.get(session_id)
    
    def get_session_summary(self, session_id: str) -> dict[str, Any]:
        """
        Obtener un resumen legible de una sesión.
        
        Returns:
            Diccionario con información resumida de la sesión.
        """
        state = self.get_session_state(session_id)
        if state is None:
            return {"error": "Sesión no encontrada"}
        
        sources = state.get("sources", [])
        jobs = state.get("jobs", [])
        operations = state.get("operations", [])
        
        return {
            "session_id": session_id,
            "status": state.get("status", "unknown"),
            "source_count": len(sources),
            "job_count": len(jobs),
            "operations": operations,
            "sources": [
                {"type": s.get("source_type"), "id": s.get("id"), "url": s.get("url")}
                for s in sources
            ],
        }
    
    def clear_session(self, session_id: str) -> bool:
        """Limpiar una sesión y liberar recursos."""
        with self._session_lock:
            if session_id in self._session_states:
                del self._session_states[session_id]
                return True
        return False
    
    def health_check(self) -> dict[str, Any]:
        """Realizar un chequeo de salud del harness."""
        return {
            "status": "healthy",
            "storage_dir": str(self.storage_dir),
            "config_loaded": bool(self._config),
            "session_count": len(self._session_states),
            "queue_size": len(self._work_queue),
            "storage_exists": self.storage_dir.exists(),
        }


def main():
    """Punto de entrada principal para pruebas del harness."""
    harness = VideoIntakeHarness()
    
    # Chequeo de salud
    health = harness.health_check()
    print("Health check:")
    for k, v in health.items():
        print(f"  {k}: {v}")
    
    # Detección de ejemplos
    test_message = """
    Mira este vídeo de YouTube: https://www.youtube.com/watch?v=dQw4w9WgXcQ
    También hay otro en Facebook: https://www.facebook.com/share/v/ABC123XYZ/
    """
    
    sources = harness.detect_video_sources(test_message)
    print(f"\nDetectadas {len(sources)} fuentes:")
    for s in sources:
        print(f"  - {s['source_type']}: {s['id']} ({s['url']})")
    
    # Crear sesión y simular flujo
    session_id = harness.create_session()
    harness.add_sources_to_session(session_id, sources)
    harness.select_operations(session_id, ["download", "transcribe", "all"])
    
    # Encolar trabajos
    for source in sources:
        job_id = harness.enqueue_job(source, ["download", "transcribe"], session_id)
        print(f"\nTrabajo encolado: {job_id} para {source['source_type']}:{source['id']}")
    
    # Procesar cola
    results = harness.process_queue(max_jobs=2)
    print(f"\nProcesados {len(results)} trabajos:")
    for r in results:
        print(f"  - {r['job_id']}: {r['status']}")
        for op, res in r.get("results", {}).items():
            print(f"    {op}: {res.get('status', 'unknown')}")
    
    # Resumen de sesión
    summary = harness.get_session_summary(session_id)
    print(f"\nResumen de sesión {session_id}:")
    print(f"  Estado: {summary['status']}")
    print(f"  Fuentes: {summary['source_count']}")
    print(f"  Trabajos: {summary['job_count']}")


if __name__ == "__main__":
    main()
