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
    # SRT format: index, timestamp line, text lines, blank line
    pattern = re.compile(
        r"^(\d+)\s*\n"
        r"(\d{2}:\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[.,]\d{3})"
        r"(?:\s*\n)?"
        r"((?:.*\n?)*)"
        r"(?=\n\n|\n\d+\s*\n|$)",
        re.MULTILINE,
    )

    for match in pattern.finditer(content):
        index = int(match.group(1))
        start_str = match.group(2).strip().replace(",", ".")
        end_str = match.group(3).strip().replace(",", ".")
        text = match.group(4).strip()
        text = text.replace("\r\n", "\n").replace("\r", "\n").strip()

        if not text:
            continue

        segments.append({
            "index": index,
            "start": start_str,
            "end": end_str,
            "text": text,
            "start_seconds": _time_to_seconds(start_str),
            "end_seconds": _time_to_seconds(end_str),
            "duration": _time_to_seconds(end_str) - _time_to_seconds(start_str),
            "source": "srt",
            "generated": False,
        })

    return segments


def parse_vtt(content: str) -> list[dict[str, Any]]:
    """Parse VTT (WebVTT) subtitle content.

    Args:
        content: Raw VTT content.

    Returns:
        List of segment dicts.
    """
    # Strip WEBVTT header
    idx = content.find("\n\n")
    if idx >= 0:
        content = content[idx + 2:]

    segments: list[dict[str, Any]] = []
    pattern = re.compile(
        r"^(\d{2}:\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[.,]\d{3})"
        r"(?:\s*[^\n]*)?\n"
        r"((?:.*\n?)*)"
        r"(?=\n\n|\n\d{2}:\d{2}:\d{2}|$)",
        re.MULTILINE,
    )

    index = 0
    for match in pattern.finditer(content):
        index += 1
        start_str = match.group(1).strip().replace(",", ".")
        end_str = match.group(2).strip().replace(",", ".")
        text = match.group(3).strip()
        text = text.replace("\r\n", "\n").replace("\r", "\n").strip()

        if not text:
            continue

        segments.append({
            "index": index,
            "start": start_str,
            "end": end_str,
            "text": text,
            "start_seconds": _time_to_seconds(start_str),
            "end_seconds": _time_to_seconds(end_str),
            "duration": _time_to_seconds(end_str) - _time_to_seconds(start_str),
            "source": "vtt",
            "generated": False,
        })

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

        segments.append({
            "index": len(segments) + 1,
            "start": start_str,
            "end": end_str,
            "text": text,
            "start_seconds": _time_to_seconds_ass(start_str),
            "end_seconds": _time_to_seconds_ass(end_str),
            "duration": _time_to_seconds_ass(end_str) - _time_to_seconds_ass(start_str),
            "source": "ass",
            "generated": False,
        })

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

        segments.append({
            "index": len(segments) + 1,
            "start": f"{start_ms / 1000:.3f}",
            "end": f"{end_ms / 1000:.3f}",
            "text": text,
            "start_seconds": start_ms / 1000,
            "end_seconds": end_ms / 1000,
            "duration": (end_ms - start_ms) / 1000,
            "source": "json3",
            "generated": False,
        })

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


def load_captions_file(file_path: str | Path, format_hint: Optional[str] = None) -> list[dict[str, Any]]:
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

            normalized.append({
                "index": len(normalized) + 1,
                "start": f"{ns:.3f}",
                "end": f"{ne:.3f}",
                "text": str(txt),
                "start_seconds": ns,
                "end_seconds": ne,
                "duration": ne - ns,
                "source": "json",
                "generated": False,
            })
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

def transcribe_with_whisper(
    audio_path: str | Path,
    model_size: str = "tiny",
    language: Optional[str] = None,
    task: str = "transcribe",
    verbose: bool = False,
) -> dict[str, Any]:
    """Transcribe audio using openai-whisper.

    Args:
        audio_path: Path to audio file.
        model_size: Whisper model size (tiny, base, small, medium, large).
        language: Language code (e.g., 'en', 'es'). Auto-detect if None.
        task: 'transcribe' or 'translate'.
        verbose: Print verbose progress.

    Returns:
        dict with full_text, segments, language, language_probability,
        model, task, duration, duration_processed.
    """
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
        audio_path,
        model=model,
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
        segments.append({
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
        })

    full_text = " ".join(s["text"] for s in segments if s.get("text"))

    # Language detection
    detected_lang = result.get("language", "")
    lang_code = None
    if detected_lang and isinstance(detected_lang, str):
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
        self.strategy_order: list[str] = self.config.get("strategy_order", [
            "platform_captions",
            "local_captions",
            "whisper",
        ])
        self.language: Optional[str] = self.config.get("language")
        self.local_engine: str = self.config.get("local_engine", "whisper")
        self.model: str = self.config.get("model", "tiny")
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
                    result["primary_text"] = " ".join(
                        s["text"] for s in captions if s.get("text")
                    )
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
        """Try to get captions from YouTube/Facebook/Instagram/TikTok."""
        import yt_dlp  # type: ignore[import]

        ydl_opts: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception:
            return None

        all_segments: list[dict[str, Any]] = []
        detected_lang: Optional[str] = None

        # Try automatic captions first, then manual
        caption_sources = []

        if info.get("automatic_captions"):
            for lang, sub_list in info["automatic_captions"].items():
                caption_sources.append((lang, sub_list, True))
        if info.get("captions"):
            for lang, sub_list in info["captions"].items():
                caption_sources.append((lang, sub_list, False))

        for lang, sub_list, is_auto in caption_sources:
            for sub in sub_list:
                try:
                    import urllib.request

                    with urllib.request.urlopen(sub["url"]) as resp:
                        content = resp.read().decode("utf-8", errors="replace")
                    segments = _parse_subtitle_content(content, lang, is_auto)
                    if segments:
                        all_segments.extend(segments)
                        if not detected_lang:
                            detected_lang = lang
                except Exception:
                    continue

        if all_segments:
            full_text = " ".join(s["text"] for s in all_segments if s.get("text"))
            return {
                "segments": all_segments,
                "full_text": full_text,
                "language": detected_lang,
                "language_probability": None,
                "source": url,
            }

        return None

    def _try_whisper(self, audio_path: str) -> Optional[dict[str, Any]]:
        """Run Whisper transcription on audio file."""
        try:
            result = transcribe_with_whisper(
                audio_path,
                model_size=self.model,
                language=self.language,
                task="transcribe",
                verbose=False,
            )
            if result.get("segments"):
                return result
        except Exception:
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
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "wav",
                    "preferredquality": "192",
                }],
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
        result["primary_text"] = " ".join(
            s["text"] for s in unique if s.get("text")
        )
        return result


def _parse_subtitle_content(
    content: str, lang: str, is_auto: bool
) -> list[dict[str, Any]]:
    """Parse downloaded subtitle content."""
    if content.startswith("WEBVTT"):
        return parse_vtt(content)
    elif re.search(r"^\d+\s*\n\d{2}:\d{2}:\d{2}", content, re.MULTILINE):
        segments = parse_srt(content)
        for s in segments:
            s["source"] = "auto_captions" if is_auto else "manual_captions"
            s["language"] = lang
        return segments
    elif "Dialogue:" in content:
        segments = parse_ass(content)
        for s in segments:
            s["source"] = "auto_captions" if is_auto else "manual_captions"
        return segments
    else:
        try:
            return parse_json3(content)
        except Exception:
            return []


# ---------------------------------------------------------------------------
# Export functions
# ---------------------------------------------------------------------------

def export_transcript_markdown(
    segments: list[dict[str, Any]],
    source_info: Optional[dict[str, Any]] = None,
    output_path: Optional[str] = None,
) -> str:
    """Export transcript segments to Markdown."""
    lines: list[str] = []

    if source_info:
        title = source_info.get("title", source_info.get("url", "N/A"))
        lines.append("# Transcripción")
        lines.append("")
        lines.append(f"**Fuente:** {title}")
        if source_info.get("uploader"):
            lines.append(f"**Canal:** {source_info['uploader']}")
        if source_info.get("duration"):
            mins, secs = divmod(int(source_info["duration"]), 60)
            lines.append(f"**Duración:** {mins}:{secs:02d}")
        lines.append(f"**Segmentos:** {len(segments)}")
        lines.append(f"**Idioma:** {source_info.get('language', 'N/A')}")
        lines.append("")

    lines.append("---")
    lines.append("")

    for seg in segments:
        start = seg.get("start", "")
        end = seg.get("end", "")
        text = seg.get("text", "")
        if text:
            lines.append(f"**[{start} → {end}]** {text}")
            lines.append("")

    if output_path:
        Path(output_path).write_text("\n".join(lines), encoding="utf-8")

    return "\n".join(lines)


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
        "whisper_installed": False,
        "whisper_version": None,
        "yt_dlp_installed": False,
        "ffmpeg_available": False,
        "tesseract_available": False,
        "scenedetect_available": False,
    }

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

    result["ffmpeg_available"] = (
        subprocess.run(["ffmpeg", "-version"], capture_output=True).returncode == 0
    )
    result["tesseract_available"] = (
        subprocess.run(["tesseract", "--version"], capture_output=True).returncode == 0
    )
    result["scenedetect_available"] = (
        subprocess.run(
            ["scenedetect", "--help"],
            capture_output=True,
        ).returncode == 0
    )

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
    transcriber = Transcriber(config={
        "strategy_order": ["platform_captions", "local_captions", "whisper"],
        "language": language,
    })
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
    transcriber = Transcriber(config={
        "strategy_order": ["local_captions", "whisper"],
        "language": language,
    })
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
                tracks.append({
                    "language": lang,
                    "format": sub.get("ext", ""),
                    "url": sub.get("url", ""),
                    "is_auto": True,
                })

    # Check manual captions
    if info.get("captions"):
        for lang, sub_list in info["captions"].items():
            for sub in sub_list:
                tracks.append({
                    "language": lang,
                    "format": sub.get("ext", ""),
                    "url": sub.get("url", ""),
                    "is_auto": False,
                })

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
        List of caption tracks.
    """
    return detect_subtitles(url)


def extract_local_captions(video_path: str | Path) -> list[dict[str, Any]]:
    """Extract local captions from a video file (contract API).

    Args:
        video_path: Path to local video file.

    Returns:
        List of caption tracks.
    """
    # For local files, we can only detect embedded subtitles via ffprobe
    # This is a placeholder - would need ffprobe to extract embedded subs
    return []


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
