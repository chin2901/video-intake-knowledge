"""
Test kit para video-intake-knowledge.

Provee utilidades para pruebas: fixtures, helpers, mocks controlados.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("video_intake_testkit")


class TestFixtures:
    """Factory de fixtures de prueba para video-intake-knowledge."""

    @staticmethod
    def sample_mp4() -> Path:
        """Devuelve la ruta a un MP4 de prueba si existe."""
        return Path(__file__).parent / "fixtures" / "sample.mp4"

    @staticmethod
    def sample_no_audio_mp4() -> Path:
        """Devuelve la ruta a un MP4 sin audio si existe."""
        return Path(__file__).parent / "fixtures" / "silent.mp4"

    @staticmethod
    def sample_with_text_mp4() -> Path:
        """Devuelve la ruta a un MP4 con texto visible si existe."""
        return Path(__file__).parent / "fixtures" / "text_video.mp4"

    @staticmethod
    def sample_with_scenes_mp4() -> Path:
        """Devuelve la ruta a un MP4 con cambios de escena si existe."""
        return Path(__file__).parent / "fixtures" / "scenes.mp4"

    @staticmethod
    def manifest() -> dict[str, Any]:
        """Devuelve un manifiesto de prueba."""
        return {
            "version": "1.0",
            "created_at": "2026-09-20T12:00:00Z",
            "videos": [
                {
                    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "title": "Sample Video 1",
                    "mode": "individual",
                    "select": "6",
                },
                {
                    "url": "https://www.facebook.com/watch/?v=12345",
                    "title": "Sample Video 2",
                    "mode": "global",
                    "select": "1,3,5",
                },
            ],
        }

    @staticmethod
    def source_dict(
        url: str = "https://example.com/video.mp4",
        title: str = "Test Video",
        platform: str = "local",
        duration_secs: float = 120.0,
    ) -> dict[str, Any]:
        """Devuelve un dict de fuente de prueba."""
        return {
            "url": url,
            "resolved_url": url,
            "title": title,
            "platform": platform,
            "type": "local_file",
            "duration_secs": duration_secs,
            "is_local": True,
        }

    @staticmethod
    def transcript_segment(
        start: float = 0.0,
        end: float = 5.0,
        speaker: str = "speaker_1",
        text: str = "Hola, este es un segmento de prueba.",
        confidence: float = 0.95,
    ) -> dict[str, Any]:
        """Devuelve un segmento de transcripción de prueba."""
        return {
            "start": start,
            "end": end,
            "speaker": speaker,
            "text": text,
            "confidence": confidence,
        }

    @staticmethod
    def transcript_result(
        full_text: str = "Texto de transcripción de prueba.",
        language: str = "es",
        segments: list[dict[str, Any]] | None = None,
        source_url: str = "https://example.com/video.mp4",
    ) -> dict[str, Any]:
        """Devuelve un resultado de transcripción de prueba."""
        if segments is None:
            segments = [
                TestFixtures.transcript_segment(
                    start=0.0, end=5.0, text="Primero.",
                ),
                TestFixtures.transcript_segment(
                    start=5.0, end=10.0, text="Segundo.",
                ),
            ]
        return {
            "full_text": full_text,
            "language": language,
            "segments": segments,
            "source_url": source_url,
            "confidence": 0.9,
            "method": "test_fixture",
            "duration_secs": sum(s["end"] - s["start"] for s in segments),
        }

    @staticmethod
    def ocr_block(
        text: str = "Texto detectado",
        confidence: float = 0.9,
        bbox: list[float] = [0, 0, 100, 50],
        lang: str = "es",
    ) -> dict[str, Any]:
        """Devuelve un bloque OCR de prueba."""
        return {
            "text": text,
            "confidence": confidence,
            "bbox": bbox,
            "language": lang,
        }

    @staticmethod
    def ocr_result(
        blocks: list[dict[str, Any]] | None = None,
        full_text: str = "Resultado OCR de prueba.",
        avg_confidence: float = 0.85,
    ) -> dict[str, Any]:
        """Devuelve un resultado OCR de prueba."""
        if blocks is None:
            blocks = [TestFixtures.ocr_block()]
        return {
            "blocks": blocks,
            "full_text": full_text,
            "avg_confidence": avg_confidence,
            "frame": None,
        }

    @staticmethod
    def scene(
        start: float = 0.0,
        end: float = 10.0,
        frame: int = 0,
        change_score: float = 45.0,
    ) -> dict[str, Any]:
        """Devuelve una escena de prueba."""
        return {
            "start": start,
            "end": end,
            "frame": frame,
            "change_score": change_score,
        }

    @staticmethod
    def keyframe(
        frame_num: int = 0,
        timestamp: float = 0.0,
        width: int = 1920,
        height: int = 1080,
    ) -> dict[str, Any]:
        """Devuelve un keyframe de prueba."""
        return {
            "frame_num": frame_num,
            "timestamp": timestamp,
            "width": width,
            "height": height,
        }

    @staticmethod
    def job_dict(
        job_id: str = "job_test_001",
        source_url: str = "https://example.com/video.mp4",
        source_title: str = "Test Video",
        source_type: str = "local_file",
        status: str = "pending",
    ) -> dict[str, Any]:
        """Devuelve un dict de job de prueba."""
        from datetime import datetime, timezone
        return {
            "id": job_id,
            "source_url": source_url,
            "source_title": source_title,
            "source_type": source_type,
            "status": status,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "started_at": None,
            "completed_at": None,
            "selections": [],
            "result_metadata": None,
            "error_message": None,
            "user_id": "test_user",
        }

    @staticmethod
    def build_proposal(
        name: str = "test_proposal",
        proposal_type: str = "skill",
        objective: str = "Probar la generación de propuestas",
        evidence: str = "El vídeo mostró un procedimiento repetible.",
        recommendation: str = "create",
        files: list[str] | None = None,
    ) -> dict[str, Any]:
        """Devuelve una propuesta de build de prueba."""
        if files is None:
            files = ["skill/test_skill/SKILL.md"]
        return {
            "name": name,
            "type": proposal_type,
            "objective": objective,
            "evidence": evidence,
            "reliable_knowledge": True,
            "requires_validation": False,
            "dependencies": [],
            "existing_tools": [],
            "risks": [],
            "autonomy": "low",
            "tests_needed": ["basic_functionality"],
            "files": files,
            "host_compatibility": ["hermes", "generic"],
            "recommendation": recommendation,
            "reason": "Procedimiento repetible y explícito en el vídeo.",
            "status": "draft",
            "created_at": "2026-09-20T12:00:00Z",
        }

    @staticmethod
    def memory_entry_dict(
        entry_id: str = "mem_test_001",
        source_url: str = "https://example.com/video.mp4",
        source_title: str = "Test Video",
        content_type: str = "transcript",
        content: str = "Contenido de prueba.",
        summary: str = "Resumen de prueba.",
        extracted_at: str | None = None,
        confidence: float = 0.9,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Devuelve un dict de entrada de memoria de prueba."""
        from datetime import datetime, timezone
        if extracted_at is None:
            extracted_at = datetime.now(timezone.utc).isoformat()
        if tags is None:
            tags = ["test", "fixture"]
        return {
            "id": entry_id,
            "source_url": source_url,
            "source_title": source_title,
            "extracted_at": extracted_at,
            "content_type": content_type,
            "content": content,
            "summary": summary,
            "confidence": confidence,
            "tags": tags,
        }

    @staticmethod
    def context_dict(
        source_url: str = "https://example.com/video.mp4",
        source_title: str = "Test Video",
        summary: str = "Resumen ejecutivo de prueba.",
        timeline: list[dict[str, Any]] | None = None,
        main_topics: list[str] = None,
        entities: list[dict[str, Any]] | None = None,
        decisions: list[str] = None,
        procedures: list[dict[str, Any]] | None = None,
        risks: list[str] = None,
        quotes: list[dict[str, Any]] | None = None,
        open_questions: list[str] = None,
        confidence: float = 0.85,
    ) -> dict[str, Any]:
        """Devuelve un dict de contexto de prueba."""
        if timeline is None:
            timeline = [
                {"start": 0.0, "end": 5.0, "topic": "Introducción"},
                {"start": 5.0, "end": 10.0, "topic": "Desarrollo"},
            ]
        if main_topics is None:
            main_topics = ["Tema 1", "Tema 2"]
        if entities is None:
            entities = [{"name": "Entidad 1", "type": "concept"}]
        if decisions is None:
            decisions = ["Decisión 1"]
        if procedures is None:
            procedures = [{"step": 1, "description": "Paso 1"}]
        if risks is None:
            risks = ["Riesgo 1"]
        if quotes is None:
            quotes = [{"text": "Cita de prueba.", "start": 0.0, "end": 5.0}]
        if open_questions is None:
            open_questions = ["Pregunta abierta 1"]
        return {
            "source_url": source_url,
            "source_title": source_title,
            "summary": summary,
            "timeline": timeline,
            "main_topics": main_topics,
            "entities": entities,
            "decisions": decisions,
            "procedures": procedures,
            "risks": risks,
            "quotes": quotes,
            "open_questions": open_questions,
            "confidence": confidence,
            "facts": "Hecho 1 afirmado en el vídeo.",
            "inferences": "Inferencia 1 generada por el sistema.",
            "recommendations": "Recomendación 1 para el usuario.",
        }


class TestHelpers:
    """Helpers para pruebas de video-intake-knowledge."""

    @staticmethod
    def assert_dict_has_keys(
        data: dict[str, Any], expected_keys: list[str], label: str = ""
    ) -> None:
        """Asserts que un dict tiene las keys esperadas."""
        missing = [k for k in expected_keys if k not in data]
        if missing:
            raise AssertionError(
                f"{label or 'Dict'} missing keys: {missing}. "
                f"Got: {list(data.keys())}"
            )

    @staticmethod
    def assert_is_valid_json(value: str, label: str = "") -> dict[str, Any]:
        """Parsea un string como JSON y lo devuelve."""
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            raise AssertionError(
                f"{label or 'JSON'} no es válido: {e}. Value: {value[:200]}"
            )

    @staticmethod
    def create_temp_video_file(
        duration_secs: float = 10.0,
        has_audio: bool = True,
        has_text: bool = False,
    ) -> Path:
        """Crea un archivo MP4 temporal de prueba.

        En un entorno real, esto usaría FFmpeg para generar un video de prueba.
        En pruebas sin FFmpeg, devuelve None y la prueba se salta.
        """
        import shutil

        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            return Path()

        import tempfile
        tmp = Path(tempfile.mktemp(suffix=".mp4"))

        if has_text:
            # Vídeo con texto visible en pantalla
            cmd = [
                ffmpeg, "-f", "lavfi", "-i", "color=c=black:s=320x240:duration=10,",
                "-vf", "drawtext=text='Texto de prueba':fontsize=24:fontcolor=white:"
                "x=(w-text_w)/2:y=(h-text_h)/2",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", str(duration_secs),
                "-y", str(tmp),
            ]
        elif has_audio:
            # Vídeo con audio (ruido blanco)
            cmd = [
                ffmpeg, "-f", "lavfi", "-i", "color=c=black:s=320x240:duration=10,",
                "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p",
                "-t", str(duration_secs), "-y", str(tmp),
            ]
        else:
            # Vídeo sin audio
            cmd = [
                ffmpeg, "-f", "lavfi", "-i", "color=c=black:s=320x240:duration=10,",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-t",
                str(duration_secs), "-y", str(tmp),
            ]

        import subprocess
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.warning(f"No se pudo crear fixture: {result.stderr[:200]}")
            return Path()

        logger.info(f"Fixture creado: {tmp} ({tmp.stat().st_size} bytes)")
        return tmp

    @staticmethod
    def create_temp_audio_file(
        duration_secs: float = 10.0,
        format: str = "wav",
    ) -> Path:
        """Crea un archivo de audio temporal de prueba."""
        import shutil
        import tempfile

        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            return Path()

        tmp = Path(tempfile.mktemp(suffix=f".{format}"))

        cmd = [
            ffmpeg, "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
            "-t", str(duration_secs), "-y", str(tmp),
        ]

        import subprocess
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.warning(f"No se pudo crear fixture de audio: {result.stderr[:200]}")
            return Path()

        logger.info(f"Fixture de audio creado: {tmp} ({tmp.stat().st_size} bytes)")
        return tmp

    @staticmethod
    def create_temp_image_with_text(
        width: int = 640,
        height: int = 480,
        text: str = "Texto de prueba",
    ) -> Path:
        """Crea una imagen PNG temporal con texto para pruebas OCR."""
        import shutil
        import tempfile

        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            return Path()

        tmp = Path(tempfile.mktemp(suffix=".png"))

        cmd = [
            ffmpeg, "-f", "lavfi", "-i", f"color=c=white:s={width}x{height}:d=1,",
            "-vf", f"drawtext=text='{text}':fontsize=36:fontcolor=black:"
            f"x=(w-text_w)/2:y=(h-text_h)/2",
            "-frames:v", "1", "-y", str(tmp),
        ]

        import subprocess
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.warning(f"No se pudo crear imagen: {result.stderr[:200]}")
            return Path()

        logger.info(f"Imagen con texto creada: {tmp} ({tmp.stat().st_size} bytes)")
        return tmp
