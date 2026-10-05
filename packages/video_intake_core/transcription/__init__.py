"""
Video transcription module.

Supports multiple transcription strategies:
1. Platform captions/subtitles (preferred)
2. Downloaded subtitle files (SRT, VTT, ASS, SSA, JSON3)
3. Local Whisper models (faster-whisper, whisper.cpp, openai-whisper)
4. Configured external models

All transcription results include timestamps, segments, detected language,
and confidence scores where available.
"""

from __future__ import annotations

import html
import json as _json
import logging
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Optional

from ..utils import detect_language_code

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Subtitle file parsers
# ---------------------------------------------------------------------------


def parse_srt(content: str) -> list[dict[str, Any]]:
    """Parse SRT subtitle content into structured segments.

    Args:
        content: Raw SRT content as string.

    Returns:
        List of dicts with: index, start, end, text, start_seconds, end_seconds.
    """
    segments: list[dict[str, Any]] = []
    if not content or not content.strip():
        return segments

    # Normalize line endings and strip UTF-8 BOM
    content = content.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")

    # SRT format: index, timestamp line, text lines, blank line
    pattern = re.compile(
        r"^(\d+)\s*\n"
        r"((?:\d+:)?\d{2}:\d{2}[.,]\d{3})\s*-->\s*((?:\d+:)?\d{2}:\d{2}[.,]\d{3})"
        r"(?:\s*\n)?"
        r"((?:.*\n?)*?)"
        r"(?=\n\n|\n\d+\s*\n|$)",
        re.MULTILINE,
    )

    for match in pattern.finditer(content):
        index = int(match.group(1))
        start_str = match.group(2).strip().replace(",", ".")
        end_str = match.group(3).strip().replace(",", ".")
        raw_text = match.group(4).strip()
        text = html.unescape(raw_text).strip()

        if not text:
            continue

        s_sec = _time_to_seconds(start_str)
        e_sec = _time_to_seconds(end_str)

        segments.append(
            {
                "index": index,
                "start": start_str,
                "end": end_str,
                "text": text,
                "start_seconds": s_sec,
                "end_seconds": e_sec,
                "duration": e_sec - s_sec,
                "source": "srt",
                "generated": False,
            }
        )

    return segments


def parse_vtt(content: str) -> list[dict[str, Any]]:
    """Parse VTT (WebVTT) subtitle content into structured segments.

    Args:
        content: Raw VTT content string.

    Returns:
        List of segment dicts with timing and cleaned text.
    """
    segments: list[dict[str, Any]] = []
    if not content or not content.strip():
        return segments

    # Normalize line endings and strip UTF-8 BOM
    content = content.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")

    # Strip WEBVTT header and metadata
    if content.startswith("WEBVTT"):
        parts = content.split("\n\n", 1)
        content = parts[1] if len(parts) > 1 else ""

    blocks = re.split(r"\n\s*\n+", content.strip())
    # Support both MM:SS.mmm and (H)H:MM:SS.mmm
    time_re = re.compile(r"((?:\d+:)?\d{2}:\d{2}[.,]\d{3})\s*-->\s*((?:\d+:)?\d{2}:\d{2}[.,]\d{3})")

    index = 0
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue

        arrow_idx = -1
        m = None
        for i, line in enumerate(lines):
            m = time_re.search(line)
            if m:
                arrow_idx = i
                break

        if arrow_idx == -1 or not m:
            continue

        start_str = m.group(1).replace(",", ".")
        end_str = m.group(2).replace(",", ".")

        text_lines = lines[arrow_idx + 1 :]
        raw_text = " ".join(text_lines)
        text = re.sub(r"<[^>]+>", "", raw_text)
        text = html.unescape(text).strip()
        if not text:
            continue

        index += 1
        s_sec = _time_to_seconds(start_str)
        e_sec = _time_to_seconds(end_str)

        segments.append(
            {
                "index": index,
                "start": start_str,
                "end": end_str,
                "text": text,
                "start_seconds": s_sec,
                "end_seconds": e_sec,
                "duration": e_sec - s_sec,
                "source": "vtt",
                "generated": False,
            }
        )

    return segments


def parse_ass(content: str) -> list[dict[str, Any]]:
    """Parse ASS/SSA subtitle content into segments.

    Args:
        content: Raw ASS/SSA content.

    Returns:
        List of segment dicts.
    """
    segments: list[dict[str, Any]] = []

    # Find Dialogue lines: Dialogue: layer, start, end, style, name, marginL, marginR, marginV, effect, text
    pattern = re.compile(
        r"Dialogue:\s*(\d+),"
        r"(\d{2}:\d{2}:\d{2}\.\d{2}),"
        r"(\d{2}:\d{2}:\d{2}\.\d{2}),"
        r"(?:comment|text),"
        r".*?,"
        r"\".*?\""
        r",(?:.*?),"
        r"\"(.*?)\"",
    )

    for match in pattern.finditer(content):
        start_str = match.group(2)
        end_str = match.group(3)
        text = match.group(4).strip()

        # Clean ASS markup
        text = re.sub(r"\\N", " ", text)
        text = re.sub(r"\\[{].*?[}]", "", text)
        text = text.strip()

        if not text:
            continue

        segments.append(
            {
                "index": len(segments) + 1,
                "start": start_str,
                "end": end_str,
                "text": text,
                "start_seconds": _time_to_seconds_ass(start_str),
                "end_seconds": _time_to_seconds_ass(end_str),
                "duration": _time_to_seconds_ass(end_str) - _time_to_seconds_ass(start_str),
                "source": "ass",
                "generated": False,
            }
        )

    match_count = len(segments)
    logger.debug(f"Parsed {match_count} ASS segments")
    return segments


def parse_json3(content: str) -> list[dict[str, Any]]:
    """Parse YouTube JSON3 caption format.

    Args:
        content: Raw JSON3 content.

    Returns:
        List of segment dicts with word-level timing aggregated.
    """
    data = _json.loads(content)
    segments: list[dict[str, Any]] = []

    if "events" not in data:
        return segments

    for event in data["events"]:
        segs = event.get("segs", [])
        if not segs:
            continue

        first_seg = segs[0]
        start_ms = _parse_tv_rating(first_seg.get("tStartMs", 0))
        last_seg = segs[-1]
        end_ms = _parse_tv_rating(last_seg.get("tEndTimeMs", 0))

        text_parts = [s.get("utf8", "") for s in segs if s.get("utf8")]
        text = "".join(text_parts).strip()
        if not text:
            continue

        segments.append(
            {
                "index": len(segments) + 1,
                "start": f"{start_ms / 1000:.3f}",
                "end": f"{end_ms / 1000:.3f}",
                "text": text,
                "start_seconds": start_ms / 1000,
                "end_seconds": end_ms / 1000,
                "duration": (end_ms - start_ms) / 1000,
                "source": "json3",
                "generated": False,
            }
        )

    return segments


def _parse_tv_rating(ms_value: Any) -> float:
    """Parse a YouTube tv rating timestamp value."""
    try:
        return float(ms_value) if ms_value is not None else 0.0
    except (ValueError, TypeError):
        return 0.0


def _time_to_seconds(time_str: str) -> float:
    """Convert HH:MM:SS.mmm or MM:SS.mmm to seconds float."""
    parts = time_str.replace(",", ".").split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    else:
        try:
            return float(time_str)
        except ValueError:
            return 0.0


def _time_to_seconds_ass(time_str: str) -> float:
    """Convert ASS timestamp (H:MM:SS.cc) to seconds float."""
    parts = time_str.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    return 0.0


def load_captions_file(
    file_path: str | Path, format_hint: Optional[str] = None
) -> list[dict[str, Any]]:
    """Load and parse a caption/subtitle file.

    Args:
        file_path: Path to the subtitle file.
        format_hint: Optional format override.

    Returns:
        List of segment dicts.
    """
    path = Path(file_path)
    if not path.exists():
        return []

    ext = path.suffix.lower().lstrip(".")
    fmt = format_hint or ext

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        logger.warning(f"Failed to read {path}: {e}")
        return []

    parsers = {
        "srt": parse_srt,
        "vtt": parse_vtt,
        "ass": parse_ass,
        "ssa": parse_ass,
        "json": _parse_json_generic,
        "json3": parse_json3,
    }

    parser = parsers.get(fmt)
    if parser is None:
        logger.warning(f"Unknown caption format: {fmt}, trying SRT")
        return parse_srt(content)

    try:
        return parser(content)
    except Exception as e:
        logger.warning(f"Failed to parse {fmt} file {path}: {e}")
        return []


def _parse_json_generic(content: str) -> list[dict[str, Any]]:
    """Try to parse JSON caption file in common formats."""
    data = _json.loads(content)

    # YouTube JSON3 format
    if "events" in data:
        return parse_json3(content)

    # Generic segment-list format
    if "segments" in data and isinstance(data["segments"], list):
        return data["segments"]

    # List-of-objects format
    if isinstance(data, list):
        normalized: list[dict[str, Any]] = []
        for item in data:
            ns = float(item.get("start", item.get("startTime", 0)))
            ne = float(item.get("end", item.get("endTime", 0)))
            txt = item.get("text", item.get("content", item.get("caption", "")))

            normalized.append(
                {
                    "index": len(normalized) + 1,
                    "start": f"{ns:.3f}",
                    "end": f"{ne:.3f}",
                    "text": str(txt),
                    "start_seconds": ns,
                    "end_seconds": ne,
                    "duration": ne - ns,
                    "source": "json",
                    "generated": False,
                }
            )
        return normalized

    return []


# ---------------------------------------------------------------------------
# Merge transcripts
# ---------------------------------------------------------------------------


def merge_transcripts(
    primary: list[dict[str, Any]],
    secondary: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge two transcript lists, preferring primary timestamps.

    Args:
        primary: Primary transcript (higher priority).
        secondary: Secondary transcript (fallback for gaps).

    Returns:
        Merged transcript list.
    """
    if not primary:
        return list(secondary)

    if not secondary:
        return list(primary)

    merged: list[dict[str, Any]] = list(primary)

    # Build a time-indexed set from primary for quick lookup
    primary_times = {s["start_seconds"] for s in primary}

    for seg in secondary:
        t = seg["start_seconds"]
        if t not in primary_times:
            merged.append(dict(seg))

    return merged


# ---------------------------------------------------------------------------
# Whisper-based transcription
# ---------------------------------------------------------------------------


def transcribe_with_faster_whisper(
    audio_path: str | Path,
    model_size: str = "base",
    language: Optional[str] = None,
    task: str = "transcribe",
    device: str = "cpu",
    compute_type: str = "int8",
    verbose: bool = False,
) -> dict[str, Any]:
    """Transcribe audio using faster-whisper (CTranslate2) with quantization.

    Provides 4x-8x speedup and significantly lower RAM footprint compared to openai-whisper.

    Args:
        audio_path: Path to audio file.
        model_size: Whisper model size (tiny, base, small, medium, large).
        language: Language code (e.g., 'en', 'es'). Auto-detect if None.
        task: 'transcribe' or 'translate'.
        device: Device for inference ('cpu', 'cuda', 'auto').
        compute_type: Quantization compute type ('int8', 'int8_float16', 'float16', 'default').
        verbose: Verbose logging.

    Returns:
        dict with full_text, segments, language, language_probability,
        model, task, duration, duration_processed, engine.
    """
    from faster_whisper import WhisperModel  # type: ignore[import]

    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Determine quantization compute type for device
    if not compute_type or compute_type == "auto":
        compute_type = "int8" if device == "cpu" else "float16"
    elif device == "cpu" and compute_type in ("float16", "int8_float16"):
        logger.warning(
            f"Compute type '{compute_type}' is not supported on CPU. Auto-adjusting to 'int8'."
        )
        compute_type = "int8"

    logger.info(f"Loading faster-whisper model '{model_size}' on {device} ({compute_type})")
    model = WhisperModel(model_size, device=device, compute_type=compute_type)

    logger.info(f"Transcribing with faster-whisper: {audio_path}")

    import time as _time

    start = _time.time()
    segments_iter, info = model.transcribe(
        str(audio_path),
        language=language,
        task=task,
        beam_size=5,
    )

    segments: list[dict[str, Any]] = []
    for seg in segments_iter:
        segments.append(
            {
                "start": f"{seg.start:.3f}",
                "end": f"{seg.end:.3f}",
                "text": seg.text.strip(),
                "start_seconds": seg.start,
                "end_seconds": seg.end,
                "duration": seg.end - seg.start,
                "confidence": getattr(seg, "avg_logprob", None),
                "no_speech_prob": getattr(seg, "no_speech_prob", None),
                "source": "faster-whisper",
                "generated": True,
            }
        )

    elapsed = _time.time() - start
    full_text = " ".join(s["text"] for s in segments if s.get("text"))

    detected_lang = getattr(info, "language", None)
    lang_code = None
    if detected_lang and isinstance(detected_lang, str):
        if len(detected_lang.strip()) in (2, 3):
            lang_code = detected_lang.strip().lower()
        else:
            lang_code = detect_language_code(detected_lang)
    elif language:
        lang_code = language

    return {
        "full_text": full_text,
        "segments": segments,
        "language": lang_code,
        "language_probability": getattr(info, "language_probability", None),
        "model": model_size,
        "task": task,
        "duration": getattr(info, "duration", 0),
        "duration_processed": elapsed,
        "engine": "faster-whisper",
    }


def transcribe_with_whisper(
    audio_path: str | Path,
    model_size: str = "tiny",
    language: Optional[str] = None,
    task: str = "transcribe",
    verbose: bool = False,
    engine: str = "auto",
    device: str = "cpu",
    compute_type: str = "int8",
    fallback_enabled: bool = True,
) -> dict[str, Any]:
    """Transcribe audio using faster-whisper or openai-whisper with transparent fallback.

    Args:
        audio_path: Path to audio file.
        model_size: Whisper model size (tiny, base, small, medium, large).
        language: Language code (e.g., 'en', 'es'). Auto-detect if None.
        task: 'transcribe' or 'translate'.
        verbose: Print verbose progress.
        engine: 'auto', 'faster-whisper', or 'whisper'.
        device: 'cpu', 'cuda', etc.
        compute_type: 'int8', 'float16', etc.
        fallback_enabled: Allow fallback if primary engine fails.

    Returns:
        dict with full_text, segments, language, language_probability,
        model, task, duration, duration_processed, engine.
    """
    normalized_engine = (engine or "auto").lower().replace("_", "-")

    if normalized_engine in ("auto", "faster-whisper"):
        try:
            return transcribe_with_faster_whisper(
                audio_path=audio_path,
                model_size=model_size,
                language=language,
                task=task,
                device=device,
                compute_type=compute_type,
                verbose=verbose,
            )
        except Exception as e:
            if normalized_engine == "faster-whisper" and not fallback_enabled:
                raise
            logger.info(
                f"faster-whisper unavailable or encountered error ({e}); falling back to openai-whisper"
            )

    from whisper import load_model, transcribe  # type: ignore[import]

    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    logger.info(f"Loading Whisper model: {model_size}")
    model = load_model(model_size)

    logger.info(f"Transcribing: {audio_path}")

    import time as _time

    start = _time.time()

    result = transcribe(
        model,
        str(audio_path),
        language=language,
        task=task,
        verbose=verbose,
        word_timestamps=False,
        temperature=0.0,
        condition_on_previous_text=True,
    )

    elapsed = _time.time() - start

    segments: list[dict[str, Any]] = []
    for seg in result.get("segments", []):
        segments.append(
            {
                "start": f"{seg['start']:.3f}",
                "end": f"{seg['end']:.3f}",
                "text": seg.get("text", "").strip(),
                "start_seconds": seg["start"],
                "end_seconds": seg["end"],
                "duration": seg["end"] - seg["start"],
                "confidence": seg.get("avg_logprob", None),
                "no_speech_prob": seg.get("no_speech_prob", None),
                "source": "whisper",
                "generated": True,
            }
        )

    full_text = " ".join(s["text"] for s in segments if s.get("text"))

    # Language detection
    detected_lang = result.get("language", "")
    lang_code = None
    if detected_lang and isinstance(detected_lang, str):
        if len(detected_lang.strip()) in (2, 3):
            lang_code = detected_lang.strip().lower()
        else:
            lang_code = detect_language_code(detected_lang)
    elif language:
        lang_code = language

    return {
        "full_text": full_text,
        "segments": segments,
        "language": lang_code,
        "language_probability": result.get("language_probability", None),
        "model": model_size,
        "task": task,
        "duration": result.get("duration", 0),
        "duration_processed": elapsed,
        "engine": "whisper",
    }


# ---------------------------------------------------------------------------
# Transcriber class
# ---------------------------------------------------------------------------


class Transcriber:
    """Orchestrates transcription using multiple strategies."""

    def __init__(
        self,
        config: Optional[dict[str, Any]] = None,
    ):
        self.config = config or {}
        self.strategy_order: list[str] = self.config.get(
            "strategy_order",
            [
                "platform_captions",
                "local_captions",
                "whisper",
            ],
        )
        self.language: Optional[str] = self.config.get("language")
        self.engine: str = self.config.get("engine", self.config.get("local_engine", "auto"))
        self.local_engine: str = self.engine
        self.compute_type: str = self.config.get("compute_type", "int8")
        self.model: str = self.config.get("whisper_model", self.config.get("model", "base"))
        self.fallback_enabled: bool = self.config.get("fallback_enabled", True)
        self.device: str = self.config.get("device", "cpu")
        self._whisper_model_cache: dict[str, Any] = {}

    def transcribe(
        self,
        source: str,
        local_audio_path: Optional[str] = None,
        captions: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """Transcribe a video source using configured strategies.

        Args:
            source: URL or file path.
            local_audio_path: Optional pre-downloaded audio file path.
            captions: Optional pre-parsed caption segments.

        Returns:
            Full transcription result dict.
        """
        result: dict[str, Any] = {
            "source": source,
            "strategies_attempted": [],
            "strategies_succeeded": [],
            "primary_text": "",
            "segments": [],
            "language": None,
            "language_probability": None,
            "model": None,
            "duration": 0,
            "warnings": [],
        }

        # Strategy 1: Platform captions
        if "platform_captions" in self.strategy_order:
            try:
                cap_result = self._try_platform_captions(source)
                if cap_result and cap_result.get("segments"):
                    result["strategies_succeeded"].append("platform_captions")
                    result["segments"] = cap_result["segments"]
                    result["primary_text"] = cap_result["full_text"]
                    result["language"] = cap_result.get("language")
                    result["language_probability"] = cap_result.get("language_probability")
                    return self._finalize_result(result)
            except Exception as e:
                logger.debug(f"Platform captions failed: {e}")
                result["warnings"].append(f"Platform captions failed: {e}")

        # Strategy 2: Local captions
        if "local_captions" in self.strategy_order and captions:
            try:
                if captions:
                    result["strategies_succeeded"].append("local_captions")
                    result["segments"] = captions
                    result["primary_text"] = " ".join(s["text"] for s in captions if s.get("text"))
                    return self._finalize_result(result)
            except Exception as e:
                logger.debug(f"Local captions failed: {e}")

        # Strategy 3: Whisper
        if "whisper" in self.strategy_order:
            audio_path = local_audio_path
            if not audio_path:
                audio_path = self._download_audio(source)

            if audio_path:
                try:
                    whisper_result = self._try_whisper(audio_path)
                    if whisper_result and whisper_result.get("segments"):
                        result["strategies_succeeded"].append("whisper")
                        result["segments"] = whisper_result["segments"]
                        result["primary_text"] = whisper_result["full_text"]
                        result["language"] = whisper_result.get("language")
                        result["language_probability"] = whisper_result.get("language_probability")
                        result["model"] = whisper_result.get("model")
                        result["duration"] = whisper_result.get("duration", 0)
                        return self._finalize_result(result)
                except Exception as e:
                    logger.debug(f"Whisper transcription failed: {e}")
                    result["warnings"].append(f"Whisper failed: {e}")

        return self._finalize_result(result)

    def _try_platform_captions(self, url: str) -> Optional[dict[str, Any]]:
        """Try to get captions from YouTube/Facebook/Instagram/TikTok in <1s (Zero-GPU)."""
        auth = self.config.get("auth")
        return extract_fast_native_subtitles(url, language=self.language, auth=auth)

    def _try_whisper(self, audio_path: str) -> Optional[dict[str, Any]]:
        """Run Whisper transcription on audio file."""
        try:
            result = transcribe_with_whisper(
                audio_path,
                model_size=self.model,
                language=self.language,
                task="transcribe",
                verbose=False,
                engine=self.engine,
                device=self.device,
                compute_type=self.compute_type,
                fallback_enabled=self.fallback_enabled,
            )
            if result and result.get("segments"):
                return result
        except Exception as e:
            logger.debug(f"Whisper transcription failed: {e}")
            return None
        return None

    def _download_audio(self, source: str) -> Optional[str]:
        """Download audio from source for transcription."""
        import yt_dlp  # type: ignore[import]

        try:
            tmp = Path(tempfile.mktemp(suffix=".wav"))
            ydl_opts: dict[str, Any] = {
                "format": "bestaudio/best",
                "outtmpl": str(tmp),
                "quiet": True,
                "no_warnings": True,
                "extractaudio": True,
                "audioformat": "wav",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "wav",
                        "preferredquality": "192",
                    }
                ],
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([source])
            if tmp.exists():
                return str(tmp)
        except Exception as e:
            logger.debug(f"Audio download failed: {e}")
        return None

    def _finalize_result(self, result: dict[str, Any]) -> dict[str, Any]:
        """Finalize transcription result."""
        seen: set[float] = set()
        unique: list[dict[str, Any]] = []
        for seg in result.get("segments", []):
            t = seg.get("start_seconds", 0)
            if t not in seen:
                seen.add(t)
                unique.append(seg)
        result["segments"] = unique
        result["primary_text"] = " ".join(s["text"] for s in unique if s.get("text"))
        return result


def format_seconds_to_timestamp(seconds: float) -> str:
    """Format seconds into HH:MM:SS or MM:SS."""
    if seconds < 0:
        seconds = 0.0
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def clean_and_deduplicate_segments(
    segments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Clean HTML/VTT markup and deduplicate consecutive identical or rolling cues.

    Eliminates rolling-buffer duplicates common in YouTube auto-generated captions,
    strips residual markup, unescapes HTML entities, and ensures clean segment boundaries.
    """
    cleaned: list[dict[str, Any]] = []
    prev_text = ""

    for seg in segments:
        raw_text = seg.get("text", "")
        # Decode HTML entities like &amp;, &#39;, &quot;, &lt;, &gt;
        text = html.unescape(raw_text)
        # Remove VTT / HTML tags like <c>, </c>, <00:00:01.000>
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            continue

        s_sec = seg.get("start_seconds")
        e_sec = seg.get("end_seconds")

        # If identical to previous, merge / extend duration
        if cleaned and text == prev_text:
            if "end" in seg:
                cleaned[-1]["end"] = seg["end"]
            if e_sec is not None:
                cleaned[-1]["end_seconds"] = e_sec
                prev_s = cleaned[-1].get("start_seconds")
                if prev_s is not None:
                    cleaned[-1]["duration"] = e_sec - prev_s
            continue

        # If previous text is a strict prefix of current text (rolling auto-captions)
        # and start times are close (< 2.5s), replace with the full sentence
        prev_s = cleaned[-1].get("start_seconds") if cleaned else None
        time_diff = (s_sec - prev_s) if (s_sec is not None and prev_s is not None) else 0.0

        if cleaned and prev_text and text.startswith(prev_text) and 0 <= time_diff < 2.5:
            cleaned[-1]["text"] = text
            if "end" in seg:
                cleaned[-1]["end"] = seg["end"]
            if e_sec is not None:
                cleaned[-1]["end_seconds"] = e_sec
                if prev_s is not None:
                    cleaned[-1]["duration"] = e_sec - prev_s
            prev_text = text
            continue

        new_seg = dict(seg)
        new_seg["text"] = text
        cleaned.append(new_seg)
        prev_text = text

    return cleaned


def format_subtitles_to_markdown(
    segments: list[dict[str, Any]],
    source_info: Optional[dict[str, Any]] = None,
    output_path: Optional[str | Path] = None,
) -> str:
    """Format subtitle segments to clean Markdown with timestamps."""
    lines: list[str] = ["# Transcripción", ""]
    if source_info:
        title = source_info.get("title") or source_info.get("url") or "Vídeo"
        lines.append(f"**Fuente:** {title}")
        if source_info.get("uploader"):
            lines.append(f"**Canal:** {source_info['uploader']}")
        if source_info.get("duration"):
            mins, secs = divmod(int(source_info["duration"]), 60)
            lines.append(f"**Duración:** {mins}:{secs:02d}")
        if source_info.get("language"):
            lines.append(f"**Idioma:** {source_info['language']}")
        if source_info.get("sub_type"):
            lines.append(f"**Tipo:** {source_info['sub_type']}")
        lines.append(f"**Segmentos:** {len(segments)}")
        lines.append("")

    lines.append("---")
    lines.append("")

    for seg in segments:
        text = seg.get("text", "").strip()
        if not text:
            continue
        s_sec = seg.get("start_seconds")
        e_sec = seg.get("end_seconds")
        if s_sec is not None and e_sec is not None:
            ts_str = (
                f"**[{format_seconds_to_timestamp(s_sec)} → {format_seconds_to_timestamp(e_sec)}]**"
            )
        else:
            s_str = str(seg.get("start", "")).split(".")[0]
            e_str = str(seg.get("end", "")).split(".")[0]
            ts_str = f"**[{s_str} → {e_str}]**"
        lines.append(f"{ts_str} {text}")
        lines.append("")

    content = "\n".join(lines)
    if output_path:
        Path(output_path).write_text(content, encoding="utf-8")
    return content


def _pick_best_format(track_formats: list[dict[str, Any]]) -> dict[str, Any]:
    """Select the best format dictionary from a track's available formats list."""
    if not track_formats:
        return {}
    # Prioritize vtt, then srt, then json3 over internal raw xml formats (srv1, srv2, ttml)
    for target_ext in ("vtt", "srt", "json3"):
        for fmt in track_formats:
            if fmt.get("ext") == target_ext and fmt.get("url"):
                return fmt
    # Second pass: any format with a url
    for fmt in track_formats:
        if fmt.get("url"):
            return fmt
    return track_formats[0]


def _select_best_subtitle_track(
    captions: dict[str, list[dict[str, Any]]],
    automatic_captions: dict[str, list[dict[str, Any]]],
    preferred_lang: Optional[str] = "es",
) -> Optional[tuple[str, dict[str, Any], bool]]:
    """Select the single best subtitle track based on language preference.

    Returns:
        (language_code, subtitle_entry, is_automatic) or None
    """
    pref = (preferred_lang or "es").lower().split("-")[0].split("_")[0]

    def matches_pref(lang_key: str) -> bool:
        norm = lang_key.lower().split("-")[0].split("_")[0]
        return norm == pref

    # 1. Manual/official captions in preferred language
    if captions:
        for lang, sub_list in captions.items():
            if matches_pref(lang) and sub_list:
                return (lang, _pick_best_format(sub_list), False)

    # 2. Automatic captions in preferred language
    if automatic_captions:
        for lang, sub_list in automatic_captions.items():
            if matches_pref(lang) and sub_list:
                return (lang, _pick_best_format(sub_list), True)

    # 3. Manual/official captions in English
    if captions and pref != "en":
        for lang, sub_list in captions.items():
            if matches_pref("en") and sub_list:
                return (lang, _pick_best_format(sub_list), False)

    # 4. Automatic captions in English
    if automatic_captions and pref != "en":
        for lang, sub_list in automatic_captions.items():
            if matches_pref("en") and sub_list:
                return (lang, _pick_best_format(sub_list), True)

    # 5. First available manual caption
    if captions:
        for lang, sub_list in captions.items():
            if sub_list:
                return (lang, _pick_best_format(sub_list), False)

    # 6. First available automatic caption
    if automatic_captions:
        for lang, sub_list in automatic_captions.items():
            if sub_list:
                return (lang, _pick_best_format(sub_list), True)

    return None


def extract_fast_native_subtitles(
    source: str | Path,
    language: Optional[str] = "es",
    auth: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    """Extract native subtitles in <1 second (Zero-GPU strategy).

    Inspects native subtitles (official or automatic) from platforms (YouTube, Facebook, etc.)
    or local adjacent/embedded subtitle files without running heavy audio transcription models.

    Returns:
        dict with segments, full_text, markdown, language, source, is_auto, strategy.
    """
    source_str = str(source)
    is_remote = source_str.startswith("http://") or source_str.startswith("https://")

    if not is_remote:
        segments = extract_local_captions(source)
        if segments:
            segments = clean_and_deduplicate_segments(segments)
            full_text = " ".join(s["text"] for s in segments if s.get("text"))
            md = format_subtitles_to_markdown(
                segments,
                source_info={
                    "title": Path(source_str).name,
                    "language": language or "es",
                    "sub_type": "Subtítulos locales (Zero-GPU)",
                },
            )
            return {
                "segments": segments,
                "full_text": full_text,
                "markdown": md,
                "language": language or "es",
                "source": source_str,
                "is_auto": False,
                "strategy": "native_subtitles_zero_gpu",
            }
        return None

    import yt_dlp  # type: ignore[import]

    ydl_opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    if auth:
        browser = str(auth.get("cookies_from_browser") or "").strip()
        cookies_path = str(auth.get("cookies_path") or "").strip()
        if browser:
            ydl_opts["cookiesfrombrowser"] = (browser, None, None, None)
        elif cookies_path and Path(cookies_path).expanduser().exists():
            ydl_opts["cookiefile"] = str(Path(cookies_path).expanduser())

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(source_str, download=False)
    except Exception as e:
        logger.debug(f"Fast subtitle extraction failed on yt-dlp metadata: {e}")
        return None

    selected = _select_best_subtitle_track(
        info.get("subtitles") or info.get("captions") or {},
        info.get("automatic_captions") or {},
        preferred_lang=language,
    )
    if not selected:
        return None

    matched_lang, track_info, is_auto = selected
    url = track_info.get("url")
    if not url:
        return None

    content = None
    try:
        # 1. Prefer ydl.urlopen which carries authenticated cookies and session headers
        with yt_dlp.YoutubeDL(ydl_opts) as ydl_fetch:
            if hasattr(ydl_fetch, "urlopen"):
                resp = ydl_fetch.urlopen(url)
                if hasattr(resp, "read"):
                    raw = resp.read()
                    if isinstance(raw, bytes):
                        content = raw.decode("utf-8", errors="replace")
    except Exception as e:
        logger.debug(f"ydl.urlopen failed ({e}), trying urllib fallback")

    if not content:
        try:
            import urllib.request

            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                content = resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            logger.debug(f"Failed to fetch subtitle content from {url}: {e}")
            return None

    try:
        segments = _parse_subtitle_content(content, matched_lang, is_auto)
        if segments:
            segments = clean_and_deduplicate_segments(segments)
            full_text = " ".join(s["text"] for s in segments if s.get("text"))
            md = format_subtitles_to_markdown(
                segments,
                source_info={
                    "title": info.get("title", source_str),
                    "url": source_str,
                    "language": matched_lang,
                    "sub_type": "Subtítulos automáticos (Zero-GPU)"
                    if is_auto
                    else "Subtítulos oficiales (Zero-GPU)",
                },
            )
            return {
                "segments": segments,
                "full_text": full_text,
                "markdown": md,
                "language": matched_lang,
                "source": source_str,
                "is_auto": is_auto,
                "strategy": "native_subtitles_zero_gpu",
            }
    except Exception as e:
        logger.debug(f"Failed to parse subtitle content from {url}: {e}")

    return None


def parse_srv_xml(content: str) -> list[dict[str, Any]]:
    """Parse YouTube srv1/srv2/srv3 XML subtitle content into structured segments."""
    segments: list[dict[str, Any]] = []
    pattern = re.compile(
        r'<text\s+[^>]*start="([^"]+)"(?:[^>]*dur="([^"]+)")?[^>]*>(.*?)</text>',
        re.DOTALL | re.IGNORECASE,
    )
    for match in pattern.finditer(content):
        try:
            start_sec = float(match.group(1))
            dur_sec = float(match.group(2)) if match.group(2) else 2.0
        except (ValueError, TypeError):
            continue
        end_sec = start_sec + dur_sec
        raw_text = match.group(3)
        clean_text = re.sub(r"<[^>]+>", "", raw_text)
        clean_text = html.unescape(clean_text).strip()
        if not clean_text:
            continue
        segments.append(
            {
                "index": len(segments) + 1,
                "start": f"{start_sec:.3f}",
                "end": f"{end_sec:.3f}",
                "text": clean_text,
                "start_seconds": start_sec,
                "end_seconds": end_sec,
                "duration": dur_sec,
                "source": "srv_xml",
                "generated": False,
            }
        )
    return segments


def _parse_subtitle_content(content: str, lang: str, is_auto: bool) -> list[dict[str, Any]]:
    """Parse downloaded subtitle content."""
    if content.startswith("WEBVTT") or "-->" in content:
        if content.startswith("WEBVTT") or not re.search(
            r"^\d+\s*\n\d{2}:\d{2}", content, re.MULTILINE
        ):
            segments = parse_vtt(content)
        else:
            segments = parse_srt(content)
    elif re.search(r"^\d+\s*\n\d{2}:\d{2}:\d{2}", content, re.MULTILINE):
        segments = parse_srt(content)
    elif "Dialogue:" in content:
        segments = parse_ass(content)
    elif "<transcript" in content or "<text start=" in content:
        segments = parse_srv_xml(content)
    else:
        try:
            segments = parse_json3(content)
        except Exception:
            segments = []

    for s in segments:
        s["source"] = "auto_captions" if is_auto else "manual_captions"
        s.setdefault("language", lang)
    return segments


# ---------------------------------------------------------------------------
# Export functions
# ---------------------------------------------------------------------------


def export_transcript_markdown(
    segments: list[dict[str, Any]],
    source_info: Optional[dict[str, Any]] = None,
    output_path: Optional[str] = None,
) -> str:
    """Export transcript segments to Markdown."""
    return format_subtitles_to_markdown(
        segments=segments,
        source_info=source_info,
        output_path=output_path,
    )


def export_transcript_json(
    segments: list[dict[str, Any]],
    source_info: Optional[dict[str, Any]] = None,
    output_path: Optional[str] = None,
) -> str:
    """Export transcript to JSON."""
    data: dict[str, Any] = {
        "segments": segments,
        "total_segments": len(segments),
    }
    if source_info:
        data["source"] = source_info

    json_str = _json.dumps(data, ensure_ascii=False, indent=2)
    if output_path:
        Path(output_path).write_text(json_str, encoding="utf-8")
    return json_str


def export_srt(segments: list[dict[str, Any]], output_path: str) -> str:
    """Export segments to SRT format."""
    lines: list[str] = []
    for i, seg in enumerate(segments, 1):
        start = seg.get("start", "00:00:00.000")
        end = seg.get("end", "00:00:00.000")
        text = seg.get("text", "")
        lines.append(f"{i}")
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")

    content = "\n".join(lines)
    Path(output_path).write_text(content, encoding="utf-8")
    return content


def export_vtt(segments: list[dict[str, Any]], output_path: str) -> str:
    """Export segments to VTT format."""
    lines: list[str] = ["WEBVTT", ""]
    for i, seg in enumerate(segments, 1):
        start = seg.get("start", "00:00:00.000")
        end = seg.get("end", "00:00:00.000")
        text = seg.get("text", "")
        lines.append(f"{i}")
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")

    content = "\n".join(lines)
    Path(output_path).write_text(content, encoding="utf-8")
    return content


# ---------------------------------------------------------------------------
# Detection of available transcription methods
# ---------------------------------------------------------------------------


def detect_available_transcribers() -> dict[str, Any]:
    """Detect which transcription methods are available."""
    result: dict[str, Any] = {
        "faster_whisper_installed": False,
        "faster_whisper_version": None,
        "whisper_installed": False,
        "whisper_version": None,
        "yt_dlp_installed": False,
        "ffmpeg_available": False,
        "tesseract_available": False,
        "scenedetect_available": False,
    }

    try:
        import faster_whisper as _fw

        result["faster_whisper_installed"] = True
        result["faster_whisper_version"] = getattr(_fw, "__version__", "unknown")
    except ImportError:
        pass

    try:
        import whisper as _whisper  # type: ignore[import]

        result["whisper_installed"] = True
        result["whisper_version"] = getattr(_whisper, "__version__", "unknown")
    except ImportError:
        pass

    try:
        import yt_dlp as _yt_dlp  # type: ignore[import]

        result["yt_dlp_installed"] = True
    except ImportError:
        pass

    import shutil

    result["ffmpeg_available"] = shutil.which("ffmpeg") is not None
    result["tesseract_available"] = shutil.which("tesseract") is not None
    result["scenedetect_available"] = shutil.which("scenedetect") is not None

    return result


# ----------------------------------------------------------------------
# Contract API wrapper functions
# ----------------------------------------------------------------------


def transcribe_from_url(
    url: str,
    strategy: str = "auto",
    language: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> dict[str, Any]:
    """Transcribe a video from URL (contract API).

    Args:
        url: Video URL to transcribe.
        strategy: Transcription strategy ('auto', 'whisper', 'captions').
        language: Language code for transcription.
        user_agent: User agent string for HTTP requests.

    Returns:
        Dict with transcription results including segments, language, etc.
    """
    transcriber = Transcriber(
        config={
            "strategy_order": ["platform_captions", "local_captions", "whisper"],
            "language": language,
        }
    )
    return transcriber.transcribe(url)


def transcribe_from_file(
    video_path: str | Path,
    strategy: str = "auto",
    language: Optional[str] = None,
) -> dict[str, Any]:
    """Transcribe a local video file (contract API).

    Args:
        video_path: Path to local video file.
        strategy: Transcription strategy ('auto', 'whisper', 'captions').
        language: Language code for transcription.

    Returns:
        Dict with transcription results including segments, language, etc.
    """
    transcriber = Transcriber(
        config={
            "strategy_order": ["local_captions", "whisper"],
            "language": language,
        }
    )
    # For local files, we need to download audio first if using whisper
    return transcriber.transcribe(str(video_path))


def detect_subtitles(url: str) -> list[dict[str, Any]]:
    """Detect available subtitle tracks for a video URL (contract API).

    Args:
        url: Video URL to check for subtitles.

    Returns:
        List of subtitle track info dicts.
    """
    import yt_dlp

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }

    tracks: list[dict[str, Any]] = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception:
        return tracks

    # Check automatic captions
    if info.get("automatic_captions"):
        for lang, sub_list in info["automatic_captions"].items():
            for sub in sub_list:
                tracks.append(
                    {
                        "language": lang,
                        "format": sub.get("ext", ""),
                        "url": sub.get("url", ""),
                        "is_auto": True,
                    }
                )

    # Check manual captions
    if info.get("captions"):
        for lang, sub_list in info["captions"].items():
            for sub in sub_list:
                tracks.append(
                    {
                        "language": lang,
                        "format": sub.get("ext", ""),
                        "url": sub.get("url", ""),
                        "is_auto": False,
                    }
                )

    return tracks


def download_subtitles(
    url: str,
    track_id: str,
    output_dir: str | Path,
) -> Path:
    """Download a subtitle track for a video URL (contract API).

    Args:
        url: Video URL.
        track_id: Identifier for the subtitle track.
        output_dir: Directory to save the subtitle file.

    Returns:
        Path to downloaded subtitle file.
    """
    import yt_dlp

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitlesformat": "srt",
        "outtmpl": str(output_dir / "%(title)s.%(ext)s"),
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        raise RuntimeError(f"Failed to download subtitles: {e}")

    # Find the downloaded file
    srt_files = list(output_dir.glob("*.srt"))
    if srt_files:
        return srt_files[0]

    raise RuntimeError("No subtitle file was downloaded")


# Alias for backward compatibility with tests
transcribe_video = transcribe_from_file


# ---------------------------------------------------------------------------
# Additional Contract API functions (for test compatibility)
# ---------------------------------------------------------------------------


from dataclasses import dataclass, field
from typing import Any


@dataclass
class TranscriptionResult:
    """Transcription result (contract API)."""

    text: str = ""
    language: str = ""
    segments: list = field(default_factory=list)
    confidence: float = 0.0
    source: str = ""
    error: str | None = None

    def __post_init__(self):
        if self.segments is None:
            self.segments = []


def extract_captions_from_platform(url: str) -> list[dict[str, Any]]:
    """Extract platform captions from a video URL (contract API).

    Args:
        url: Video URL.

    Returns:
        List of caption tracks or extracted segments.
    """
    fast = extract_fast_native_subtitles(url)
    if fast and fast.get("segments"):
        return fast["segments"]
    return detect_subtitles(url)


def extract_local_captions(video_path: str | Path) -> list[dict[str, Any]]:
    """Extract local captions from adjacent files or embedded subtitle streams (contract API).

    Args:
        video_path: Path to local video file.

    Returns:
        List of caption segments.
    """
    video_path = Path(video_path)
    if not video_path.exists():
        return []

    # 1. Check adjacent subtitle files
    for ext in [".srt", ".vtt", ".sub", ".es.srt", ".es.vtt", ".en.srt", ".en.vtt"]:
        cand = video_path.with_suffix(ext)
        if cand.exists():
            try:
                content = cand.read_text(encoding="utf-8", errors="replace")
                segments = _parse_subtitle_content(content, "auto", is_auto=False)
                if segments:
                    return clean_and_deduplicate_segments(segments)
            except Exception as e:
                logger.debug(f"Error reading adjacent subtitle {cand}: {e}")

    # 2. Check embedded streams via ffmpeg
    try:
        tmp_srt = Path(tempfile.mktemp(suffix=".srt"))
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-map",
            "0:s:0",
            str(tmp_srt),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if res.returncode == 0 and tmp_srt.exists() and tmp_srt.stat().st_size > 0:
            content = tmp_srt.read_text(encoding="utf-8", errors="replace")
            tmp_srt.unlink(missing_ok=True)
            segments = parse_srt(content)
            if segments:
                return clean_and_deduplicate_segments(segments)
        tmp_srt.unlink(missing_ok=True)
    except Exception as e:
        logger.debug(f"Error extracting embedded subtitle stream: {e}")

    return []


def load_faster_whisper_model(
    model_size: str = "base",
    device: str = "cpu",
    compute_type: str = "int8",
) -> Any:
    """Load a faster-whisper model."""
    try:
        from faster_whisper import WhisperModel

        if device == "cpu" and compute_type in ("float16", "int8_float16"):
            compute_type = "int8"

        return WhisperModel(model_size, device=device, compute_type=compute_type)
    except Exception as e:
        logger.debug(f"Failed to load faster-whisper model: {e}")
        return None


def load_whisper_model(model_size: str = "base", device: str = "auto") -> Any:
    """Load a Whisper model (contract API).

    Args:
        model_size: Model size (tiny, base, small, medium, large).
        device: Device to load on (cpu, cuda, auto).

    Returns:
        Loaded Whisper model or None if not available.
    """
    try:
        import whisper

        return whisper.load_model(model_size, device=device)
    except ImportError:
        return None


class WhisperTranscriptionStrategy:
    """Whisper transcription strategy (contract API)."""

    def __init__(self, model_size: str = "base", language: str | None = None):
        self.model_size = model_size
        self.language = language
        self._model = None

    def _get_model(self):
        if self._model is None:
            self._model = load_whisper_model(self.model_size)
        return self._model

    def transcribe(self, audio_path: str) -> TranscriptionResult:
        """Transcribe audio file using Whisper."""
        model = self._get_model()
        if model is None:
            return TranscriptionResult(
                text="",
                error="Whisper not available",
            )

        result = model.transcribe(audio_path, language=self.language)
        return TranscriptionResult(
            text=result.get("text", ""),
            language=result.get("language", ""),
            segments=result.get("segments", []),
            confidence=1.0,
            source=audio_path,
        )
