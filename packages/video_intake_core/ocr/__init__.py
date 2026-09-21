"""
OCR module for extracting text from video frames.

Uses Tesseract OCR via pytesseract with OpenCV preprocessing.
Supports multiple languages and provides confidence scores
and bounding box coordinates for detected text.
"""

from __future__ import annotations

import json as _json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Optional

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# Cached tesseract languages
_tesseract_langs: Optional[list[str]] = None


def get_tesseract_languages() -> list[str]:
    """Get list of available Tesseract languages."""
    global _tesseract_langs
    if _tesseract_langs is None:
        try:
            result = subprocess.run(
                ["tesseract", "--list-langs"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                _tesseract_langs = [
                    line.strip()
                    for line in result.stdout.split("\n")
                    if line.strip() and line.strip() != "List of available languages:"
                ]
        except Exception:
            _tesseract_langs = []

    return _tesseract_langs or []


def extract_text(
    frame_path: str | Path,
    language: str = "eng",
    config: Optional[str] = None,
    preprocessing: str = "auto",
) -> dict[str, Any]:
    """Extract text from a single frame image using Tesseract OCR.

    Args:
        frame_path: Path to image file.
        language: Tesseract language code (e.g., 'eng', 'spa', 'fra').
            Multiple languages: 'eng+spa'.
        config: Additional Tesseract config string.
        preprocessing: Preprocessing method: 'none', 'grayscale',
            'threshold', 'adaptive', 'auto' (auto-select based on image).

    Returns:
        dict with:
            - text: Full extracted text.
            - text_clean: Cleaned text (whitespace normalized).
            - confidence: Average confidence (0-100).
            - confidence_per_block: Per-block confidence list.
            - bounding_boxes: List of {text, confidence, x, y, w, h}.
            - frame_path: Input frame path.
            - language: Language used.
            - preprocessing: Preprocessing applied.
            - tesseract_version: Tesseract version string.
    """
    frame_path = Path(frame_path)
    if not frame_path.exists():
        return {
            "text": "",
            "text_clean": "",
            "confidence": 0,
            "confidence_per_block": [],
            "bounding_boxes": [],
            "frame_path": str(frame_path),
            "language": language,
            "preprocessing": preprocessing,
            "tesseract_version": _get_tesseract_version(),
            "error": f"File not found: {frame_path}",
        }

    # Check language availability
    avail_langs = get_tesseract_languages()
    langs_to_use = language.split("+")
    for lang in langs_to_use:
        if lang not in avail_langs and lang != "eng":
            logger.warning(f"Language '{lang}' not installed, using eng")
            # Don't fail — Tesseract will fall back

    # Load image
    img = cv2.imread(str(frame_path))
    if img is None:
        return {
            "text": "",
            "text_clean": "",
            "confidence": 0,
            "confidence_per_block": [],
            "bounding_boxes": [],
            "frame_path": str(frame_path),
            "language": language,
            "preprocessing": preprocessing,
            "tesseract_version": _get_tesseract_version(),
            "error": "Failed to load image",
        }

    # Preprocess
    if preprocessing == "auto":
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Check if image is already light (text-light background)
        mean_val = np.mean(gray)
        if mean_val < 128:
            # Dark image — invert
            gray = cv2.bitwise_not(gray)
        # Check contrast
        std_dev = np.std(gray)
        if std_dev < 30:
            # Low contrast — apply adaptive threshold
            preprocessed = _preprocess_adaptive(gray)
        else:
            preprocessed = _preprocess_threshold(gray)
    elif preprocessing == "grayscale":
        preprocessed = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    elif preprocessing == "threshold":
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        preprocessed = _preprocess_threshold(gray)
    elif preprocessing == "adaptive":
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        preprocessed = _preprocess_adaptive(gray)
    else:
        preprocessed = img

    # OCR
    tesseract_config = f"--lang={language} --psm 3"
    if config:
        tesseract_config += f" {config}"

    # Get boxes and data
    try:
        import pytesseract

        # Data with confidence
        data = pytesseract.image_to_data(
            preprocessed,
            output_type=pytesseract.Output.DICT,
            config=tesseract_config,
        )

        # Full text
        full_text = pytesseract.image_to_string(
            preprocessed,
            config=tesseract_config,
        ).strip()

        # Parse results
        boxes: list[dict[str, Any]] = []
        confidences: list[float] = []
        n_boxes = len(data["text"])

        for i in range(n_boxes):
            text = data["text"][i].strip()
            conf_str = data.get("conf", [""])[i] if len(data.get("conf", [])) > i else ""
            conf = 0.0
            try:
                conf = float(conf_str)
            except (ValueError, TypeError):
                conf = -1.0

            if text and conf >= 0:
                x = data.get("left", [0])[i]
                y = data.get("top", [0])[i]
                w = data.get("width", [0])[i]
                h = data.get("height", [0])[i]
                boxes.append({
                    "text": text,
                    "confidence": conf,
                    "x": int(x),
                    "y": int(y),
                    "w": int(w),
                    "h": int(h),
                })
                confidences.append(conf)

        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

        result: dict[str, Any] = {
            "text": full_text,
            "text_clean": " ".join(full_text.split()),
            "confidence": avg_conf,
            "confidence_per_block": confidences,
            "bounding_boxes": boxes,
            "frame_path": str(frame_path),
            "language": language,
            "preprocessing": preprocessing,
            "tesseract_version": _get_tesseract_version(),
        }

        # Save OCR data as JSON next to frame if path is set
        _save_ocr_to_json(result, frame_path)

        return result

    except Exception as e:
        logger.error(f"OCR failed: {e}")
        return {
            "text": "",
            "text_clean": "",
            "confidence": 0,
            "confidence_per_block": [],
            "bounding_boxes": [],
            "frame_path": str(frame_path),
            "language": language,
            "preprocessing": preprocessing,
            "tesseract_version": _get_tesseract_version(),
            "error": str(e),
        }


def _preprocess_threshold(gray: np.ndarray) -> np.ndarray:
    """Apply Otsu's threshold to a grayscale image."""
    _, thresh = cv2.threshold(
        gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    return thresh


def _preprocess_adaptive(gray: np.ndarray) -> np.ndarray:
    """Apply adaptive threshold to a grayscale image."""
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2,
    )
    return thresh


def _get_tesseract_version() -> str:
    """Get Tesseract version string."""
    try:
        result = subprocess.run(
            ["tesseract", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            first_line = result.stdout.split("\n")[0]
            return first_line.strip()
    except Exception:
        pass
    return "unknown"


def _save_ocr_to_json(ocr_result: dict[str, Any], frame_path: Path) -> None:
    """Save OCR result as JSON next to the frame."""
    json_path = frame_path.with_suffix(".ocr.json")
    try:
        json_path.write_text(
            _json.dumps(ocr_result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        logger.debug(f"Failed to save OCR JSON: {e}")


def batch_ocr(
    image_paths: list[str | Path],
    engine: str = "tesseract",
) -> list[dict[str, Any]]:
    """Run OCR on multiple frames (contract API).

    Args:
        image_paths: List of image paths.
        engine: OCR engine to use (default: "tesseract").

    Returns:
        List of OCR result dicts.
    """
    # Usar valores por defecto para el resto de parámetros
    results: list[dict[str, Any]] = []

    for frame_path in image_paths:
        result = extract_text(
            frame_path,
            language="eng",
            preprocessing="auto",
        )
        results.append(result)

    return results


def ocr_frame_directory(
    directory: str | Path,
    pattern: str = "*.png",
    recursive: bool = False,
    output_json: Optional[str | Path] = None,
    language: str = "eng",
) -> list[dict[str, Any]]:
    """Run OCR on all frames in a directory.

    Args:
        directory: Directory containing frame images.
        pattern: Glob pattern for image files.
        recursive: Recurse into subdirectories.
        output_json: Optional path to save aggregated results.
        language: Tesseract language.

    Returns:
        List of OCR result dicts.
    """
    dir_path = Path(directory)
    if not dir_path.is_dir():
        return []

    if recursive:
        frame_files = list(dir_path.rglob(pattern))
    else:
        frame_files = list(dir_path.glob(pattern))

    # Sort by name for consistent ordering
    frame_files.sort(key=lambda p: p.name)

    return batch_ocr(
        [str(p) for p in frame_files],
    )


def merge_ocr_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge multiple OCR results into a consolidated result.

    Args:
        results: List of OCR result dicts from multiple frames.

    Returns:
        Merged dict with combined text, highest confidence frame,
        and aggregated bounding boxes.
    """
    if not results:
        return {"text": "", "frames_processed": 0, "frame_results": []}

    # Find best confidence frame
    best = max(results, key=lambda r: r.get("confidence", 0))
    all_text = " ".join(r.get("text", "") for r in results if r.get("text"))
    all_boxes: list[dict[str, Any]] = []
    frame_results: list[dict[str, Any]] = []

    for r in results:
        frame_results.append({
            "frame": r.get("frame_path", ""),
            "text": r.get("text", ""),
            "confidence": r.get("confidence", 0),
            "bounding_boxes": r.get("bounding_boxes", []),
        })
        all_boxes.extend(r.get("bounding_boxes", []))

    return {
        "text": all_text,
        "text_clean": " ".join(all_text.split()),
        "confidence": best.get("confidence", 0),
        "best_frame": best.get("frame_path", ""),
        "bounding_boxes": all_boxes,
        "frames_processed": len(results),
        "frame_results": frame_results,
        "language": results[0].get("language", "eng") if results else "eng",
    }


# ----------------------------------------------------------------------
# Contract API wrapper functions
# ----------------------------------------------------------------------


def run_ocr(
    frame_path: str | Path,
    language: str = "eng",
    config: Optional[str] = None,
    preprocessing: str = "auto",
) -> dict[str, Any]:
    """Run OCR on a single frame (contract API).

    Args:
        frame_path: Path to frame image.
        language: Tesseract language.
        config: Additional Tesseract config.
        preprocessing: Preprocessing method.

    Returns:
        OCR result dict.
    """
    return extract_text(frame_path, language, config, preprocessing)


# Contract API wrapper matching EXPECTED_OCR_FUNCTIONS signature
def run_ocr(image_path: str | Path) -> dict[str, Any]:
    """Run OCR on a single image (contract API - minimal signature).

    Args:
        image_path: Path to image file.

    Returns:
        OCR result dict with text, confidence, bounding_boxes.
    """
    return extract_text(image_path, language="eng", config=None, preprocessing="auto")


# ----------------------------------------------------------------------
# Additional Contract API functions (for test compatibility)
# ----------------------------------------------------------------------


from dataclasses import dataclass, field
from typing import Any


@dataclass
class OCRResult:
    """OCR result (contract API - matches test expectations)."""
    image_path: str = ""
    text: str = ""
    text_clean: str = ""
    confidence: float = 0.0
    bounding_boxes: list = field(default_factory=list)
    language: str = ""
    preprocessing: str = ""
    error: str | None = None


@dataclass
class OCRFrameResult:
    """OCR result for a single frame (contract API)."""
    frame: str = ""
    text: str = ""
    text_clean: str = ""
    confidence: float = 0.0
    bounding_boxes: list = field(default_factory=list)
    language: str = ""
    preprocessing: str = ""
    error: str | None = None


def ocr_frame(
    frame_path: str | Path,
    language: str = "eng",
    config: Optional[str] = None,
    preprocessing: str = "auto",
) -> OCRFrameResult:
    """Run OCR on a single frame and return OCRFrameResult (contract API).

    Args:
        frame_path: Path to frame image.
        language: Tesseract language.
        config: Additional Tesseract config.
        preprocessing: Preprocessing method.

    Returns:
        OCRFrameResult object.
    """
    result = extract_text(frame_path, language, config, preprocessing)
    return OCRFrameResult(
        frame=result.get("frame_path", ""),
        text=result.get("text", ""),
        text_clean=result.get("text_clean", ""),
        confidence=result.get("confidence", 0.0),
        bounding_boxes=result.get("bounding_boxes", []),
        language=result.get("language", ""),
        preprocessing=result.get("preprocessing", ""),
        error=result.get("error"),
    )


def preprocess_frame(
    frame_path: str | Path,
    method: str = "auto",
) -> np.ndarray:
    """Preprocess a frame image for OCR (contract API).

    Args:
        frame_path: Path to frame image.
        method: Preprocessing method ('none', 'grayscale', 'threshold', 'adaptive', 'auto').

    Returns:
        Preprocessed image as numpy array.
    """
    frame_path = Path(frame_path)
    img = cv2.imread(str(frame_path))
    if img is None:
        raise ValueError(f"Failed to load image: {frame_path}")

    if method == "auto":
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        mean_val = np.mean(gray)
        if mean_val < 128:
            gray = cv2.bitwise_not(gray)
        std_dev = np.std(gray)
        if std_dev < 30:
            return _preprocess_adaptive(gray)
        else:
            return _preprocess_threshold(gray)
    elif method == "grayscale":
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    elif method == "threshold":
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return _preprocess_threshold(gray)
    elif method == "adaptive":
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return _preprocess_adaptive(gray)
    else:
        return img
