"""
Unit tests for faster-whisper integration, quantization, and engine fallback.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from video_intake_core.policies import PolicyResolver
from video_intake_core.transcription import (
    detect_available_transcribers,
    load_faster_whisper_model,
    transcribe_with_faster_whisper,
    transcribe_with_whisper,
)

pytest.importorskip("faster_whisper")


class TestFasterWhisperUnit:
    """Tests for faster-whisper and transcription engine selection."""

    def test_detect_available_transcribers_includes_faster_whisper(self):
        """detect_available_transcribers reports faster_whisper availability."""
        res = detect_available_transcribers()
        assert "faster_whisper_installed" in res
        assert "whisper_installed" in res
        assert res["faster_whisper_installed"] is True
        assert res["faster_whisper_version"] is not None

    def test_load_faster_whisper_model_success(self):
        """load_faster_whisper_model instantiates WhisperModel."""
        with patch("faster_whisper.WhisperModel") as mock_model_cls:
            mock_inst = MagicMock()
            mock_model_cls.return_value = mock_inst

            model = load_faster_whisper_model(model_size="tiny", device="cpu", compute_type="int8")
            assert model == mock_inst
            mock_model_cls.assert_called_once_with("tiny", device="cpu", compute_type="int8")

    def test_load_faster_whisper_model_failure_returns_none(self):
        """load_faster_whisper_model returns None when loading fails."""
        with patch("faster_whisper.WhisperModel", side_effect=Exception("Model loading error")):
            model = load_faster_whisper_model(model_size="invalid", device="cpu")
            assert model is None

    def test_transcribe_with_faster_whisper_mocked(self, tmp_path: Path):
        """transcribe_with_faster_whisper processes segments and returns standard schema."""
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"dummy audio content")

        mock_seg1 = MagicMock()
        mock_seg1.start = 0.0
        mock_seg1.end = 2.5
        mock_seg1.text = " Hola mundo"
        mock_seg1.avg_logprob = -0.15
        mock_seg1.no_speech_prob = 0.01

        mock_seg2 = MagicMock()
        mock_seg2.start = 2.5
        mock_seg2.end = 5.0
        mock_seg2.text = " de prueba"
        mock_seg2.avg_logprob = -0.12
        mock_seg2.no_speech_prob = 0.02

        mock_info = MagicMock()
        mock_info.language = "es"
        mock_info.language_probability = 0.99
        mock_info.duration = 5.0

        with patch("faster_whisper.WhisperModel") as mock_model_cls:
            mock_model = MagicMock()
            mock_model.transcribe.return_value = ([mock_seg1, mock_seg2], mock_info)
            mock_model_cls.return_value = mock_model

            res = transcribe_with_faster_whisper(
                audio_file,
                model_size="base",
                device="cpu",
                compute_type="int8",
            )

            assert res["engine"] == "faster-whisper"
            assert res["full_text"] == "Hola mundo de prueba"
            assert len(res["segments"]) == 2
            assert res["segments"][0]["text"] == "Hola mundo"
            assert res["segments"][0]["start_seconds"] == 0.0
            assert res["segments"][0]["end_seconds"] == 2.5
            assert res["language"] == "es"
            assert res["language_probability"] == 0.99
            mock_model_cls.assert_called_once_with("base", device="cpu", compute_type="int8")

    def test_transcribe_with_whisper_auto_engine_calls_faster_whisper(self, tmp_path: Path):
        """engine='auto' prefers faster-whisper when available."""
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"dummy audio content")

        with patch("video_intake_core.transcription.transcribe_with_faster_whisper") as mock_fw:
            mock_fw.return_value = {
                "full_text": "Transcrito con faster-whisper",
                "segments": [
                    {"start": "0.000", "end": "2.000", "text": "Transcrito con faster-whisper"}
                ],
                "engine": "faster-whisper",
            }

            res = transcribe_with_whisper(audio_file, engine="auto")
            assert res["engine"] == "faster-whisper"
            assert mock_fw.called

    def test_transcribe_with_whisper_fallback_to_openai_whisper(self, tmp_path: Path):
        """When faster-whisper fails in auto mode, transparent fallback to openai-whisper occurs."""
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"dummy audio content")

        with (
            patch(
                "video_intake_core.transcription.transcribe_with_faster_whisper",
                side_effect=Exception("FW failed"),
            ),
            patch("whisper.load_model") as mock_load,
            patch("whisper.transcribe") as mock_tr,
        ):
            mock_load.return_value = MagicMock()
            mock_tr.return_value = {
                "text": "Fallback text from whisper",
                "segments": [{"start": 0.0, "end": 1.0, "text": "Fallback text from whisper"}],
                "language": "es",
            }

            res = transcribe_with_whisper(audio_file, engine="auto")
            assert res["engine"] == "whisper"
            assert "Fallback text from whisper" in res["full_text"]

    def test_transcribe_with_whisper_forced_engine_whisper(self, tmp_path: Path):
        """engine='whisper' directly executes openai-whisper without attempting faster-whisper."""
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"dummy audio content")

        with (
            patch("video_intake_core.transcription.transcribe_with_faster_whisper") as mock_fw,
            patch("whisper.load_model") as mock_load,
            patch("whisper.transcribe") as mock_tr,
        ):
            mock_load.return_value = MagicMock()
            mock_tr.return_value = {
                "text": "Direct whisper text",
                "segments": [{"start": 0.0, "end": 1.0, "text": "Direct whisper text"}],
                "language": "es",
            }

            res = transcribe_with_whisper(audio_file, engine="whisper")
            assert res["engine"] == "whisper"
            assert not mock_fw.called

    def test_transcription_policy_engine_and_compute_type(self, monkeypatch: pytest.MonkeyPatch):
        """PolicyResolver properly resolves engine, compute_type and environment overrides."""
        resolver = PolicyResolver()
        assert resolver.get_transcription_engine() in {"auto", "faster-whisper", "whisper"}
        assert resolver.get_transcription_compute_type() in {"int8", "float16", "default"}

        monkeypatch.setenv("VITK_TRANSCRIPTION_ENGINE", "faster-whisper")
        monkeypatch.setenv("VITK_TRANSCRIPTION_COMPUTE_TYPE", "float16")

        assert resolver.get_transcription_engine() == "faster-whisper"
        assert resolver.get_transcription_compute_type() == "float16"

    def test_load_faster_whisper_model_cpu_float16_auto_adjusts_to_int8(self):
        """When float16 is passed for CPU device, it auto-adjusts to int8 to avoid CTranslate2 crash."""
        with patch("faster_whisper.WhisperModel") as mock_model_cls:
            mock_inst = MagicMock()
            mock_model_cls.return_value = mock_inst

            model = load_faster_whisper_model(
                model_size="tiny", device="cpu", compute_type="float16"
            )
            assert model == mock_inst
            mock_model_cls.assert_called_once_with("tiny", device="cpu", compute_type="int8")
