# Task Assignment: Worker M1 (High-Performance Engine, Acquisition & Inspection - R1)

## Context
- Project Root: `/srv/video-intake-knowledge`
- Working Directory: `/srv/video-intake-knowledge/.agents/teamwork_preview_worker_m1`
- Authoritative Requirements: `/srv/video-intake-knowledge/.agents/ORIGINAL_REQUEST.md` (MUST read in full)
- System Constitution: `/home/aibos/AGENTS.md` (MUST adhere strictly)
- Scope & Architecture: `/srv/video-intake-knowledge/.agents/PROJECT.md`
- Survey Findings: Read `/srv/video-intake-knowledge/.agents/teamwork_preview_explorer_survey_1/survey_report.md`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Write Ownership
You EXCLUSIVELY own and may modify:
- `packages/video_intake_core/inspection/`
- `packages/video_intake_core/acquisition/`
- `packages/video_intake_core/audio/`
- `packages/video_intake_core/batch.py` (or batch module)
- `packages/video_intake_core/orchestrator.py` (engine & pipeline logic)
DO NOT modify files outside your ownership boundary.

## Objectives & Implementation Directives
1. **Sub-300ms Inspection SLA (F1)**:
   - Make `yt_dlp` a lazy import in `packages/video_intake_core/inspection/__init__.py` (do not import at module top-level; only import when inspecting remote URLs that require it).
   - Optimize native `ffprobe` execution and JSON parsing for local media files.
   - Empirically verify that `video-intake inspect <sample_video>` executes in <300ms (target: ~100-150ms).
2. **VideoInfo Contract & Rich Metadata Restoration (F2)**:
   - Ensure `VideoInfo` dataclass in `schemas/source.py` / `inspection/__init__.py` properly retains and exposes `width`, `height`, `fps`, `streams`, `video_codec`, `audio_codec`, `format_name`, `file_size_bytes`, and `title`.
   - Update `inspect_video()` so local files map `filename` to `title` and populate all extracted stream attributes without data loss.
3. **Platform Ingestion & Normalizer Overhaul (F3)**:
   - In `packages/video_intake_core/acquisition/__init__.py`:
     - Overhaul YouTube URL detection to use `urllib.parse` so any parameter ordering (`?feature=shared&v=...`, `?t=10&v=...`) is cleanly parsed.
     - Add support for Facebook shortlinks (`https://fb.watch/...`) and mobile URLs (`m.facebook.com`).
     - Support `file://` URIs cleanly in `detect_source`.
     - Implement real HTTP HEAD/GET redirect resolution for shortened URLs (such as `vm.tiktok.com`) to extract canonical platform IDs.
4. **Direct Audio Download Stream (F4)**:
   - In `packages/video_intake_core/audio/__init__.py`: download direct `bestaudio` stream with `yt-dlp` instead of downloading full 1080p/4k video when only audio is needed.
5. **Real Concurrent Batch Processing (F5)**:
   - Replace the dummy loop in `cmd_batch` / batch execution with a genuine `ThreadPoolExecutor(max_workers=max_parallel_jobs)` that processes entries concurrently, tracks job statuses in SQLite, and emits progress.
6. **Pipeline Unification (F6)**:
   - Refactor `orchestrator.py` to delegate directly to `acquisition`, `audio`, `transcription`, `visual`, and `ocr` modular components.
7. **Verification**:
   - Run tests for your components (`pytest tests/unit/test_inspection.py tests/unit/test_acquisition.py -v`).
   - Deliver `handoff.md` with verification commands, benchmark results, and status.

## 2026-09-22T01:06:52Z
Implement features F1, F2, F3, F4, F5, F6. Run tests to verify your implementation. Deliver handoff.md and notify the orchestrator via send_message.

## 2026-09-21T23:13:08Z
**Context**: Milestone M1 Implementation (Engine & Batch)
**Content**: E2E Test Writer encountered a circular import between `orchestrator.py` and `batch.py`:
- `orchestrator.py:26` imports `from video_intake_core.batch import BatchResult, BatchRunner, run_batch`
- `batch.py:22` imports `from video_intake_core.orchestrator import check_and_extract, parse_extraction_choices`
This causes `ImportError: cannot import name 'check_and_extract' from partially initialized module 'video_intake_core.orchestrator'`.
**Action**: Please resolve this circular import cleanly in `batch.py` / `orchestrator.py` (e.g. by making the import in `batch.py` function-local or lazy, or refactoring shared types) so that `video_intake_core` imports cleanly.
