"""
Unit tests for the 'Zero-GPU / Subtitles First' strategy and fast native subtitle extraction.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from video_intake_core.orchestrator import check_and_extract
from video_intake_core.transcription import (
    _parse_subtitle_content,
    _select_best_subtitle_track,
    clean_and_deduplicate_segments,
    extract_fast_native_subtitles,
    extract_local_captions,
    format_seconds_to_timestamp,
    format_subtitles_to_markdown,
    parse_srt,
    parse_srv_xml,
    parse_vtt,
)


class TestSubtitlesFirstUnit:
    """Tests for fast subtitle extraction, cue cleaning, and zero-GPU strategy."""

    def test_format_seconds_to_timestamp(self):
        """Timestamp formatting handles sub-minute, minutes, and hours."""
        assert format_seconds_to_timestamp(5.0) == "00:05"
        assert format_seconds_to_timestamp(65.0) == "01:05"
        assert format_seconds_to_timestamp(3665.0) == "01:01:05"
        assert format_seconds_to_timestamp(-10.0) == "00:00"

    def test_clean_and_deduplicate_segments_html_and_rolling(self):
        """Cleans HTML tags and deduplicates repeated rolling cues from YouTube."""
        raw_segments = [
            {
                "start": "00:00:01.000",
                "end": "00:00:03.000",
                "start_seconds": 1.0,
                "end_seconds": 3.0,
                "text": "<c>Bienvenidos</c> a este",
            },
            {
                # Rolling prefix extension
                "start": "00:00:02.000",
                "end": "00:00:04.500",
                "start_seconds": 2.0,
                "end_seconds": 4.5,
                "text": "Bienvenidos a este nuevo vídeo tutorial",
            },
            {
                # Duplicate consecutive cue
                "start": "00:00:04.500",
                "end": "00:00:05.500",
                "start_seconds": 4.5,
                "end_seconds": 5.5,
                "text": "Bienvenidos a este nuevo vídeo tutorial",
            },
            {
                # Distinct next sentence
                "start": "00:00:06.000",
                "end": "00:00:09.000",
                "start_seconds": 6.0,
                "end_seconds": 9.0,
                "text": "Hoy vamos a ver la velocidad Zero-GPU.",
            },
        ]

        cleaned = clean_and_deduplicate_segments(raw_segments)
        assert len(cleaned) == 2
        assert cleaned[0]["text"] == "Bienvenidos a este nuevo vídeo tutorial"
        assert cleaned[0]["start_seconds"] == 1.0
        assert cleaned[0]["end_seconds"] == 5.5
        assert cleaned[1]["text"] == "Hoy vamos a ver la velocidad Zero-GPU."

    def test_format_subtitles_to_markdown(self):
        """Formats segments cleanly into Markdown with timestamps."""
        segments = [
            {
                "start_seconds": 0.0,
                "end_seconds": 4.5,
                "text": "Introducción y bienvenida.",
            },
            {
                "start_seconds": 4.5,
                "end_seconds": 12.0,
                "text": "Demostración de extracción en menos de 1 segundo.",
            },
        ]
        md = format_subtitles_to_markdown(
            segments,
            source_info={
                "title": "Tutorial AibOS",
                "language": "es",
                "sub_type": "Subtítulos oficiales (Zero-GPU)",
            },
        )
        assert "# Transcripción" in md
        assert "**Fuente:** Tutorial AibOS"
        assert "**Idioma:** es"
        assert "**[00:00 → 00:04]** Introducción y bienvenida." in md
        assert "**[00:04 → 00:12]** Demostración de extracción en menos de 1 segundo." in md

    def test_parse_vtt_with_short_and_long_timestamps(self):
        """parse_vtt parses both MM:SS.mmm and HH:MM:SS.mmm."""
        vtt_content = (
            "WEBVTT\n\n"
            "00:01.000 --> 00:04.000\n"
            "Hola mundo en MM:SS\n\n"
            "01:00:05.000 --> 01:00:08.500\n"
            "Hola mundo en HH:MM:SS\n\n"
        )
        segs = parse_vtt(vtt_content)
        assert len(segs) == 2
        assert segs[0]["text"] == "Hola mundo en MM:SS"
        assert segs[0]["start_seconds"] == 1.0
        assert segs[1]["text"] == "Hola mundo en HH:MM:SS"
        assert segs[1]["start_seconds"] == 3605.0

    def test_select_best_subtitle_track_precedence(self):
        """_select_best_subtitle_track respects strict language and official-first precedence."""
        captions = {
            "en": [{"url": "http://example.com/en.vtt", "ext": "vtt"}],
            "es": [{"url": "http://example.com/es.vtt", "ext": "vtt"}],
        }
        auto_captions = {
            "es": [{"url": "http://example.com/es_auto.vtt", "ext": "vtt"}],
            "fr": [{"url": "http://example.com/fr_auto.vtt", "ext": "vtt"}],
        }

        # 1. Official Spanish should win over auto Spanish and English
        lang, track, is_auto = _select_best_subtitle_track(
            captions, auto_captions, preferred_lang="es"
        )
        assert lang == "es"
        assert track["url"] == "http://example.com/es.vtt"
        assert is_auto is False

        # 2. When only auto Spanish is available
        captions_no_es = {"en": [{"url": "http://example.com/en.vtt", "ext": "vtt"}]}
        lang, track, is_auto = _select_best_subtitle_track(
            captions_no_es, auto_captions, preferred_lang="es"
        )
        assert lang == "es"
        assert track["url"] == "http://example.com/es_auto.vtt"
        assert is_auto is True

        # 3. When preferred language is not available, falls back to English or first available
        lang, track, is_auto = _select_best_subtitle_track(captions_no_es, {}, preferred_lang="it")
        assert lang == "en"

    def test_extract_fast_native_subtitles_local_file(self, tmp_path: Path):
        """extract_fast_native_subtitles instantly parses adjacent .srt file for local video."""
        video_path = tmp_path / "video.mp4"
        video_path.write_bytes(b"dummy video bytes")

        srt_path = tmp_path / "video.srt"
        srt_path.write_text(
            "1\n00:00:00,000 --> 00:00:02,000\nSubtítulo local adyacente.\n\n",
            encoding="utf-8",
        )

        res = extract_fast_native_subtitles(video_path, language="es")
        assert res is not None
        assert res["strategy"] == "native_subtitles_zero_gpu"
        assert len(res["segments"]) == 1
        assert "Subtítulo local adyacente." in res["full_text"]
        assert "**[00:00 → 00:02]** Subtítulo local adyacente." in res["markdown"]

    def test_extract_fast_native_subtitles_remote_url(self):
        """extract_fast_native_subtitles downloads only the best track and formats in <1s."""
        fake_vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:05.000\nTexto de YouTube en VTT\n\n"

        fake_info = {
            "title": "Vídeo YouTube Test",
            "subtitles": {"es": [{"url": "https://video.test/es.vtt", "ext": "vtt"}]},
            "automatic_captions": {},
        }

        with patch("yt_dlp.YoutubeDL") as mock_ydl_cls:
            mock_ydl = MagicMock()
            mock_ydl.extract_info.return_value = fake_info
            mock_ydl_cls.return_value.__enter__.return_value = mock_ydl

            mock_resp = MagicMock()
            mock_resp.read.return_value = fake_vtt.encode("utf-8")
            with patch("urllib.request.urlopen") as mock_urlopen:
                mock_urlopen.return_value.__enter__.return_value = mock_resp

                res = extract_fast_native_subtitles(
                    "https://www.youtube.com/watch?v=dummy123", language="es"
                )
                assert res is not None
                assert res["strategy"] == "native_subtitles_zero_gpu"
                assert "Texto de YouTube en VTT" in res["full_text"]
                assert res["language"] == "es"
                assert res["is_auto"] is False

    def test_extract_local_captions_contract_helper(self, tmp_path: Path):
        """extract_local_captions finds adjacent subtitle and returns clean segments."""
        video = tmp_path / "sample.mp4"
        video.write_bytes(b"dummy")
        vtt = tmp_path / "sample.vtt"
        vtt.write_text(
            "WEBVTT\n\n00:00:00.000 --> 00:00:03.000\nTexto local VTT\n\n", encoding="utf-8"
        )

        segments = extract_local_captions(video)
        assert len(segments) == 1
        assert segments[0]["text"] == "Texto local VTT"

    def test_orchestrator_zero_gpu_bypasses_whisper(self, tmp_path: Path):
        """Orchestrator uses Zero-GPU native subtitles and avoids loading/running Whisper."""
        video_file = tmp_path / "test_vid.mp4"
        video_file.write_bytes(b"dummy")
        srt_file = tmp_path / "test_vid.srt"
        srt_file.write_text(
            "1\n00:00:00,000 --> 00:00:02,000\nSubtítulo Zero-GPU instantáneo.\n\n",
            encoding="utf-8",
        )

        sources = [
            {
                "type": "local",
                "resolved_url": str(video_file),
                "platform": "local",
                "title": "test_zero_gpu",
                "is_local": True,
            }
        ]

        with patch("video_intake_core.transcription.transcribe_with_whisper") as mock_whisper:
            # Operación 3 = Transcripción
            artifacts = check_and_extract(sources, {3}, tmp_path)

            # Whisper NUNCA debe ser llamado porque los subtítulos nativos ya proporcionaron la transcripción
            assert not mock_whisper.called
            assert "transcript" in artifacts["files"]
            transcript_content = Path(artifacts["files"]["transcript"]).read_text(encoding="utf-8")
            assert "Subtítulo Zero-GPU instantáneo." in transcript_content
            assert "**[00:00 → 00:02]**" in transcript_content

    def test_parse_vtt_and_srt_crlf_and_bom(self):
        """parse_vtt and parse_srt handle Windows CRLF endings and UTF-8 BOM."""
        crlf_vtt = "\ufeffWEBVTT\r\n\r\n00:01.000 --> 00:04.000\r\nTexto VTT CRLF\r\n\r\n"
        segs_vtt = parse_vtt(crlf_vtt)
        assert len(segs_vtt) == 1
        assert segs_vtt[0]["text"] == "Texto VTT CRLF"
        assert segs_vtt[0]["start_seconds"] == 1.0

        crlf_srt = "\ufeff1\r\n00:00:01,000 --> 00:00:04,000\r\nTexto SRT CRLF\r\n\r\n2\r\n00:00:04,000 --> 00:00:08,000\r\nSegundo segmento\r\n\r\n"
        segs_srt = parse_srt(crlf_srt)
        assert len(segs_srt) == 2
        assert segs_srt[0]["text"] == "Texto SRT CRLF"
        assert segs_srt[1]["text"] == "Segundo segmento"

    def test_parse_vtt_single_digit_hour(self):
        """parse_vtt handles single-digit hour timestamps (e.g. 1:02:03.456)."""
        content = "WEBVTT\n\n1:02:03.456 --> 1:02:06.000\nSubtítulo tras una hora\n\n"
        segs = parse_vtt(content)
        assert len(segs) == 1
        assert segs[0]["text"] == "Subtítulo tras una hora"
        assert segs[0]["start_seconds"] == 3723.456
        assert segs[0]["end_seconds"] == 3726.0

    def test_clean_and_deduplicate_unescapes_html_entities(self):
        """clean_and_deduplicate_segments decodes HTML entities properly."""
        raw = [
            {
                "start_seconds": 0.0,
                "end_seconds": 3.0,
                "text": "Don&#39;t worry &amp; &quot;be happy&quot; &lt;now&gt;",
            }
        ]
        cleaned = clean_and_deduplicate_segments(raw)
        assert len(cleaned) == 1
        assert cleaned[0]["text"] == 'Don\'t worry & "be happy"'

    def test_parse_srv_xml_and_content_detection(self):
        """parse_srv_xml parses YouTube XML format and _parse_subtitle_content detects it."""
        xml = (
            '<?xml version="1.0" encoding="utf-8" ?>\n'
            "<transcript>\n"
            '  <text start="1.5" dur="3.0">YouTube XML subtítulo &amp; prueba</text>\n'
            "</transcript>"
        )
        segs = parse_srv_xml(xml)
        assert len(segs) == 1
        assert segs[0]["text"] == "YouTube XML subtítulo & prueba"
        assert segs[0]["start_seconds"] == 1.5
        assert segs[0]["end_seconds"] == 4.5

        detected_segs = _parse_subtitle_content(xml, "es", is_auto=True)
        assert len(detected_segs) == 1
        assert detected_segs[0]["source"] == "auto_captions"
        assert detected_segs[0]["language"] == "es"

    def test_select_best_subtitle_track_prefers_vtt_over_srv1(self):
        """_select_best_subtitle_track selects VTT format even when srv1 is first in list."""
        captions = {
            "es": [
                {"ext": "srv1", "url": "https://video.test/es.srv1"},
                {"ext": "vtt", "url": "https://video.test/es.vtt"},
            ]
        }
        lang, track, is_auto = _select_best_subtitle_track(captions, {}, preferred_lang="es")
        assert lang == "es"
        assert track["ext"] == "vtt"
        assert track["url"] == "https://video.test/es.vtt"
