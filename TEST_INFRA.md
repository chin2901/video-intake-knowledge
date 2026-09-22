# Project: video-intake-knowledge Engineering Elevation

## Architecture
- **Packaging Layout**: Multi-package architecture under `/srv/video-intake-knowledge/packages/`:
  - `video_intake_core`: Main engine, acquisition, inspection, extraction, storage, memory, jobs, and unified CLI.
  - `video_intake_schemas`: JSON schema definitions for data exchange.
  - `video_intake_testkit`: Test fixtures, synthetic media generators, and mocking utilities.
- **Data Flow & Dual Pipeline**:
  - **Inspection**: URL/Path -> Security Validator -> Lazy Probe / Native ffprobe -> Rich VideoInfo (<300ms SLA).
  - **Extraction**: User Selection (Phase 1) -> Security Gateway -> Parallel/Direct Acquisition -> Multi-layer extraction (Video, Audio, Subtitles, Audio Context, Visual OCR) -> Sanitization Boundary -> Storage Artifacts.
  - **Routing & Scaffolding**: User Selection (Phase 2) -> Session Injection / Memory Bank (~/.video-intake/) / Dynamic Proposals (`video-intake proposals --scaffold`).
- **Isolation Boundaries**:
  - User memory and jobs database strictly housed in `~/.video-intake/` (`memory.db`, `jobs.db`).
  - Working tree strictly clean of database binaries, cache, or `.memory/` artifacts.
  - LLM prompt context strictly enclosed in XML containment boundaries (`<video_transcript>`, `<ocr_extracted_content>`).

---

## Feature Inventory

| # | Feature | Description | Milestone | Source |
|---|---|---|---|---|
| F1 | Sub-300ms CLI & Local Inspection | Lazy import `yt_dlp` in `inspection/__init__.py`, optimize ffprobe JSON streaming to achieve <300ms SLA | M1 | Survey 1 |
| F2 | Rich VideoInfo Contract Restoration | Map title, streams, resolution, fps, and codecs from ffprobe/yt-dlp into `VideoInfo` without data loss | M1 | Survey 1 |
| F3 | Robust Platform Ingestion & URL Normalization | Parse YouTube query parameters (`?v=`, `?feature=shared&v=`), Facebook shortlinks (`fb.watch`, `m.facebook.com`), TikTok HTTP redirect resolution, and `file://` URIs | M1 | Survey 1 |
| F4 | Direct Audio Download Stream | Download direct `bestaudio` stream with yt-dlp without downloading full video when only audio is requested | M1 | Survey 1 |
| F5 | Concurrent Batch Processing Engine | Replace dummy `cmd_batch` loop with bounded `ThreadPoolExecutor(max_workers=max_parallel_jobs)` and SQLite job tracking | M1 | Survey 1 |
| F6 | Engine Pipeline Unification | Refactor `orchestrator.py` to delegate directly to modular sub-packages (`acquisition`, `audio`, `transcription`, `visual`, `ocr`) | M1 | Survey 1 |
| F7 | Canonical Single Source of Truth for SKILL.md | Root `SKILL.md` with standard YAML frontmatter, clean 2-phase numbering, proposals CLI command, remove duplicate `skill/SKILL.md` and obsolete `vitk` | M2 | Survey 2 |
| F8 | Multi-Platform Agent Adapters | Add Cursor adapter (`adapters/cursor/`, `.cursorrules`), fix Codex adapter, fix Hermes path bug & commands, update AGY with Phase 2 routing, modernize Claude Code & OpenCode | M2 | Survey 2 |
| F9 | Multi-Platform `install.sh` | Update installer to support `--hermes`, `--agy`, `--claude-code`, `--opencode`, `--codex`, `--cursor`, `--all` | M2 | Survey 2 |
| F10 | 2-Phase Conversational Flow CLI Integration | Interactive TTY detection in `video-intake extract` and dedicated `video-intake interactive [URL]` with Phase 1 extraction menu and Phase 2 knowledge routing | M2 | Survey 2 |
| F11 | Selection & Menu Parser Consolidation | Single SSoT in `cli/menu.py` eliminating 3 divergent parsers | M2 | Survey 2 |
| F12 | Dynamic Proposal & Asset Scaffolding | Elevate `video-intake proposals --scaffold {skill,tool,agent}` to generate dynamic templates derived from video transcript, topics, and chapters | M2 | Survey 2 |
| F13 | Deterministic SSRF Prevention | Socket DNS resolution (`socket.getaddrinfo`), IP canonicalization, strict blocking of loopback, private, link-local, carrier-grade NAT, and cloud metadata IPs (`169.254.169.254`, `metadata.google.internal`), neutralizing octal/hex/decimal IP bypasses and DNS rebinding | M3 | Survey 3 |
| F14 | Security Gateway Enforcement | Wire `validate_url` and `validate_video_url` directly before any network call in `orchestrator.py` and `acquisition/` | M3 | Survey 3 |
| F15 | Path Traversal Defenses in File Ingestion & Storage | Enforce `sanitize_path` and `validate_local_file` in `orchestrator.py` and `storage/__init__.py`, prevent arbitrary local file copying | M3 | Survey 3 |
| F16 | Prompt & Subtitle Injection Sanitization | Apply `sanitize_for_prompt` and LLM boundary encapsulation to transcripts and OCR text in `context/__init__.py` | M3 | Survey 3 |
| F17 | Strict SQLite & Memory Isolation | Enforce `~/.video-intake/` for all SQLite databases including `jobs.db` and `memory.db`; delete root `jobs.db`; clean git tree | M3 | Survey 3 |
| F18 | CLI Architecture Modularization & SSoT | Refactor `cli/__init__.py` monolith to delegate to modular files `cli/*.py`, eliminating duplicate `cmd_*` functions and dead code | M4 | Survey 2, 3 |
| F19 | Transparent Coverage Configuration | Remove deceptive `omit = ["**/__init__.py"]` from `pyproject.toml` | M4 | Survey 1, 3 |
| F20 | Modern UV Dependency Groups & CI/CD Workflow Alignment | Define `[dependency-groups]` matching `.github/workflows/ci.yml`, fix CI test execution | M4 | Survey 3 |
| F21 | Doctor Health Check SSoT | Unify doctor implementations into `video_intake_core.cli.doctor`, fix failure counting in `scripts/doctor.sh` | M4 | Survey 3 |
| F22 | Elite Test Suite (>95% Coverage) | Create `tests/conftest.py`, build comprehensive unit/integration test suites for context, visual, audio, transcription, storage, cli | M4 | Survey 3 |
| F23 | Strict Typing & Linting | Ensure 0 ruff errors and strict typing (`mypy` clean without errors) | M4 | Survey 3 |
| F24 | World-Class Visual README & Badges | CI status, coverage %, python versions, license, ruff badges | M5 | Survey 3 |
| F25 | 3 Mermaid Architecture Diagrams | 2-phase flow, security isolation, storage & artifact hierarchy diagrams | M5 | Survey 3 |
| F26 | Formal JSON Data Schemas Documentation | Document 10 schemas in `schemas/` with field definitions, types, constraints, examples | M5 | Survey 3 |
| F27 | Documentation Drift Pruning & Integration Guides | Quickstart, Agent Integration walk-throughs, remove ClamAV/quarantine doc drift | M5 | Survey 3 |
| F28 | E2E 4-Tier Test Infrastructure & Verification | Independent opaque-box test runner + 4-tier test suite (Tiers 1-4) + Tier 5 adversarial hardening | E2E / Final | Survey 1, 2, 3 |

---

## Milestones

| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| E2E | E2E Testing Track Orchestrator | Design & build 4-tier opaque-box test runner, infrastructure, and test cases covering all 28 features -> publish `TEST_READY.md` | none | PLANNED |
| M1 | High-Performance Ingestion & Extraction Engine (R1) | Features F1, F2, F3, F4, F5, F6: Sub-300ms inspect, VideoInfo restore, URL normalizers, direct audio, concurrent batch engine, pipeline unification | none | PLANNED |
| M2 | Universal Agent Experience & Scaffolding (R2) | Features F7, F8, F9, F10, F11, F12: Canonical SKILL.md, Cursor adapter, Codex fix, Hermes fix, AGY routing, install.sh, CLI interactive 2-phase, dynamic scaffolding | none | PLANNED |
| M3 | Hardened Security & Strict Memory Isolation (R3) | Features F13, F14, F15, F16, F17: Socket DNS SSRF defense, gateway wiring, path traversal containment, prompt injection boundaries, ~/.video-intake/ isolation, delete root jobs.db | none | PLANNED |
| M4 | Code Quality, Strict Typing, CI/CD & Test Suite (>95% cov) (R4) | Features F18, F19, F20, F21, F22, F23: CLI refactor to modular files, remove coverage omits, UV dependency-groups, doctor SSoT, >95% test coverage, strict typing | M1, M2, M3 | PLANNED |
| M5 | World-Class Developer Documentation & Architecture Diagrams (R5) | Features F24, F25, F26, F27: README badges, 3 Mermaid diagrams, formal JSON schemas catalog, quickstart, doc drift elimination | M1, M2, M3 | PLANNED |
| Final | Final E2E Verification & Adversarial Hardening | Feature F28: Pass 100% E2E tests (Tiers 1-4), Challenger adversarial coverage hardening (Tier 5), doctor 100% healthy | E2E, M1-M5 | PLANNED |

---

## Interface Contracts

### Acquisition & Inspection ↔ Engine
- `detect_source(url_or_path: str) -> SourceType | None`
- `resolve_url(url: str, follow_redirects: bool = True) -> ResolvedURL`
- `inspect_video(target: str, timeout: float = 10.0) -> VideoInfo`
  - `VideoInfo`: must expose `title`, `duration`, `width`, `height`, `fps`, `streams`, `video_codec`, `audio_codec`, `format_name`, `file_size_bytes`.

### Security ↔ Acquisition & Orchestrator
- `validate_video_url(url: str) -> ValidationResult`
  - Checks scheme (`http`, `https`), resolves DNS via `socket.getaddrinfo`, inspects all IPs against private/loopback/link-local/metadata networks, validates target host against SSRF blocklist.
- `validate_local_file(path: str | Path, allowed_roots: list[Path] | None = None) -> ValidationResult`
  - Resolves path, verifies existence, forbids system directories (`/etc`, `/proc`, `/sys`, `/dev`, `/root`), verifies containment.
- `sanitize_path(base_dir: Path, target: str | Path) -> Path`
  - Strict traversal prevention ensuring resolved path is relative to `base_dir`.
- `sanitize_for_prompt(text: str) -> str` and `wrap_for_llm(tag: str, content: str) -> str`
  - Escapes instruction injection tokens, encloses content inside explicit XML boundaries (`<video_transcript>`, `<ocr_extracted_content>`).

### Batch Processing ↔ Job Manager
- `run_batch(manifest_path: Path, max_workers: int = 4, output_dir: Path = ...) -> BatchResult`
  - Spawns `ThreadPoolExecutor(max_workers=max_workers)`, records jobs in `~/.video-intake/jobs.db`, returns overall status.

### CLI ↔ Modular Subcommands
- `packages/video_intake_core/cli/__init__.py`: Clean dispatcher delegating to `cli.doctor.run_doctor`, `cli.extract.run_extract`, `cli.batch.run_batch`, `cli.status.run_status`, `cli.artifacts.run_artifacts`, `cli.cleanup.run_cleanup`, `cli.export.run_export`, `cli.models.run_models`, `cli.config_cmd.run_config`, `cli.proposals.run_proposals`, `cli.memory.run_memory`, `cli.interactive.run_interactive`.
- Menu parsing: Single canonical parser `parse_menu_selection(raw: str) -> set[int]` in `cli/menu.py`.

---

## Code Layout

- Core Library: `packages/video_intake_core/`
  - `acquisition/`: Source detection, platform normalizers, redirect resolver.
  - `inspection/`: Fast ffprobe metadata extractor, lazy yt-dlp inspector.
  - `audio/`: Direct audio extraction, normalization, slicing.
  - `transcription/`: Platform subtitle parser, Whisper fallback.
  - `visual/`: Keyframe extraction, scene detection.
  - `ocr/`: Tesseract wrapper, text filter.
  - `context/`: Audio context, visual context, chapters, summarization, prompt boundary wrapping.
  - `storage/`: Artifact manifest, directory layout, path containment.
  - `memory/`: SQLite memory provider targeting `~/.video-intake/memory.db`.
  - `jobs/`: SQLite job queue manager targeting `~/.video-intake/jobs.db`.
  - `security/`: SSRF socket validator, path traversal defense, prompt injection sanitizer.
  - `cli/`: Modular command handlers (`doctor.py`, `extract.py`, `batch.py`, `interactive.py`, `proposals.py`, etc.).
- Schemas: `packages/video_intake_schemas/` & `packages/video_intake_core/schemas/`
- Agent Adapters: `adapters/hermes/`, `adapters/agy/`, `adapters/claude-code/`, `adapters/opencode/`, `adapters/codex/`, `adapters/cursor/`.
- Root Specification: `/srv/video-intake-knowledge/SKILL.md` (SSoT).
- Testing: `/srv/video-intake-knowledge/tests/` (unit, integration, security, contract, e2e).
