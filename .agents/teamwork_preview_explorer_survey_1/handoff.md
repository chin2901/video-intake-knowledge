# Handoff Report: Explorer 1 (R1 Core Architecture, Performance & Ingestion Survey)

## 1. Observation

### Observation 1: CLI Metadata Inspection Latency Bottleneck
- **Command & Timing**:
  ```bash
  $ time /srv/video-intake-knowledge/venv/bin/video-intake inspect tests/fixtures/video/sample.mp4
  Título: N/A
  Plataforma: local
  Duración: 5.0s (N/A)
  Streams: 0
  URL: /srv/video-intake-knowledge/tests/fixtures/video/sample.mp4

  real    0m0,381s
  user    0m0,333s
  sys     0m0,049s
  ```
- **Code Path**: `packages/video_intake_core/inspection/__init__.py:20`:
  ```python
  import yt_dlp
  ```
- **Isolated Timing**:
  - `python -c "import yt_dlp"` takes **181.88 ms**.
  - `inspect_video_file` (ffprobe execution + JSON parse) takes **66.22 ms**.
  - Isolated local inspection without importing `yt_dlp` takes **69.05 ms**.

### Observation 2: Metadata Extraction Data Loss
- **Code Path**: `packages/video_intake_core/inspection/__init__.py:452-474` and `packages/video_intake_core/cli/__init__.py:401-417`:
  - `inspect_video()` maps `result.get("title")` instead of `result.get("filename")` for local files.
  - `inspect_video()` maps `result.get("formats", [])` to `formats` instead of mapping `result.get("streams", [])`.
  - `VideoInfo` dataclass does not define `width`, `height`, `fps`, `video_codec`, `audio_codec`, or `audio_channels`.
  - Result: `video-intake inspect` prints `Título: N/A`, `Streams: 0`, and omits resolution, fps, and codecs for all local files.

### Observation 3: Ingestion Regex & Resolution Failures
- **Code Path**: `packages/video_intake_core/acquisition/__init__.py:31`:
  ```python
  re.compile(r"^https?://(www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)", re.IGNORECASE)
  ```
- **Runtime Error**:
  ```python
  >>> from video_intake_core.acquisition import resolve_url
  >>> resolve_url('https://www.youtube.com/watch?feature=shared&v=dQw4w9WgXcQ')
  ValueError: Unsupported source type for URL: https://www.youtube.com/watch?feature=shared&v=dQw4w9WgXcQ
  ```
- **Shortlink Failure**:
  `resolve_url('https://vm.tiktok.com/ZM123456/', follow_redirects=True)` never performs HTTP redirect resolution; returns raw URL with dummy SHA-256 ID.
- **URI Detection Inconsistency**:
  `detect_video_sources` outputs `file://` URIs, but `detect_source` rejects `file://` because `Path("file:///...").exists()` returns `False`.

### Observation 4: Mock Batch Processing
- **Code Path**: `packages/video_intake_core/cli/__init__.py:488-507`:
  ```python
  for entry in entries:
      ...
      print(f"  · {s.get('title', url)} [{select}]")
      if args.json:
          print(json.dumps({"source": url, "mode": mode, "select": select}))

  print(f"\nLote completado: {len(entries)} vídeos procesados.")
  ```
  `cmd_batch` never executes extraction, creates no jobs, and spawns no concurrent tasks.

### Observation 5: Sequential Execution & Architectural Drift
- **Code Path**: `packages/video_intake_core/orchestrator.py:94`:
  ```python
  for idx, src in enumerate(sources, 1):
  ```
  `orchestrator.py` runs a blocking sequential loop using raw subprocess calls (`ffmpeg`, `yt-dlp`, `tesseract`), completely bypassing modular sub-packages (`audio`, `transcription`, `visual`, `ocr`).
  `max_parallel_jobs: 4` in `config/default.yaml:142` is completely ignored.

### Observation 6: Git Working Tree Pollution
- **Code Path**: `packages/video_intake_core/jobs/__init__.py:44`:
  ```python
  def __init__(self, db_path: str | Path = "jobs.db") -> None:
  ```
  Running operations in the project root creates `/srv/video-intake-knowledge/jobs.db` directly in the working tree.

### Observation 7: Test Coverage Concealment
- **Code Path**: `pyproject.toml:146-150`:
  ```toml
  [tool.coverage.run]
  source = ["video_intake_core"]
  branch = true
  omit = ["**/__init__.py", "**/cli.py", "**/__main__.py"]
  ```
  Testing true coverage via `pytest --cov=video_intake_core` shows **47%** coverage (1332 statements, 652 misses).

---

## 2. Logic Chain

1. **Inspection Latency**: Observation 1 proves that local file inspection takes 381ms. Isolated benchmarking proves that importing `yt_dlp` accounts for 181.88ms of that time, while native `ffprobe` execution requires only 54-66ms. Therefore, deferring `yt_dlp` import until remote URL inspection is required will reduce cold CLI local inspection to ~120-140ms, achieving the `<300ms` acceptance criterion.
2. **Metadata Integrity**: Observation 2 proves that `inspect_video()` fails to forward `inspect_video_file()` attributes into `VideoInfo`. By adding the missing attributes (`width`, `height`, `fps`, `streams`, codecs) to `VideoInfo` and mapping `filename` to `title` for local files, `video-intake inspect` will output accurate, rich metadata.
3. **Platform Ingestion Robustness**: Observation 3 demonstrates that parameter-first YouTube URLs and shortlinks crash or fail canonicalization due to rigid regex patterns and fake redirect logic. Replacing regexes with `urllib.parse` query parameter inspection and implementing genuine HTTP HEAD redirect following will make ingestion deterministic across platforms.
4. **Batch Scaling**: Observation 4 and 5 demonstrate that batch processing is currently a cosmetic stub, and orchestrator execution is single-threaded. Integrating a `ThreadPoolExecutor` bounded by `max_parallel_jobs` (default 4) into `cmd_batch` and `check_and_extract` will enable true parallel batch ingestion without memory exhaustion.
5. **Git Tree Cleanliness**: Observation 6 demonstrates that `JobManager` writes `jobs.db` into CWD. Defaulting the path to `~/.video-intake/jobs.db` ensures the Git repository remains 100% free of SQLite databases.
6. **Testing Rigor**: Observation 7 demonstrates that the project's claim of high coverage was artificially achieved by omitting `**/__init__.py` files. Correcting `pyproject.toml` and adding missing unit/integration tests is required to attain a genuine >95% coverage standard.

---

## 3. Caveats

- **Network Constraints**: Live downloads from external platforms (YouTube, TikTok, Instagram, Facebook) were evaluated statically and via URL structure parsing rather than live network streaming against platforms that require active residential IP/cookies.
- **Optional ML Inference**: Host machine has `/usr/bin/tesseract` and `/usr/bin/ffmpeg` installed, but `openai-whisper` and `pytesseract` are not installed in the virtual environment. Evaluations of Whisper were based on codebase code paths and fallback handling.

---

## 4. Conclusion

The current codebase contains solid foundational scaffolding, but suffers from 4 critical operational deficits:
1. **Broken Inspection SLA**: 381ms cold latency caused by eager `yt_dlp` import.
2. **Broken Batch Processing**: `cmd_batch` is a no-op mock stub.
3. **Fragile Ingestion Engine**: YouTube query parameter fragility, unhandled Facebook shortlinks, and non-functional redirect following.
4. **Architectural Drift**: `orchestrator.py` duplicates functionality instead of utilizing the modular core.

These findings are fully documented with line-by-line evidence and benchmarks in `survey_report.md`.

---

## 5. Verification Method

To independently verify all findings:

1. **Benchmark Local Inspection Latency**:
   ```bash
   time /srv/video-intake-knowledge/venv/bin/video-intake inspect tests/fixtures/video/sample.mp4
   ```
   *Expected result*: Displays real execution time (~380ms) and outputs `Streams: 0`, `Título: N/A`.

2. **Verify yt_dlp Import Cost**:
   ```bash
   /srv/video-intake-knowledge/venv/bin/python -c "import time; t0=time.perf_counter(); import yt_dlp; print(f'yt_dlp import: {(time.perf_counter()-t0)*1000:.2f}ms')"
   ```
   *Expected result*: Measures ~180ms.

3. **Verify YouTube URL Ingestion Bug**:
   ```bash
   /srv/video-intake-knowledge/venv/bin/python -c "from video_intake_core.acquisition import resolve_url; resolve_url('https://www.youtube.com/watch?feature=shared&v=dQw4w9WgXcQ')"
   ```
   *Expected result*: Raises `ValueError: Unsupported source type for URL`.

4. **Verify Mock Batch CLI**:
   Inspect `packages/video_intake_core/cli/__init__.py:488-507`. Notice absence of any job dispatch or extraction calls.

5. **Verify Real Coverage**:
   ```bash
   /srv/video-intake-knowledge/venv/bin/pytest --cov=video_intake_core --cov-report=term
   ```
   *Expected result*: Coverage is only 47% with 652 misses and SQLite unclosed connection warnings.
