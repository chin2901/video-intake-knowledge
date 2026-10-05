"""
Slide and code screen change detection using perceptual similarity (SSIM / MSE).

Filters duplicate and near-identical consecutive frames in presentations,
tutorials, and terminal recordings, preserving keyframes at true transition points.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def _load_and_normalize(
    image: str | Path | np.ndarray,
    target_size: tuple[int, int] = (320, 240),
) -> np.ndarray | None:
    """Load image as grayscale float array resized for fast comparison."""
    try:
        if isinstance(image, (str, Path)):
            p = Path(image)
            if not p.exists():
                return None
            img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        elif isinstance(image, np.ndarray):
            if image.size == 0:
                return None
            img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        else:
            return None

        if img is None or img.size == 0:
            return None

        if (img.shape[1], img.shape[0]) != target_size:
            img = cv2.resize(img, target_size, interpolation=cv2.INTER_AREA)

        return img.astype(np.float64)
    except Exception as e:
        logger.debug("Image loading/normalization failed: %s", e)
        return None


def calculate_mse(
    image1: str | Path | np.ndarray,
    image2: str | Path | np.ndarray,
) -> float:
    """Compute Mean Squared Error (MSE) between two frames.

    Args:
        image1: First frame (path or numpy array).
        image2: Second frame (path or numpy array).

    Returns:
        MSE value >= 0.0. Lower values indicate higher similarity (0.0 = identical).
    """
    img1 = _load_and_normalize(image1)
    img2 = _load_and_normalize(image2)
    if img1 is None or img2 is None:
        return 1e6

    err = np.mean((img1 - img2) ** 2)
    return round(float(err), 4)


def calculate_ssim(
    image1: str | Path | np.ndarray,
    image2: str | Path | np.ndarray,
) -> float:
    """Compute Structural Similarity Index (SSIM) between two frames.

    Args:
        image1: First frame (path or numpy array).
        image2: Second frame (path or numpy array).

    Returns:
        SSIM value between 0.0 and 1.0 (1.0 = identical).
    """
    img1 = _load_and_normalize(image1)
    img2 = _load_and_normalize(image2)
    if img1 is None or img2 is None:
        return 0.0

    # Short-circuit identical arrays
    if np.array_equal(img1, img2):
        return 1.0

    # Constants to avoid division by zero
    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2

    # Gaussian blur for local means
    ksize = (11, 11)
    sigma = 1.5
    mu1 = cv2.GaussianBlur(img1, ksize, sigma)
    mu2 = cv2.GaussianBlur(img2, ksize, sigma)

    mu1_sq = mu1 * mu1
    mu2_sq = mu2 * mu2
    mu1_mu2 = mu1 * mu2

    sigma1_sq = cv2.GaussianBlur(img1 * img1, ksize, sigma) - mu1_sq
    sigma2_sq = cv2.GaussianBlur(img2 * img2, ksize, sigma) - mu2_sq
    sigma12 = cv2.GaussianBlur(img1 * img2, ksize, sigma) - mu1_mu2

    numerator = (2 * mu1_mu2 + c1) * (2 * sigma12 + c2)
    denominator = (mu1_sq + mu2_sq + c1) * (sigma1_sq + sigma2_sq + c2)

    ssim_map = numerator / denominator
    score = float(np.mean(ssim_map))
    return round(float(np.clip(score, 0.0, 1.0)), 4)


def calculate_frame_similarity(
    image1: str | Path | np.ndarray,
    image2: str | Path | np.ndarray,
) -> float:
    """Compute combined perceptual similarity score between two frames.

    Combines SSIM (75%) and normalized MSE (25%) into a unified [0.0, 1.0] metric.

    Args:
        image1: First frame.
        image2: Second frame.

    Returns:
        Similarity score from 0.0 (completely distinct) to 1.0 (identical).
    """
    ssim = calculate_ssim(image1, image2)
    mse = calculate_mse(image1, image2)

    # Normalize MSE: typical max MSE for 8-bit images is 255^2 = 65025
    # An MSE > 4000 indicates a major visual shift
    mse_norm = max(0.0, 1.0 - (mse / 4000.0))

    combined = (0.75 * ssim) + (0.25 * mse_norm)
    return round(float(np.clip(combined, 0.0, 1.0)), 4)


def filter_duplicate_frames(
    frames: list[Any],
    similarity_threshold: float = 0.92,
    preserve_first: bool = True,
) -> list[Any]:
    """Filter out duplicate or near-identical frames, keeping genuine slide changes.

    Compares consecutive frames; if similarity exceeds the threshold, the frame
    is recognized as the same slide/screen and omitted.

    Args:
        frames: List of image paths (str | Path) or dicts with 'frame_path'.
        similarity_threshold: Similarity above which a frame is considered duplicate.
            Default is 0.92 (92% visual match).
        preserve_first: Whether to always retain the very first frame.

    Returns:
        List of deduplicated keyframes representing distinct visual states.
    """
    if not frames:
        return []

    if len(frames) == 1:
        return list(frames)

    def _get_path(item: Any) -> Any:
        if isinstance(item, dict):
            return item.get("frame_path") or item.get("path")
        return item

    retained: list[Any] = []
    last_retained_path: Any = None

    for item in frames:
        current_path = _get_path(item)
        if not current_path:
            continue

        if not retained:
            if preserve_first:
                retained.append(item)
                last_retained_path = current_path
            continue

        sim = calculate_frame_similarity(last_retained_path, current_path)
        if sim < similarity_threshold:
            # Significant visual change detected (new slide or screen layout)
            retained.append(item)
            last_retained_path = current_path

    # Safety: ensure at least one frame is retained
    if not retained and frames:
        retained.append(frames[0])

    return retained


def detect_slide_transitions(
    frames: list[Any],
    change_threshold: float = 0.15,
) -> list[dict[str, Any]]:
    """Detect specific transition events between consecutive frames.

    Args:
        frames: List of image paths or dicts.
        change_threshold: Minimum visual distance (1.0 - similarity) to flag transition.

    Returns:
        List of transition dicts with index, similarity, change_amount, and paths.
    """
    transitions: list[dict[str, Any]] = []
    if len(frames) < 2:
        return transitions

    def _get_path(item: Any) -> Any:
        if isinstance(item, dict):
            return item.get("frame_path") or item.get("path")
        return item

    for idx in range(len(frames) - 1):
        p1 = _get_path(frames[idx])
        p2 = _get_path(frames[idx + 1])
        if not p1 or not p2:
            continue

        sim = calculate_frame_similarity(p1, p2)
        change = round(1.0 - sim, 4)
        is_transition = change >= change_threshold

        transitions.append(
            {
                "from_index": idx,
                "to_index": idx + 1,
                "from_frame": str(p1),
                "to_frame": str(p2),
                "similarity": sim,
                "change_score": change,
                "is_transition": is_transition,
            }
        )

    return transitions
