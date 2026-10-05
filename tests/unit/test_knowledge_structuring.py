"""
Unit tests for Elite Knowledge Structuring (Fase 3):
- Interactive Table of Contents (TOC) with formatted timestamps (00:01:23)
- Structured Executive Summary (high-level summary, key takeaways, tools, glossary, action items)
- Comprehensive Markdown report integration and artifact export
"""

from __future__ import annotations

from pathlib import Path

from video_intake_core.context import (
    export_knowledge_report,
    format_executive_summary_markdown,
    format_timestamp,
    format_toc_markdown,
    generate_comprehensive_markdown_report,
    generate_structured_executive_summary,
    generate_table_of_contents,
)


class TestTableOfContentsStructuring:
    """Tests for timestamp formatting and interactive Table of Contents (TOC)."""

    def test_format_timestamp(self):
        assert format_timestamp(0.0) == "00:00:00"
        assert format_timestamp(83.0) == "00:01:23"
        assert format_timestamp(3665.0) == "01:01:05"
        assert format_timestamp(83.0, include_hours=False) == "01:23"
        assert format_timestamp(-15.0) == "00:00:00"

    def test_generate_table_of_contents_with_segments(self):
        segments = [
            {
                "start": "00:00:00.000",
                "end": "00:00:30.000",
                "start_seconds": 0.0,
                "end_seconds": 30.0,
                "text": "Bienvenidos al curso de arquitectura de sistemas. Hoy veremos los fundamentos.",
            },
            {
                "start": "00:00:30.000",
                "end": "00:01:30.000",
                "start_seconds": 30.0,
                "end_seconds": 90.0,
                "text": "Configuramos Docker y PostgreSQL para la base de datos principal.",
            },
            {
                "start": "00:01:30.000",
                "end": "00:02:45.000",
                "start_seconds": 90.0,
                "end_seconds": 165.0,
                "text": "Implementamos el pipeline de OCR y visión por computador con OpenCV y Tesseract.",
            },
        ]

        keyframes = [
            {"frame_path": "frames/frame_0001.png", "timestamp": 15.0},
            {"frame_path": "frames/frame_0002.png", "timestamp": 60.0},
        ]

        chapters = generate_table_of_contents(
            segments=segments,
            video_duration=165.0,
            keyframes=keyframes,
        )

        assert len(chapters) >= 1
        first = chapters[0]
        assert first["chapter_number"] == 1
        assert "start_time" in first
        assert "end_time" in first
        assert "00:00:00" in first["start_time"]
        assert len(first["title"]) > 0
        assert len(first["key_points"]) > 0

    def test_generate_table_of_contents_fallback_empty_segments(self):
        chapters = generate_table_of_contents(
            segments=[],
            video_duration=120.0,
            full_text="Resumen global de prueba para vídeo sin subtítulos.",
        )
        assert len(chapters) == 1
        assert chapters[0]["chapter_number"] == 1
        assert chapters[0]["start_time"] == "00:00:00"
        assert chapters[0]["end_time"] == "00:02:00"

    def test_format_toc_markdown(self):
        sample_chapters = [
            {
                "chapter_number": 1,
                "start_time": "00:01:23",
                "end_time": "00:03:45",
                "duration_seconds": 142.0,
                "title": "Arquitectura y Prerrequisitos",
                "summary": "Revisión de dependencias del sistema y configuración inicial.",
                "key_points": ["Instalación de paquetes", "Variables de entorno"],
                "matched_keyframe": "frames/frame_0001.png",
            }
        ]

        md = format_toc_markdown(sample_chapters, title="Índice Navegable")
        assert "# Índice Navegable" in md
        assert "**`00:01:23`**" in md
        assert "[00:01:23 → 00:03:45] 1. Arquitectura y Prerrequisitos" in md
        assert "Instalación de paquetes" in md


class TestStructuredExecutiveSummary:
    """Tests for high-level executive summary, tools catalog, glossary, and action items."""

    def test_generate_structured_executive_summary(self):
        transcript_text = """
Bienvenidos a este tutorial de AibOS. El objetivo fundamental de esta sesión es desplegar
un pipeline con Docker y FastAPI utilizando Python.
Configuraremos OpenCV y Tesseract para el análisis visual.
Debemos calcular la Laplacian Variance y el índice SSIM para descartar fotogramas borrosos
y duplicados. Hay que verificar que las pruebas pasen con pytest antes de enviar a CI/CD.
Primero ejecutar git clone para clonar el repositorio. Segundo configurar el archivo .env.
"""
        source_info = {
            "title": "Despliegue de Pipeline Visual en AibOS",
            "url": "https://example.com/tutorial",
            "duration": 300,
        }

        data = generate_structured_executive_summary(transcript_text, source_info=source_info)

        # 1. High level summary
        assert len(data["high_level_summary"]) > 30

        # 2. Key takeaways
        assert len(data["key_takeaways"]) >= 1

        # 3. Tools and technologies detected
        tool_names = [t["name"].lower() for t in data["tools_and_software"]]
        assert "python" in tool_names
        assert "docker" in tool_names
        assert "fastapi" in tool_names

        # 4. Glossary terms detected
        glossary_terms = [g["term"].lower() for g in data["glossary"]]
        assert any(t in glossary_terms for t in ("ssim", "laplacian variance", "ocr", "ci/cd"))

        # 5. Action items
        assert len(data["action_items"]) >= 1
        assert any(
            "git clone" in a["action"].lower() or "clonar" in a["action"].lower()
            for a in data["action_items"]
        )

    def test_format_executive_summary_markdown(self):
        summary_data = {
            "title": "Tutorial de Optimización",
            "source": {"url": "https://aibos.internal/video1", "duration": 180},
            "high_level_summary": "Este proyecto aborda la optimización de ingesta multimedia.",
            "key_takeaways": ["Cero consumo de GPU", "Detección precisa de diapositivas"],
            "tools_and_software": [
                {"name": "Python", "category": "Lenguaje", "description": "Runtime base"}
            ],
            "glossary": [
                {"term": "SSIM", "definition": "Métrica de similitud estructural entre imágenes."}
            ],
            "action_items": [
                {
                    "step": 1,
                    "action": "Instalar dependencias del proyecto.",
                    "command": "uv sync",
                }
            ],
        }

        md = format_executive_summary_markdown(summary_data)
        assert "# Resumen Ejecutivo Estructurado: Tutorial de Optimización" in md
        assert "## 1. Visión General de Alto Nivel" in md
        assert "## 2. Puntos Clave Destacados (Key Takeaways)" in md
        assert "## 3. Herramientas, Tecnologías y Software Mencionados" in md
        assert "## 4. Glosario de Términos Técnicos" in md
        assert "## 5. Plan de Acción y Pasos Prácticos (Action Items)" in md
        assert "```bash\n   uv sync\n   ```" in md


class TestComprehensiveKnowledgeReport:
    """Tests for end-to-end report generation and export."""

    def test_generate_comprehensive_markdown_report(self, tmp_path: Path):
        title = "Pipeline de Inteligencia Visual"
        source_info = {"url": "https://youtu.be/test1234", "duration": 240}
        transcript = "Explicación detallada del flujo de trabajo y arquitectura."
        keyframes = [
            {
                "frame_path": str(tmp_path / "frame_0001.png"),
                "timestamp": 10.0,
                "timestamp_str": "00:00:10",
            }
        ]
        ocr_results = [
            {
                "frame_path": str(tmp_path / "frame_0001.png"),
                "text": "def calculate():\n    return 42",
                "is_code": True,
                "code_language": "python",
                "formatted_markdown": "```python\ndef calculate():\n    return 42\n```",
            }
        ]

        report = generate_comprehensive_markdown_report(
            title=title,
            source_info=source_info,
            transcript_text=transcript,
            keyframes=keyframes,
            ocr_results=ocr_results,
        )

        assert f"# Reporte Integral de Conocimiento: {title}" in report
        assert "## Metadatos del Contenido Audiovisual" in report
        assert "## Resumen Ejecutivo y Síntesis de Alto Nivel" in report
        assert "## Tabla de Contenidos y Navegación Cronológica" in report
        assert "## Inteligencia Visual y Momentos Clave" in report
        assert "```python" in report
        assert "## Transcripción Completa del Contenido" in report

    def test_export_knowledge_report(self, tmp_path: Path):
        content = "# Reporte de Prueba\nContenido verificado."
        saved_file = export_knowledge_report(tmp_path, content, filename="knowledge_report.md")

        assert saved_file.exists()
        assert saved_file.read_text(encoding="utf-8") == content
