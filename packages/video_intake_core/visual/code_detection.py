"""
Code and technical terminal detection for OCR and visual analysis.

Identifies source code and terminal sessions in video frames, detects programming
languages, and formats extracted technical text as Markdown code blocks.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Heuristic indicator patterns by language
_LANGUAGE_PATTERNS: dict[str, list[tuple[re.Pattern, float, str]]] = {
    "python": [
        (re.compile(r"^\s*def\s+[a-zA-Z_]\w*\s*\(", re.MULTILINE), 3.0, "def function"),
        (re.compile(r"^\s*class\s+[a-zA-Z_]\w*(\(.*?\))?:", re.MULTILINE), 3.0, "class definition"),
        (
            re.compile(r"^\s*(from\s+[\w\.]+\s+)?import\s+[\w\.]+", re.MULTILINE),
            2.5,
            "import statement",
        ),
        (
            re.compile(r"^\s*if\s+__name__\s*==\s*['\"]__main__['\"]:", re.MULTILINE),
            4.0,
            "main guard",
        ),
        (re.compile(r"\bself\.[a-zA-Z_]\w*", re.MULTILINE), 2.0, "self attribute"),
        (re.compile(r"\bprint\s*\(.*?\)", re.MULTILINE), 1.5, "print function"),
        (re.compile(r"^\s*elif\s+.*?:", re.MULTILINE), 2.0, "elif statement"),
        (re.compile(r"^\s*except\s+(\w+)?\s*(as\s+\w+)?:", re.MULTILINE), 2.5, "except clause"),
        (re.compile(r"^\s*@[\w\.]+(\(.*?\))?", re.MULTILINE), 2.0, "decorator"),
        (re.compile(r"__init__|__str__|__repr__", re.MULTILINE), 2.5, "dunder method"),
    ],
    "bash": [
        (re.compile(r"^\s*[$#]\s+[a-zA-Z0-9_\-\.]+", re.MULTILINE), 3.0, "shell prompt"),
        (
            re.compile(
                r"\b(sudo\s+)?(apt-get|apt|dnf|pacman|brew)\s+(install|update)", re.MULTILINE
            ),
            3.5,
            "package manager",
        ),
        (
            re.compile(
                r"\b(git\s+(clone|pull|push|commit|checkout|status|diff|add|branch))", re.MULTILINE
            ),
            3.5,
            "git command",
        ),
        (
            re.compile(r"\b(docker\s+(run|build|compose|ps|exec|images|pull))", re.MULTILINE),
            3.5,
            "docker command",
        ),
        (
            re.compile(r"\b(pip|uv|poetry)\s+(install|run|add)", re.MULTILINE),
            3.0,
            "python package command",
        ),
        (
            re.compile(r"\b(npm|bun|pnpm|yarn)\s+(install|run|build|test)", re.MULTILINE),
            3.0,
            "node package command",
        ),
        (
            re.compile(
                r"^\s*(cd|mkdir|rm\s+-rf|chmod|chown|ls\s+-[a-zA-Z]+|cat|grep|curl|wget)\b",
                re.MULTILINE,
            ),
            2.5,
            "unix core utility",
        ),
        (re.compile(r"\bexport\s+[A-Z0-9_]+=", re.MULTILINE), 2.5, "shell export"),
        (re.compile(r"^#!\s*/bin/(bash|sh|zsh)", re.MULTILINE), 4.0, "shebang"),
    ],
    "javascript": [
        (
            re.compile(r"\b(const|let|var)\s+[a-zA-Z_]\w*\s*=", re.MULTILINE),
            2.5,
            "variable declaration",
        ),
        (re.compile(r"\bfunction\s*[a-zA-Z_]\w*\s*\(", re.MULTILINE), 2.5, "function definition"),
        (re.compile(r"\bconsole\.(log|error|warn|info)\s*\(", re.MULTILINE), 2.5, "console log"),
        (re.compile(r"=>\s*\{?", re.MULTILINE), 2.0, "arrow function"),
        (
            re.compile(r"^\s*export\s+(default\s+)?(function|class|const)", re.MULTILINE),
            2.5,
            "es export",
        ),
        (re.compile(r"^\s*import\s+.*?\s+from\s+['\"].*?['\"];?", re.MULTILINE), 2.5, "es import"),
        (re.compile(r"\b(async\s+function|await\s+)", re.MULTILINE), 2.0, "async/await"),
    ],
    "typescript": [
        (re.compile(r"\binterface\s+[A-Z]\w*\s*\{", re.MULTILINE), 3.5, "ts interface"),
        (re.compile(r"\btype\s+[A-Z]\w*\s*=", re.MULTILINE), 3.0, "ts type alias"),
        (
            re.compile(
                r":\s*(string|number|boolean|any|void|unknown|never)[\s\[\],;]", re.MULTILINE
            ),
            2.5,
            "ts primitive type",
        ),
    ],
    "sql": [
        (
            re.compile(r"\bSELECT\s+.*?\s+FROM\b", re.IGNORECASE | re.MULTILINE),
            3.5,
            "select statement",
        ),
        (re.compile(r"\bINSERT\s+INTO\b", re.IGNORECASE | re.MULTILINE), 3.5, "insert statement"),
        (
            re.compile(r"\bUPDATE\s+.*?\s+SET\b", re.IGNORECASE | re.MULTILINE),
            3.5,
            "update statement",
        ),
        (re.compile(r"\bDELETE\s+FROM\b", re.IGNORECASE | re.MULTILINE), 3.5, "delete statement"),
        (re.compile(r"\bCREATE\s+TABLE\b", re.IGNORECASE | re.MULTILINE), 3.5, "create table"),
        (
            re.compile(
                r"\b(WHERE|GROUP\s+BY|ORDER\s+BY|HAVING|INNER\s+JOIN|LEFT\s+JOIN)\b", re.IGNORECASE
            ),
            2.0,
            "sql clause",
        ),
    ],
    "rust": [
        (re.compile(r"\bfn\s+[a-zA-Z_]\w*\s*\(", re.MULTILINE), 3.0, "fn keyword"),
        (re.compile(r"\blet\s+mut\s+[a-zA-Z_]\w*", re.MULTILINE), 3.5, "let mut"),
        (re.compile(r"\bimpl(\s+<.*?>)?\s+[A-Z]\w*", re.MULTILINE), 3.5, "impl block"),
        (re.compile(r"\bprintln!\s*\(", re.MULTILINE), 3.0, "println macro"),
        (re.compile(r"\buse\s+std::", re.MULTILINE), 3.0, "use std"),
    ],
    "go": [
        (re.compile(r"^\s*func\s+(\(.*?\)\s*)?[a-zA-Z_]\w*\s*\(", re.MULTILINE), 3.5, "go func"),
        (re.compile(r"^\s*package\s+[a-zA-Z_]\w*", re.MULTILINE), 3.5, "package statement"),
        (re.compile(r"\bfmt\.Println\s*\(", re.MULTILINE), 3.0, "fmt print"),
    ],
    "json": [
        (re.compile(r'^\s*\{\s*".*?"\s*:\s*', re.MULTILINE), 3.0, "json object"),
    ],
}


def detect_code_content(text: str) -> dict[str, Any]:
    """Analyze text extracted from an image to determine if it contains source code or terminal.

    Args:
        text: Extracted raw text (e.g. from OCR).

    Returns:
        Dict with:
            - is_code: bool
            - language: detected programming/scripting language (e.g. 'python', 'bash')
            - confidence: confidence score in [0.0, 1.0]
            - formatted_markdown: syntax-highlighted Markdown block or original text
            - indicators: list of matched features
            - line_count: number of non-empty lines
    """
    if not text or not text.strip():
        return {
            "is_code": False,
            "language": "",
            "confidence": 0.0,
            "formatted_markdown": "",
            "indicators": [],
            "line_count": 0,
        }

    clean_text = text.strip()
    lines = [line for line in clean_text.splitlines() if line.strip()]
    line_count = len(lines)

    # Score each language
    scores: dict[str, float] = {}
    matched_indicators: dict[str, list[str]] = {}

    for lang, patterns in _LANGUAGE_PATTERNS.items():
        lang_score = 0.0
        indicators: list[str] = []
        for pattern, weight, label in patterns:
            matches = pattern.findall(clean_text)
            if matches:
                lang_score += weight * min(len(matches), 3)
                indicators.append(f"{label} ({len(matches)})")
        if lang_score > 0:
            scores[lang] = lang_score
            matched_indicators[lang] = indicators

    # Additional generic syntax heuristics
    punctuation_count = len(re.findall(r"[{}\[\]();=><:!&|/\\$\"']", clean_text))
    punct_ratio = punctuation_count / max(len(clean_text), 1)

    # Indentation structure check
    indented_lines = sum(1 for line in lines if line.startswith(("  ", "\t")))
    indent_ratio = indented_lines / max(line_count, 1)

    best_lang = "python"
    best_score = 0.0

    if scores:
        best_lang, best_score = max(scores.items(), key=lambda x: x[1])

    # If typescript indicators detected, prefer typescript over javascript
    if "typescript" in scores and scores["typescript"] >= 2.5:
        best_lang = "typescript"
        best_score = scores["typescript"] + scores.get("javascript", 0)

    # Decision criteria:
    # 1. At least 2.5 points in language-specific patterns OR
    # 2. Significant punctuation and indentation with at least 1 indicator
    is_code = False
    confidence = 0.0

    if best_score >= 2.5:
        is_code = True
        confidence = min(0.60 + (best_score * 0.08), 0.99)
    elif best_score >= 1.5 and (punct_ratio > 0.08 or indent_ratio > 0.3):
        is_code = True
        confidence = 0.65
    elif punct_ratio > 0.15 and indent_ratio > 0.4 and line_count >= 3:
        is_code = True
        best_lang = "text"
        confidence = 0.50

    indicators = matched_indicators.get(best_lang, [])
    if punct_ratio > 0.08:
        indicators.append(f"punctuation density: {punct_ratio:.2f}")
    if indent_ratio > 0.3:
        indicators.append(f"indented lines: {indent_ratio:.0%}")

    formatted_markdown = f"```{best_lang}\n{clean_text}\n```" if is_code else clean_text

    return {
        "is_code": is_code,
        "language": best_lang if is_code else "",
        "confidence": round(confidence, 2),
        "formatted_markdown": formatted_markdown,
        "indicators": indicators,
        "line_count": line_count,
    }


def format_technical_ocr(ocr_data: str | dict[str, Any]) -> str:
    """Format OCR text or result dict into clean, syntax-aware Markdown.

    Args:
        ocr_data: Raw OCR string or OCR result dict containing a 'text' key.

    Returns:
        Markdown-formatted string with code blocks where appropriate.
    """
    if isinstance(ocr_data, dict):
        text = str(ocr_data.get("text", "")).strip()
    else:
        text = str(ocr_data).strip()

    if not text:
        return ""

    detection = detect_code_content(text)
    return detection["formatted_markdown"]


def enrich_ocr_with_code_detection(ocr_result: dict[str, Any]) -> dict[str, Any]:
    """Enrich an OCR result dict with code detection metadata and formatted Markdown.

    Args:
        ocr_result: Existing OCR result dict.

    Returns:
        Enriched dict with 'is_code', 'code_language', 'code_confidence',
        and 'formatted_markdown'.
    """
    text = ocr_result.get("text", "")
    detection = detect_code_content(text)

    enriched = dict(ocr_result)
    enriched["is_code"] = detection["is_code"]
    enriched["code_language"] = detection["language"]
    enriched["code_confidence"] = detection["confidence"]
    enriched["formatted_markdown"] = detection["formatted_markdown"]
    enriched["code_indicators"] = detection["indicators"]
    return enriched
