"""
Sharpness and blur detection for video frames.

Uses Laplacian variance to compute image sharpness and filter out
unfocused or blurry frames prior to OCR and visual analysis.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def calculate_sharpness(image: str | Path | np.ndarray) -> float:
    """Calculate the sharpness score of an image using Laplacian variance.

    Higher values indicate sharper images; lower values indicate blurriness.

    Args:
        image: Path to image file, Path object, or numpy array.

    Returns:
        Sharpness score (variance of the Laplacian) as a float >= 0.0.
    """
    try:
        if isinstance(image, (str, Path)):
            img_path = Path(image)
            if not img_path.exists():
                return 0.0
            img = cv2.imread(str(img_path))
            if img is None:
                return 0.0
        elif isinstance(image, np.ndarray):
            img = image
        else:
            return 0.0

        if img.size == 0:
            return 0.0

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        score = float(laplacian.var())
        return round(max(score, 0.0), 2)
    except Exception as e:
        logger.debug("calculate_sharpness failed: %s", e)
        return 0.0


def is_blurry(image: str | Path | np.ndarray, threshold: float = 100.0) -> bool:
    """Determine whether an image is blurry based on a sharpness threshold.

    Args:
        image: Path to image file, Path object, or numpy array.
        threshold: Variance threshold below which an image is considered blurry.
            Defaults to 100.0.

    Returns:
        True if the image is considered blurry, False otherwise.
    """
    return calculate_sharpness(image) < threshold


def filter_blurry_frames(
    frames: list[Any],
    threshold: float = 100.0,
    min_keep: int = 1,
) -> list[Any]:
    """Filter out blurry frames, retaining only sharp keyframes.

    If filtering would discard all frames, keeps the top `min_keep` sharpest
    frames to ensure no complete loss of visual context.

    Args:
        frames: List of image paths (str | Path) or dicts with a 'frame_path' key.
        threshold: Minimum Laplacian variance to be considered sharp.
        min_keep: Minimum number of frames to retain even if all are below threshold.

    Returns:
        List of retained frames in their original order.
    """
    if not frames:
        return []

    scored_frames: list[tuple[int, Any, float]] = []

    for idx, item in enumerate(frames):
        if isinstance(item, dict):
            path_val = item.get("frame_path") or item.get("path")
            score = calculate_sharpness(path_val) if path_val else 0.0
        else:
            score = calculate_sharpness(item)
        scored_frames.append((idx, item, score))

    # Keep sharp frames
    sharp_frames = [item for item in scored_frames if item[2] >= threshold]

    # Fallback: if fewer than min_keep frames meet the threshold, take the sharpest ones
    if len(sharp_frames) < min_keep and scored_frames:
        sorted_by_score = sorted(scored_frames, key=lambda x: x[2], reverse=True)
        fallback = sorted_by_score[: max(min_keep, 1)]
        # Preserve original sequence order
        fallback.sort(key=lambda x: x[0])
        return [item[1] for item in fallback]

    # Sort back to original chronological order
    sharp_frames.sort(key=lambda x: x[0])
    return [item[1] for item in sharp_frames]
