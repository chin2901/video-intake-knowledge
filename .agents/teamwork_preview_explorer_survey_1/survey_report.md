# Comprehensive Survey Report: R1 Core Architecture, Performance & Platform Ingestion

**Author**: Explorer 1 (Investigation & Synthesis)  
**Date**: 2026-09-21T23:20:00Z  
**Project**: `video-intake-knowledge`  
**Target Scope**: R1 — Motor de Ingesta y Extracción de Alto Rendimiento  
**Guiding Standard**: AibOS Constitution (`/home/aibos/AGENTS.md`) — Zero Speculation, Ground Truth, Radical Simplicity ("Menos es Más").

---

## Executive Summary

An exhaustive empirical survey was conducted across the `video-intake-knowledge` repository. While the project exhibits an ambitious multi-package design (`video_intake_core`, `video_intake_schemas`, `video_intake_testkit`) with 17 specialized modules, the actual runtime execution reveals severe architectural drift, critical performance bottlenecks, broken batch processing stubs, regex failures on platform ingestion, and deceptive test coverage masking:

1. **Inspection Latency Deficit (>300ms)**: Cold CLI local file inspection clocks in at **381 ms** (failing the `<300ms` acceptance criterion). Root cause: eager top-level `import yt_dlp` in `video_intake_core/inspection/__init__.py:20`, which consumes **181.88 ms** alone even when inspecting purely local files via `ffprobe`. Isolated `ffprobe` execution requires only **69.05 ms**.
2. **Platform Acquisition Regressions & Fragility**:
   - **YouTube Ingestion Bug**: Regex in `acquisition/__init__.py:31` requires `v=` to immediately succeed `watch?`. URLs with parameters preceding `v=` (e.g., `?feature=shared&v=...`, timestamps `?t=10&v=...`) return `None` and crash with `ValueError: Unsupported source type`.
   - **Facebook Ingestion Gaps**: `fb.watch/...` mobile shortlinks and `m.facebook.com` are completely unsupported.
   - **False Redirect Following**: `resolve_url(follow_redirects=True)` never issues network requests. Shortened TikTok links (`vm.tiktok.com`) fail canonical ID extraction and resolve to raw URLs with dummy hashes.
   - **`file://` Inconsistency**: `detect_video_sources` emits `file://` URLs, but `detect_source` rejects `file://` URIs because `Path("file:///...").exists()` returns `False`.
3. **Batch Processing is a Mock Stub**: `cmd_batch` in `cli/__init__.py:462-508` loops over manifest entries, prints them, and terminates. It calls **zero extraction, zero job creation, and zero background processing**.
4. **Architectural Duplication & Drift**: `orchestrator.py` completely bypasses the modular sub-packages (`acquisition`, `audio`, `transcription`, `visual`, `ocr`) and instead implements an ad-hoc, sequential, un-parallelized pipeline using direct `subprocess.run` calls.
5. **False Coverage Illusion**: Global test coverage is officially reported as passing, but true coverage is only **47%**. In `pyproject.toml:149`, `omit = ["**/__init__.py", ...]` hides virtually the entire codebase because almost all implementation logic resides directly inside package `__init__.py` files.
6. **Git Tree Pollution**: `JobManager` in `jobs/__init__.py:44` defaults to `db_path="jobs.db"` in the current working directory, writing a SQLite database into the Git root repository and directly violating acceptance criteria.

---

## 1. Codebase Layout, Entry Points, Dependencies & Packaging

### 1.1 Packaging and Module Structure
The repository is laid out as a multi-package Python project under `packages/`:
```
/srv/video-intake-knowledge/
├── pyproject.toml              # Build & dependency specification
├── Makefile                    # Target definitions
├── SKILL.md                    # Agentic skill specification
├── install.sh                  # Host agent installer
├── packages/
│   ├── video_intake_core/      # Core execution engine & CLI
│   ├── video_intake_schemas/   # Versioned JSON schema catalog
│   └── video_intake_testkit/   # Testing utilities & fixtures
├── adapters/                   # Adapters (hermes, agy, claude-code, codex, opencode)
├── config/                     # Configuration presets (default.yaml, production.yaml, etc.)
└── tests/                      # Pytest test suite (contract, e2e, integration, security, unit)
```

### 1.2 Entry Points
- Specified in `pyproject.toml:106-107`:
  ```toml
  [project.scripts]
  video-intake = "video_intake_core.cli:main"
  ```
- The CLI uses `argparse` with command handlers registered in `packages/video_intake_core/cli/__init__.py` and submodules (`artifacts.py`, `cleanup.py`, `config_cmd.py`, `doctor.py`, `export.py`, `extract.py`, `memory.py`, `menu.py`, `models.py`, `proposals.py`, `status.py`).

### 1.3 Packaging & Pyproject Deficiencies
1. **Pytest Misconfiguration in `pyproject.toml:140`**:
   The table is titled `[tool.preamble]` instead of standard `[tool.pytest.ini_options]`. Pytest 9.1 ignores `tool.preamble` and falls back to default discovery unless options are explicitly passed.
2. **Deceptive Coverage Masking (`pyproject.toml:146-150`)**:
   ```toml
   [tool.coverage.run]
   source = ["video_intake_core"]
   branch = true
   omit = ["**/__init__.py", "**/cli.py", "**/__main__.py"]
   ```
   Because almost all core modules (`acquisition`, `inspection`, `audio`, `transcription`, `visual`, `ocr`, `storage`, `security`, `jobs`) place their primary code in `__init__.py`, omitting `**/__init__.py` eliminates >75% of the codebase from coverage analysis.
   - True statement coverage with all modules included: **47%** (1332 statements, 652 misses).
   - Target acceptance criteria requirement: **>95%**.
3. **Runtime Python & SQLite Leaks**:
   Tests running under Python 3.14 trigger 24+ `ResourceWarning: unclosed database in <sqlite3.Connection object>` because `JobManager` and SQLite memory providers do not close database connections on termination.
4. **Git Root Pollution**:
   `JobManager` defaults to `db_path="jobs.db"` in current working directory (`jobs/__init__.py:44`), causing `jobs.db` (28 KB binary) to sit directly in `/srv/video-intake-knowledge/jobs.db`.

---

## 2. Media Acquisition Core (YouTube, Facebook, Instagram, TikTok, Local Files)

### 2.1 Pattern Matching & Ingestion Gaps
Examining `packages/video_intake_core/acquisition/__init__.py`:

#### A. YouTube Regex Vulnerability
Lines 30-37 define:
```python
YOUTUBE_PATTERNS = [
    re.compile(r"^https?://(www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)", re.IGNORECASE),
    ...
]
```
- **Empirical Test**:
  - `https://www.youtube.com/watch?v=dQw4w9WgXcQ` -> `SourceType.YOUTUBE` (Pass)
  - `https://www.youtube.com/watch?feature=shared&v=dQw4w9WgXcQ` -> `None` (FAIL)
  - `https://youtube.com/watch?time_continue=10&v=dQw4w9WgXcQ` -> `None` (FAIL)
- **Impact**: Any mobile-shared or parameter-ordered YouTube link fails source detection and raises `ValueError: Unsupported source type for URL`.

#### B. Facebook Gaps
Lines 39-48 omit standard shortened mobile links:
- `https://fb.watch/abc1234/` -> `None` (FAIL)
- `https://m.facebook.com/watch?v=12345678` -> `None` (FAIL)

#### C. Redirect Resolution Fallacy
Lines 124-211 define `resolve_url(url, follow_redirects=True)`:
```python
def resolve_url(url: str, follow_redirects: bool = True) -> ResolvedURL:
    ...
    return ResolvedURL(
        original_url=url,
        resolved_url=resolved_url,
        canonical_id=canonical_id,
        source_type=source_type,
        redirect_chain=[url] if follow_redirects else [],
    )
```
- Despite the parameter `follow_redirects: bool = True`, **no HTTP request (HEAD/GET) is ever dispatched**.
- Shortened URLs like `https://vm.tiktok.com/ZM123456/` cannot extract an ID via regex (`g.isdigit()` check fails on alphanumeric string), falling back to SHA-256 hash. The returned `resolved_url` is identical to the raw input.

#### D. Local File URI Inconsistency
- In `detect_video_sources` (lines 394, 417), local files are emitted as:
  `url=f"file://{direct_path.resolve()}"`
- In `detect_source` (lines 99-102):
  ```python
  path = Path(url_or_path)
  if path.exists() and path.is_file():
  ```
  `Path("file:///path/to/video.mp4").exists()` evaluates to `False`. Thus, `detect_source("file:///...")` returns `None`.

#### E. Audio Acquisition Inefficiency
In `packages/video_intake_core/audio/__init__.py:87-104`:
```python
def _download_to_temp(url: str) -> Path:
    import yt_dlp
    tmp = Path(tempfile.mktemp(suffix=".mp4"))
    ydl_opts = {
        "format": "bestvideo+bestaudio/best",
        "outtmpl": str(tmp),
        "merge_output_format": "mkv",
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return tmp
```
- When a user requests **audio extraction only**, the engine downloads the entire multi-gigabyte video stream (`bestvideo+bestaudio`), then calls ffmpeg to discard the video track!
- Ground truth fix: Use `format: bestaudio/best` and extract audio directly during yt-dlp download (`--extract-audio --audio-format mp3`).

---

## 3. Metadata Inspection Mechanism & Latency Benchmarks (<300ms Requirement)

### 3.1 Empirical Latency Benchmarks
Acceptance Criterion:
> *"Tiempo de inicio de la CLI y de inspección de fuentes locales inferior a 300ms."*

Empirical measurements on `/srv/video-intake-knowledge`:
| Phase / Action | Command / Function | Latency | Status |
|---|---|---|---|
| Python interpreter startup | `python3 -c "pass"` | 31.2 ms | Baseline |
| CLI Help / Parser | `video-intake --help` | 105.0 ms | Pass |
| **CLI Local Inspect** | `video-intake inspect sample.mp4` | **381.0 ms** | **FAIL (>300ms)** |
| Internal Inspection Import | `from video_intake_core.inspection import ...` | **177.8 ms** | Bottleneck |
| `yt_dlp` Isolated Import | `import yt_dlp` | **181.9 ms** | Root Cause |
| Native `ffprobe` Execution | `ffprobe -v error ...` on sample.mp4 | 54.0 - 66.2 ms | Fast |
| Isolated Local Inspect (no yt-dlp) | Custom Python script executing ffprobe & JSON parse | **69.0 ms** | Optimal |

### 3.2 Root Cause of Latency Violation
In `packages/video_intake_core/inspection/__init__.py:20`:
```python
import yt_dlp
```
`yt_dlp` is imported unconditionally at the top of the module. `yt_dlp` imports hundreds of platform extractors and cryptographic routines, requiring ~180 ms of CPU time.
- By converting `import yt_dlp` to a lazy import inside `inspect_download_url()`, the local file inspection time drops from **381 ms to ~120-140 ms** (a ~65% latency reduction), comfortably fulfilling the `<300ms` SLA.

### 3.3 Data Flow & Contract Defect in Metadata Inspection
When running `video-intake inspect tests/fixtures/video/sample.mp4`, the CLI outputs:
```
Título: N/A
Plataforma: local
Duración: 5.0s (N/A)
Streams: 0
URL: /srv/video-intake-knowledge/tests/fixtures/video/sample.mp4
```
Notice:
1. `Título: N/A`: `inspect_video()` in `inspection/__init__.py:454` looks for `result.get("title")`. For local files, `inspect_video_file()` returns `filename`, not `title`.
2. `Streams: 0`: `inspect_video_file()` populates `streams: [...]`, but `inspect_video()` only copies `formats: result.get("formats", [])` (empty for local files).
3. Missing Resolution, FPS, and Codecs: `cmd_inspect()` in `cli/__init__.py:406-415` queries `info.get("width")`, `info.get("height")`, `info.get("fps")`, `info.get("video_codec")`, and `info.get("audio_codec")`. However, the contract dataclass `VideoInfo` does not have any of these attributes. Rich media attributes extracted by ffprobe are discarded before reaching the user.

---

## 4. Batch Processing, Concurrency, Memory/CPU & Streaming FFprobe

### 4.1 Mock Batch Processing (`cmd_batch`)
In `packages/video_intake_core/cli/__init__.py:488-507`:
```python
    for entry in entries:
        url = entry.get("url") or entry.get("file")
        if not url:
            continue
        sources = _detect_sources([url] if url.startswith("http") else [], [url] if not url.startswith("http") else [])
        if not sources:
            print(f"  ✗ No procesable: {url}")
            continue
        s = sources[0]
        mode = entry.get("mode", "individual")
        select = entry.get("select", "6")

        print(f"  · {s.get('title', url)} [{select}]")
        if args.json:
            print(json.dumps({"source": url, "mode": mode, "select": select}))

    print(f"\nLote completado: {len(entries)} vídeos procesados.")
```
**Ground Truth Finding**: `cmd_batch` performs no processing whatsoever. It merely prints lines from the YAML manifest and declares the batch completed. No worker threads, no queues, no sub-processes are spawned.

### 4.2 Concurrency & Orchestrator Execution
In `packages/video_intake_core/orchestrator.py:94`:
```python
for idx, src in enumerate(sources, 1):
```
- Processing is completely sequential and blocking.
- `max_parallel_jobs: 4` is configured in `config/default.yaml:142`, but completely ignored by both `orchestrator.py` and `cli/__init__.py`.
- No `concurrent.futures.ThreadPoolExecutor` or `ProcessPoolExecutor` is utilized.

### 4.3 Memory & Resource Waste
1. **Unbounded Frame Generation**:
   `orchestrator.py:266-270`:
   ```bash
   ffmpeg -y -i <video> -vf fps=1/5,scale=1280:-1 -q:v 2 frame_%04d.jpg
   ```
   For a 60-minute video, this extracts 720 uncompressed JPEG images to disk (consuming hundreds of megabytes).
2. **60-Second Hardcap on OCR Analysis**:
   `orchestrator.py:278`:
   ```python
   for frame in frames[:12]:
   ```
   Even though hundreds of frames are extracted, only the first 12 frames (0 to 60 seconds) are passed to OCR. Any presentation slides, code, or diagrams appearing after minute 1 are ignored.
3. **Sequential Subprocess OCR**:
   Instead of using batch inference or memory-buffered OCR, `orchestrator.py:280` spawns a brand new `tesseract` process per frame:
   `subprocess.run(["tesseract", str(frame), str(txt_file), "-l", "spa+eng"])`
   12 separate OS process spawns per video, each reloading Tesseract dictionaries and language models.

### 4.4 Streaming FFprobe
- Current inspection relies on reading entire files from the local filesystem or running full `yt-dlp` metadata downloads.
- Opportunity for streaming inspection:
  - For remote streams, `yt-dlp -g <url>` can obtain the direct CDN media stream URL.
  - Streaming this URL directly into `ffprobe -v error -show_format -show_streams -i <stream_url>` with `-probesize 1000000 -analyzeduration 1000000` allows instantaneous inspection of remote container metadata without downloading the video payload or waiting for yt-dlp extractor bloat.

---

## 5. Native Fallbacks (yt-dlp, ffmpeg) & Optional AI Fallbacks (Whisper, Tesseract)

### 5.1 System Host Reality vs Python Dependencies
Host inspection (`which` & Python runtime):
- `/usr/bin/ffmpeg`: Installed (v8.0.1)
- `/usr/bin/ffprobe`: Installed
- `/usr/bin/tesseract`: Installed
- `/home/aibos/.local/bin/yt-dlp`: Installed (2026.08.19)
- Python virtual environment packages:
  - `yt_dlp`: Installed
  - `cv2` (opencv-python-headless): Installed
  - `moviepy`: Installed
  - `openai-whisper`: **NOT INSTALLED**
  - `pytesseract`: **NOT INSTALLED**
  - `scenedetect`: **NOT INSTALLED**

### 5.2 Graceful Degradation Audit
1. **Subtitles & Transcription**:
   - Priority 1: Adjacent local subtitle file (`.srt`, `.vtt`, `.sub`). (Functional)
   - Priority 2: Remote platform subtitles via `yt-dlp --write-subs --write-auto-subs`. (Functional)
   - Priority 3: Local Whisper (`import whisper`). When not installed, gracefully catches `(ImportError, Exception)` and continues without failing the job.
2. **Visual & OCR**:
   - `video_intake_core/visual/__init__.py` has fallback from `scenedetect` to `ffmpeg select='gt(scene,threshold)'`. (Functional)
   - However, `orchestrator.py` bypasses both and does simple fixed `fps=1/5` keyframing.
   - For OCR, `orchestrator.py` checks `shutil.which("tesseract")` and directly executes `/usr/bin/tesseract`, bypassing the missing `pytesseract` Python module.

### 5.3 Architectural Drift & Component Fragmentation
The biggest structural defect in the repository is **dual implementation**:
- **Layer A**: The modular library (`video_intake_core/transcription`, `audio`, `visual`, `ocr`, `acquisition`). Well-structured, dataclass-based, with schema validation, but largely unused by the CLI.
- **Layer B**: The monolithic script (`orchestrator.py`). Used directly by `video-intake extract` and `test_orchestrator_execution.py`. Directly invokes raw CLI binaries and re-implements basic heuristics inline.

---

## 6. Concrete Gaps Against R1 Requirements & Acceptance Criteria

| Requirement / Acceptance Criterion | Current Status | Empirical Evidence | Severity | Root Cause & Remediation |
|---|---|---|---|---|
| **CLI & Local Inspection < 300ms** | **FAILED** (381 ms) | `time video-intake inspect sample.mp4` = 381ms. `import yt_dlp` = 181.88ms. | **HIGH** | `inspection/__init__.py:20` eagerly imports `yt_dlp`. Fix: Lazy import `yt_dlp` only when remote URL is detected. |
| **Complete & Accurate Metadata** | **FAILED** | Local inspection yields `Título: N/A`, `Streams: 0`, 0 resolution/fps/codecs. | **HIGH** | `inspect_video()` in `inspection/__init__.py:452` fails to map local file attributes into `VideoInfo`. `VideoInfo` missing `width`, `height`, `fps`, `streams`. |
| **Concurrent Batch Processing** | **FAILED** | `cmd_batch` in `cli/__init__.py:488` is a no-op print loop; orchestrator is strictly sequential. | **CRITICAL** | Implement real batch worker engine with `ThreadPoolExecutor(max_workers=max_parallel_jobs)` and SQLite state updates. |
| **Robust Platform Ingestion (YouTube, FB, IG, TikTok)** | **FAILED** | YouTube URLs with params before `v=` fail. `fb.watch` fails. TikTok short links don't follow redirects. | **HIGH** | Fix regexes in `acquisition/__init__.py` to parse query parameters with `urllib.parse`. Implement genuine HTTP HEAD/GET redirect resolution. |
| **Clean Git Tree (Zero DB / Cache Pollution)** | **FAILED** | `jobs.db` is generated directly in project root `/srv/video-intake-knowledge/jobs.db`. | **MEDIUM** | `JobManager.__init__` defaults to `"jobs.db"`. Must default to `~/.video-intake/jobs.db` or config storage path. |
| **Native Fallback Priority over AI** | **PARTIAL** | Platform subtitles and ffmpeg keyframing are prioritized, but orchestrator duplicates logic and ignores modular engine. | **MEDIUM** | Unify `orchestrator.py` with `video_intake_core.{audio, transcription, visual, ocr}` SSoT modules. |
| **Test Coverage > 95%** | **FAILED** (47%) | `pytest --cov=video_intake_core` shows 47% true coverage. `pyproject.toml` omits `**/__init__.py`. | **CRITICAL** | Remove misleading omit rules; add thorough unit and integration test coverage for all modules. |
| **Graceful Degradation** | **PASSED** | When `whisper` or `pytesseract` is absent, execution logs warning and proceeds with platform subtitles/empty OCR. | **PASS** | Working as designed. |

---

## Conclusion & Architectural Elevation Directives

To bring `video-intake-knowledge` to world-class 100k-star engineering excellence (R1):
1. **Immediate Latency Win**: Make `yt_dlp` lazily imported in `inspection/__init__.py`.
2. **Contract Restoration**: Align `VideoInfo` dataclass and `inspect_video_file` mapping so resolution, streams, codecs, fps, and title are preserved.
3. **True Batch Concurrency**: Replace the `cmd_batch` dummy loop with a robust, bounded `ThreadPoolExecutor` concurrent runner supporting progress bars and cancellation.
4. **URL Normalizer Overhaul**: Replace brittle URL regexes with `urllib.parse.parse_qs` parameter parsing to support all YouTube, Facebook, and TikTok parameter variants and shortlinks.
5. **SSoT Unification**: Refactor `orchestrator.py` to delegate directly to `video_intake_core.acquisition`, `audio`, `transcription`, `visual`, and `ocr` rather than duplicate inline CLI commands.
6. **Isolated Persistence**: Enforce `~/.video-intake/` for all SQLite databases (`jobs.db`, `memory.db`), permanently removing any database artifacts from the Git working tree.
