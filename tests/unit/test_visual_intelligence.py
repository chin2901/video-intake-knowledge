"""
Unit tests for Advanced Visual Intelligence (Fase 3):
- Laplacian Variance sharpness filtering and blur detection
- Perceptual similarity (SSIM / MSE) slide and screen deduplication
- Code and technical terminal detection from OCR text
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest
from video_intake_core.visual import (
    calculate_frame_similarity,
    calculate_mse,
    calculate_sharpness,
    calculate_ssim,
    detect_code_content,
    detect_slide_transitions,
    enrich_ocr_with_code_detection,
    filter_blurry_frames,
    filter_duplicate_frames,
    format_technical_ocr,
    is_blurry,
)


class TestSharpnessAndBlurFilter:
    """Tests for Laplacian Variance sharpness calculation and blurry frame filtering."""

    @pytest.fixture
    def sharp_image(self) -> np.ndarray:
        """Create a high-contrast sharp checkerboard image."""
        img = np.zeros((300, 300, 3), dtype=np.uint8)
        # Create alternating black and white squares for sharp edges
        for i in range(0, 300, 30):
            for j in range(0, 300, 30):
                if (i // 30 + j // 30) % 2 == 0:
                    img[i : i + 30, j : j + 30] = 255
        return img

    @pytest.fixture
    def blurry_image(self, sharp_image: np.ndarray) -> np.ndarray:
        """Create a blurry version using heavy Gaussian blur."""
        return cv2.GaussianBlur(sharp_image, (35, 35), 15.0)

    def test_sharp_image_has_high_variance(self, sharp_image: np.ndarray):
        score = calculate_sharpness(sharp_image)
        assert score > 100.0
        assert not is_blurry(sharp_image, threshold=100.0)

    def test_blurry_image_has_low_variance(self, blurry_image: np.ndarray):
        score = calculate_sharpness(blurry_image)
        assert score < 50.0
        assert is_blurry(blurry_image, threshold=100.0)

    def test_invalid_and_empty_inputs_handled_safely(self, tmp_path: Path):
        assert calculate_sharpness(tmp_path / "non_existent.png") == 0.0
        assert calculate_sharpness(np.zeros((0, 0), dtype=np.uint8)) == 0.0
        assert is_blurry(tmp_path / "non_existent.png") is True

    def test_filter_blurry_frames_separates_quality(
        self, sharp_image: np.ndarray, blurry_image: np.ndarray, tmp_path: Path
    ):
        p_sharp = tmp_path / "sharp.png"
        p_blur = tmp_path / "blur.png"
        cv2.imwrite(str(p_sharp), sharp_image)
        cv2.imwrite(str(p_blur), blurry_image)

        frames = [str(p_sharp), str(p_blur)]
        filtered = filter_blurry_frames(frames, threshold=100.0)

        assert len(filtered) == 1
        assert filtered[0] == str(p_sharp)

    def test_filter_blurry_frames_min_keep_fallback(self, blurry_image: np.ndarray, tmp_path: Path):
        """Even if all frames are below threshold, min_keep prevents complete loss."""
        p_blur1 = tmp_path / "blur1.png"
        p_blur2 = tmp_path / "blur2.png"
        cv2.imwrite(str(p_blur1), blurry_image)
        cv2.imwrite(str(p_blur2), cv2.GaussianBlur(blurry_image, (15, 15), 5.0))

        frames = [str(p_blur1), str(p_blur2)]
        filtered = filter_blurry_frames(frames, threshold=500.0, min_keep=1)

        assert len(filtered) == 1
        # The slightly less blurry one (blur1, which did not undergo extra gaussian blur) is kept
        assert filtered[0] == str(p_blur1)

    def test_filter_blurry_frames_with_dicts(self, sharp_image: np.ndarray, tmp_path: Path):
        p_sharp = tmp_path / "sharp.png"
        cv2.imwrite(str(p_sharp), sharp_image)

        frame_dict = {"frame_path": str(p_sharp), "timestamp": 12.5}
        filtered = filter_blurry_frames([frame_dict], threshold=50.0)
        assert len(filtered) == 1
        assert filtered[0]["timestamp"] == 12.5


class TestSlideAndScreenDeduplication:
    """Tests for SSIM, MSE, and slide transition / deduplication."""

    @pytest.fixture
    def base_slide(self) -> np.ndarray:
        """Create a presentation-like slide with white background and black text boxes."""
        img = np.full((240, 320, 3), 255, dtype=np.uint8)
        # Header banner
        img[20:60, 20:300] = (200, 50, 50)
        # Bullet point boxes
        img[90:110, 40:280] = (50, 50, 50)
        img[130:150, 40:250] = (50, 50, 50)
        return img

    @pytest.fixture
    def modified_slide(self, base_slide: np.ndarray) -> np.ndarray:
        """Create a new slide with different content layout."""
        img = np.full((240, 320, 3), 255, dtype=np.uint8)
        # Green header
        img[20:60, 20:300] = (50, 180, 50)
        # Large central block (e.g. code/diagram)
        img[80:200, 40:280] = (30, 30, 30)
        return img

    def test_identical_images_have_maximum_similarity(self, base_slide: np.ndarray):
        ssim = calculate_ssim(base_slide, base_slide)
        mse = calculate_mse(base_slide, base_slide)
        sim = calculate_frame_similarity(base_slide, base_slide)

        assert ssim == 1.0
        assert mse == 0.0
        assert sim == 1.0

    def test_minor_noise_has_high_similarity(self, base_slide: np.ndarray):
        """Minor changes (speaker cam overlay or slight flicker) retain high similarity."""
        noisy = base_slide.copy()
        # Add small 10x10 corner watermark
        noisy[210:230, 280:310] = (100, 100, 100)

        ssim = calculate_ssim(base_slide, noisy)
        sim = calculate_frame_similarity(base_slide, noisy)

        assert ssim > 0.90
        assert sim > 0.90

    def test_distinct_slides_have_lower_similarity(
        self, base_slide: np.ndarray, modified_slide: np.ndarray
    ):
        sim = calculate_frame_similarity(base_slide, modified_slide)
        assert sim < 0.70

    def test_filter_duplicate_frames_keeps_real_transitions(
        self, base_slide: np.ndarray, modified_slide: np.ndarray, tmp_path: Path
    ):
        p1 = tmp_path / "slide1_t0.png"
        p2 = tmp_path / "slide1_t5.png"  # identical to p1
        p3 = tmp_path / "slide1_t10.png"  # identical to p1
        p4 = tmp_path / "slide2_t15.png"  # new slide
        p5 = tmp_path / "slide2_t20.png"  # identical to p4

        cv2.imwrite(str(p1), base_slide)
        cv2.imwrite(str(p2), base_slide)
        cv2.imwrite(str(p3), base_slide)
        cv2.imwrite(str(p4), modified_slide)
        cv2.imwrite(str(p5), modified_slide)

        frames = [str(p1), str(p2), str(p3), str(p4), str(p5)]
        deduped = filter_duplicate_frames(frames, similarity_threshold=0.92)

        # Should keep slide 1 once and slide 2 once
        assert len(deduped) == 2
        assert deduped[0] == str(p1)
        assert deduped[1] == str(p4)

    def test_detect_slide_transitions_records_changes(
        self, base_slide: np.ndarray, modified_slide: np.ndarray, tmp_path: Path
    ):
        p1 = tmp_path / "f1.png"
        p2 = tmp_path / "f2.png"
        cv2.imwrite(str(p1), base_slide)
        cv2.imwrite(str(p2), modified_slide)

        transitions = detect_slide_transitions([str(p1), str(p2)], change_threshold=0.15)
        assert len(transitions) == 1
        assert transitions[0]["is_transition"] is True
        assert transitions[0]["change_score"] > 0.15


class TestCodeAndTerminalDetection:
    """Tests for detecting programming languages and syntax formatting in OCR text."""

    def test_detect_python_code(self):
        code_sample = """
import os
import sys

def calculate_metrics(values: list[float]) -> float:
    total = sum(values)
    return total / len(values) if values else 0.0

if __name__ == '__main__':
    print(calculate_metrics([1.0, 2.0, 3.0]))
"""
        result = detect_code_content(code_sample)
        assert result["is_code"] is True
        assert result["language"] == "python"
        assert result["confidence"] > 0.70
        assert "```python" in result["formatted_markdown"]
        assert "def calculate_metrics" in result["formatted_markdown"]

    def test_detect_bash_terminal(self):
        terminal_sample = """
$ sudo apt-get update && sudo apt-get install -y docker.io
$ docker pull postgres:15-alpine
$ docker run -d --name pg-test -e POSTGRES_PASSWORD=secret -p 5432:5432 postgres:15-alpine
$ docker ps
"""
        result = detect_code_content(terminal_sample)
        assert result["is_code"] is True
        assert result["language"] == "bash"
        assert result["confidence"] > 0.70
        assert "```bash" in result["formatted_markdown"]

    def test_detect_typescript_code(self):
        ts_sample = """
export interface UserProfile {
    id: string;
    username: string;
    active: boolean;
}

export const fetchProfile = async (id: string): Promise<UserProfile> => {
    const res = await fetch(`/api/users/${id}`);
    return res.json();
};
"""
        result = detect_code_content(ts_sample)
        assert result["is_code"] is True
        assert result["language"] in ("typescript", "javascript")
        assert "```" in result["formatted_markdown"]

    def test_plain_text_not_flagged_as_code(self):
        plain_text = """
En este video explicaremos la evolución histórica de los sistemas informáticos
en Europa durante el siglo XX. Veremos cómo se fundaron las primeras empresas
y cómo cambiaron las industrias de telecomunicación.
"""
        result = detect_code_content(plain_text)
        assert result["is_code"] is False
        assert "```" not in result["formatted_markdown"]
        assert result["formatted_markdown"] == plain_text.strip()

    def test_empty_text_handled_safely(self):
        result = detect_code_content("")
        assert result["is_code"] is False
        assert result["formatted_markdown"] == ""

    def test_format_technical_ocr(self):
        raw = "git status\ngit commit -m 'feat: add vision pipeline'\ngit push"
        formatted = format_technical_ocr(raw)
        assert "```bash" in formatted
        assert "git commit" in formatted

    def test_enrich_ocr_with_code_detection(self):
        ocr_item = {
            "frame_path": "/path/to/frame_0001.png",
            "text": "def hello():\n    return 'world'",
            "confidence": 95.0,
        }
        enriched = enrich_ocr_with_code_detection(ocr_item)
        assert enriched["is_code"] is True
        assert enriched["code_language"] == "python"
        assert "```python" in enriched["formatted_markdown"]
