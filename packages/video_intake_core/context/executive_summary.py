"""
Structured Executive Summary generator.

Produces high-level executive summaries, key takeaways, tools & software catalogs,
technical glossaries, and reproducible practical action items.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Known tools/software dictionary with categories and descriptions
_KNOWN_TOOLS_CATALOG: dict[str, tuple[str, str]] = {
    "python": ("Lenguaje", "Lenguaje de programación interpretado de alto nivel"),
    "whisper": ("IA / Transcripción", "Modelo neuronal de transcripción de audio de OpenAI"),
    "faster-whisper": (
        "IA / Rendimiento",
        "Implementación optimizada de Whisper basada en CTranslate2",
    ),
    "ffmpeg": (
        "Multimedia",
        "Herramienta CLI para decodificación, codificación y conversión multimedia",
    ),
    "ffprobe": ("Multimedia", "Analizador de secuencias y contenedores multimedia"),
    "opencv": ("Visión por Computador", "Biblioteca de visión artificial en tiempo real (cv2)"),
    "tesseract": ("OCR", "Motor de reconocimiento óptico de caracteres"),
    "pytesseract": ("OCR", "Wrapper Python para el motor Tesseract OCR"),
    "docker": ("Contenedores", "Plataforma de virtualización y contenedorización"),
    "git": ("Control de Versiones", "Sistema distribuido de control de versiones"),
    "github": ("DevOps", "Plataforma de alojamiento de repositorios y CI/CD"),
    "yt-dlp": ("Adquisición", "Extractor CLI avanzado para descarga de vídeo y subtítulos"),
    "fastapi": ("Backend", "Framework web async moderno en Python"),
    "sqlite": ("Base de Datos", "Motor SQL embebido transaccional y serverless"),
    "postgresql": ("Base de Datos", "Sistema gestor de bases de datos relacionales avanzado"),
    "linux": ("Sistema Operativo", "Sistema operativo Unix-like"),
    "ubuntu": ("Sistema Operativo", "Distribución Linux orientada a servidor y escritorio"),
    "bash": ("Scripting / Terminal", "Intérprete de comandos y lenguaje de scripting"),
    "curl": ("Redes / CLI", "Cliente de transferencia de datos por línea de comandos"),
    "pytest": ("Testing", "Framework de pruebas unitarias y de integración en Python"),
    "ruff": ("Calidad de Código", "Linter y formateador ultrarrápido para Python"),
    "mypy": ("Tipado Estático", "Verificador estático de tipos para Python"),
}

# Technical terms for automated glossary extraction
_KNOWN_GLOSSARY_CATALOG: dict[str, str] = {
    "ssim": "Índice de similitud estructural (Structural Similarity Index) que evalúa la fidelidad perceptual entre fotogramas.",
    "mse": "Error cuadrático medio (Mean Squared Error), métrica de distancia pixel a pixel entre imágenes.",
    "ocr": "Reconocimiento óptico de caracteres (Optical Character Recognition) para convertir texto visual a datos legibles por máquina.",
    "laplacian variance": "Varianza del operador Laplaciano utilizada como métrica cuantitativa de enfoque y nitidez de imagen.",
    "zero-gpu": "Estrategia de procesamiento directo sin coste de acelerador, priorizando subtítulos nativos y cuantización int8.",
    "int8 quantization": "Técnica de compresión de modelos de deep learning a enteros de 8 bits reduciendo memoria y multiplicando velocidad.",
    "keyframe": "Fotograma clave representativo de una secuencia o diapositiva donde ocurre un cambio visual significativo.",
    "pipeline": "Cadena de etapas secuenciales automatizadas de ingesta, procesamiento y estructuración de datos.",
    "token": "Unidad atómica de texto o código procesada por modelos lingüísticos o analizadores léxicos.",
    "ci/cd": "Integración y despliegue continuos (Continuous Integration / Continuous Deployment) para pruebas y validación automatizada.",
    "ssot": "Fuente única de verdad (Single Source of Truth), principio arquitectónico que prohíbe fuentes de datos redundantes o divergentes.",
}


def _clean_text(text: str) -> str:
    """Normalize whitespace and strip text."""
    return " ".join(text.split()).strip()


def _split_into_sentences(text: str) -> list[str]:
    """Split text into individual clean sentences."""
    raw = re.split(r"(?<=[.!?¡¿])\s+", text)
    sentences: list[str] = []
    for s in raw:
        cleaned = _clean_text(s)
        if len(cleaned) > 12:
            sentences.append(cleaned)
    return sentences


def generate_structured_executive_summary(
    text: str,
    segments: list[dict[str, Any]] | None = None,
    source_info: dict[str, Any] | None = None,
    tools_list: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Generate a structured, professional executive summary from content.

    Args:
        text: Full transcript or document text.
        segments: Optional transcript segments with timestamps.
        source_info: Optional metadata about the source (title, url, duration, etc.).
        tools_list: Optional pre-extracted tools list.

    Returns:
        Dict containing high_level_summary, key_takeaways, tools_and_software,
        glossary, and action_items.
    """
    clean_full = _clean_text(text)
    sentences = _split_into_sentences(clean_full)
    text_lower = clean_full.lower()

    # 1. High-Level Summary
    intro_sentences = sentences[:3] if len(sentences) >= 3 else sentences
    outro_sentences = sentences[-2:] if len(sentences) >= 5 else []
    core_summary = " ".join(intro_sentences)
    if outro_sentences and outro_sentences != intro_sentences:
        core_summary += " En conclusión, " + " ".join(outro_sentences).lstrip()

    if not core_summary:
        core_summary = "Extracción y análisis de contenido audiovisual completado exitosamente."

    # 2. Key Points (4 to 8 takeaways)
    key_takeaways: list[str] = []
    seen_takeaways: set[str] = set()

    for s in sentences:
        s_low = s.lower()
        if (
            any(
                kw in s_low
                for kw in (
                    "importante",
                    "clave",
                    "fundamental",
                    "objetivo",
                    "ventaja",
                    "permite",
                    "arquitectura",
                    "proceso",
                    "método",
                    "función",
                    "sistema",
                    "resultado",
                )
            )
            and s_low not in seen_takeaways
            and len(s) < 220
        ):
            seen_takeaways.add(s_low)
            key_takeaways.append(s)
            if len(key_takeaways) >= 6:
                break

    if len(key_takeaways) < 3 and sentences:
        for s in sentences[1:5]:
            if s.lower() not in seen_takeaways:
                key_takeaways.append(s)

    # 3. Tools and Software Identification
    tools: list[dict[str, str]] = []
    seen_tools: set[str] = set()

    # Incorporate pre-extracted tools
    if tools_list:
        for t in tools_list:
            name = t.get("tool") or t.get("name", "")
            if name and name.lower() not in seen_tools:
                seen_tools.add(name.lower())
                tools.append(
                    {
                        "name": name,
                        "category": t.get("category", "Software"),
                        "description": t.get("description", "Herramienta identificada en el vídeo"),
                    }
                )

    # Check known catalog
    for name, (cat, desc) in _KNOWN_TOOLS_CATALOG.items():
        if re.search(rf"\b{re.escape(name)}\b", text_lower) and name not in seen_tools:
            seen_tools.add(name)
            tools.append(
                {
                    "name": name.capitalize()
                    if name not in ("ffmpeg", "ffprobe", "yt-dlp", "ci/cd")
                    else name,
                    "category": cat,
                    "description": desc,
                }
            )

    # 4. Glossary Extraction
    glossary: list[dict[str, str]] = []
    seen_terms: set[str] = set()

    for term, definition in _KNOWN_GLOSSARY_CATALOG.items():
        if re.search(rf"\b{re.escape(term)}\b", text_lower) and term not in seen_terms:
            seen_terms.add(term)
            glossary.append(
                {
                    "term": term.upper() if len(term) <= 5 else term.title(),
                    "definition": definition,
                }
            )

    # 5. Action Items & Reproducible Steps
    action_items: list[dict[str, Any]] = []
    action_candidates: list[str] = []

    # Look for imperative phrases or steps
    for s in sentences:
        s_low = s.lower()
        if (
            any(
                kw in s_low
                for kw in (
                    "debemos",
                    "hay que",
                    "tenemos que",
                    "primero",
                    "segundo",
                    "paso",
                    "ejecutar",
                    "configurar",
                    "instalar",
                    "verificar",
                    "asegurar",
                    "probar",
                )
            )
            and len(s) < 200
            and s not in action_candidates
        ):
            action_candidates.append(s)

    for idx, act in enumerate(action_candidates[:5], 1):
        # Detect if command line is mentioned
        cmd_match = re.search(r"(`[^`]+`|\b(uv|pip|docker|git|apt)\s+[a-z0-9_\-\.]+)", act)
        cmd_str = cmd_match.group(0).strip("`") if cmd_match else None
        action_items.append(
            {
                "step": idx,
                "action": act,
                "command": cmd_str,
            }
        )

    # Fallback default action items if text was conversational
    if not action_items:
        action_items = [
            {
                "step": 1,
                "action": "Revisar los prerrequisitos técnicos y herramientas identificadas en la documentación.",
                "command": None,
            },
            {
                "step": 2,
                "action": "Reproducir la secuencia operativa y verificar las salidas esperadas en cada hito.",
                "command": None,
            },
            {
                "step": 3,
                "action": "Validar la correcta integración en la suite de pruebas automatizadas.",
                "command": "uv run pytest",
            },
        ]

    return {
        "title": source_info.get("title", "Resumen de Contenido")
        if source_info
        else "Resumen de Contenido",
        "source": source_info or {},
        "high_level_summary": core_summary,
        "key_takeaways": key_takeaways,
        "tools_and_software": tools,
        "glossary": glossary,
        "action_items": action_items,
        "total_characters": len(clean_full),
    }


def format_executive_summary_markdown(
    summary_data: dict[str, Any],
    title: str = "Resumen Ejecutivo Estructurado",
) -> str:
    """Format structured executive summary dictionary into a clean Markdown document.

    Args:
        summary_data: Dict returned by generate_structured_executive_summary().
        title: Header title string.

    Returns:
        Markdown string ready for saving as executive_summary.md.
    """
    doc_title = summary_data.get("title") or title
    src = summary_data.get("source", {})

    lines: list[str] = [
        f"# {title}: {doc_title}",
        "",
        "> Resumen de alto nivel, puntos clave, herramientas identificadas, glosario técnico y pasos prácticos.",
        "",
    ]

    if src:
        lines.append(f"- **Fuente:** {src.get('resolved_url') or src.get('url', 'N/A')}")
        if src.get("duration"):
            lines.append(f"- **Duración:** {src.get('duration')}s")
        if src.get("platform"):
            lines.append(f"- **Plataforma:** {src.get('platform')}")
        lines.append("")

    # 1. Visión General
    lines.append("## 1. Visión General de Alto Nivel")
    lines.append("")
    lines.append(summary_data.get("high_level_summary", "Sin resumen disponible."))
    lines.append("")

    # 2. Puntos Clave
    takeaways = summary_data.get("key_takeaways", [])
    if takeaways:
        lines.append("## 2. Puntos Clave Destacados (Key Takeaways)")
        lines.append("")
        for pt in takeaways:
            lines.append(f"- {pt}")
        lines.append("")

    # 3. Herramientas y Software
    tools = summary_data.get("tools_and_software", [])
    if tools:
        lines.append("## 3. Herramientas, Tecnologías y Software Mencionados")
        lines.append("")
        lines.append("| Herramienta | Categoría | Propósito / Descripción |")
        lines.append("| :--- | :--- | :--- |")
        for t in tools:
            lines.append(
                f"| **{t['name']}** | {t.get('category', 'N/A')} | {t.get('description', '')} |"
            )
        lines.append("")

    # 4. Glosario
    glossary = summary_data.get("glossary", [])
    if glossary:
        lines.append("## 4. Glosario de Términos Técnicos")
        lines.append("")
        for g in glossary:
            lines.append(f"- **{g['term']}:** {g['definition']}")
        lines.append("")

    # 5. Action Items
    action_items = summary_data.get("action_items", [])
    if action_items:
        lines.append("## 5. Plan de Acción y Pasos Prácticos (Action Items)")
        lines.append("")
        for item in action_items:
            step = item.get("step", 1)
            act = item.get("action", "")
            cmd = item.get("command")
            lines.append(f"{step}. **Paso {step}:** {act}")
            if cmd:
                lines.append(f"   ```bash\n   {cmd}\n   ```")
        lines.append("")

    return "\n".join(lines).strip() + "\n"
