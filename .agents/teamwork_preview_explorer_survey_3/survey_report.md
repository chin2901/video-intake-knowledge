# Survey Report: Security, Isolation, QA, Testing & Documentation (R3, R4, R5)
**Explorer 3 — video-intake-knowledge Engineering Elevation**  
**Date**: 2026-09-21 | **Working Directory**: `/srv/video-intake-knowledge/.agents/teamwork_preview_explorer_survey_3`  
**Constitution & Methodology**: Tony's Problem-Solving Principles (`/home/aibos/AGENTS.md`) — Ground Truth, SSoT, Radical Simplicity, Cero Especulación, Cero Chapuzas.

---

## 1. Executive Summary

An exhaustive, empirical, read-only investigation of `/srv/video-intake-knowledge` was conducted across Requirements **R3** (Security & Isolation), **R4** (QA, Testing & CI/CD), and **R5** (World-Class Documentation).

### Primary Findings
1. **Critical SSRF Bypasses & Security Pipeline Detachment (R3)**:
   - The SSRF protection (`_is_blocked_ip`) checks only raw string IP literals. Any hostname that resolves to loopback/private ranges (e.g. `127.0.0.1.nip.io`, `localtest.me`), or non-canonical IP formats (octal `0177.0.0.1`, integer `2130706433`), returns `safe = True`.
   - More critically: **neither `validate_url` nor `validate_video_url` is called in the execution pipeline** before passing target URLs to `yt-dlp` (`orchestrator.py` lines 126–135). Security utilities were written in isolation but detached from the runtime.
   - Similarly, `validate_local_file` and `sanitize_path` are defined but **never called anywhere in the codebase**. Local file intake resolves arbitrary user paths without containment checks, permitting exfiltration of `/etc/passwd` if operation 1 (video download/preservation) is triggered.
   - Neither `sanitize_for_prompt` nor `PromptInjectionProtection` is integrated into transcript/OCR knowledge generation (`context/__init__.py`), allowing malicious video subtitles to enter LLM agent contexts raw.
2. **Git Working Tree Pollution & Inconsistent Memory Isolation (R3)**:
   - A 28 KB SQLite database `jobs.db` containing 22 jobs was detected directly in the project root (`/srv/video-intake-knowledge/jobs.db`). `JobManager` in `packages/video_intake_core/jobs/__init__.py` defaults to `db_path="jobs.db"`, violating the requirement that the git working tree remains 100% free of SQLite databases.
   - Documentation (`docs/architecture.md`, `examples/memory-integration/README.md`) still refers to `./video_intake_memory.db` and `/srv/video-intake-knowledge/memory/memory.db`.
3. **Severe Test Coverage Deficit & Broken CI Workflows (R4)**:
   - Measured across the entire package, **global pytest coverage is only 37%** (3,869 missed statements out of 6,169). The core knowledge engine `context/__init__.py` (3,342 lines) has only **5% coverage**; `visual` has 11%, `transcription` 12%, `audio` 23%, `ocr` 26%.
   - `pyproject.toml` contained `omit = ["**/__init__.py"]` under `[tool.coverage.run]`, which masked 90% of the codebase because all package logic was placed in `__init__.py` files.
   - CI/CD workflow `.github/workflows/ci.yml` is **broken**: it executes `uv sync --group core/build/docs/full`, but `pyproject.toml` defines dependencies under `[project.optional-dependencies]`, causing instant failure (`error: Group core is not defined`).
   - `mypy` is not installed in the local virtual environment.
   - Doctor scripts suffer from SSoT fragmentation: `cli/__init__.py` has one implementation, `cli/doctor.py` has a second, and `./scripts/doctor.sh` is a third that prints `✗` for missing packages but never increments failures, falsely outputting `Fallos: 0` and `✓ Saludable`.
4. **Documentation Deficits & Hallucinations (R5)**:
   - `README.md` has **0 badges** and **0 Mermaid diagrams**. There is not a single Mermaid diagram in the entire repository.
   - 10 formal JSON schemas exist in `packages/video_intake_core/schemas/` but are completely undocumented.
   - Documentation hallucination: `docs/security-model.md` and `docs/architecture.md` claim support for ClamAV scanning and a `quarantine/` folder, neither of which exists in code.

---

## 2. Security & Isolation Deep Dive (R3)

### 2.1 SSRF Defenses & URL Validation

#### Empirical Vulnerabilities Verified
In `packages/video_intake_core/utils/validation.py` (lines 30–40) and `packages/video_intake_core/security/__init__.py` (lines 80–86, 374–440), SSRF validation relies on:
```python
def _is_blocked_ip(host: str) -> bool:
    host = host.lower().rstrip(".")
    try:
        addr = IPv4Address(host)
        if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_unspecified:
            return True
        return any(addr in net for net in _SSRF_BLOCKED_NETWORKS)
    except ValueError:
        pass
    return False
```
Because DNS resolution is never performed on non-IP hostnames and non-canonical IP encodings fail `IPv4Address` parsing:
- `http://127.0.0.1.nip.io/video.mp4` -> Evaluated as `safe = True` (DNS rebinding / alias bypass).
- `http://0177.0000.0000.0001/video.mp4` -> Evaluated as `safe = True` (Octal bypass).
- `http://2130706433/video.mp4` -> Evaluated as `safe = True` (Integer representation of `127.0.0.1`).
- `http://metadata.google.internal/video.mp4` -> In `utils/validation.py`, evaluated as `safe = True`.
- IPv6 loopback (`[::1]`) is handled inconsistently across the two validation modules.

#### Pipeline Detachment (The "Ghost Defense" Anti-Pattern)
A grep across `packages/video_intake_core` reveals that **`validate_url` or `validate_video_url` is NEVER called by the orchestrator or acquisition pipelines**.
In `packages/video_intake_core/orchestrator.py`:
```python
94:  for idx, src in enumerate(sources, 1):
95:      target = str(src.get("resolved_url") or src.get("url") or "")
...
126:     elif not is_local and target.startswith("http"):
127:         print("[1/5] Adquiriendo vídeo con yt-dlp...")
128:         out_tmpl = str(job_dir / f"{title}_%(id)s.%(ext)s")
129:         cmd = [
130:             "yt-dlp",
131:             "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
132:             "--no-playlist",
133:             "-o", out_tmpl,
134:             target,
135:         ]
136:         res = subprocess.run(cmd, capture_output=True, text=True)
```
Target URLs are passed straight to `yt-dlp` without any scheme, host, or SSRF inspection.

### 2.2 Path Traversal Defenses in Media & Cache Storage

#### Unused Defense Functions
- `packages/video_intake_core/utils/fs.py`: `sanitize_path(base: Path, user_path: str | Path) -> Path` (lines 73–107) is well written, but **never called anywhere in the entire codebase**.
- `packages/video_intake_core/security/__init__.py`: `validate_local_file(...)` (lines 165–229) contains checks against sensitive directories (`/etc`, `/proc`, `/sys`, `/dev`, `/root`, `/var/run`), but **is never called anywhere in the codebase**.

#### Vulnerable Ingestion of Local Files
In `packages/video_intake_core/orchestrator.py` lines 106–125:
```python
106: if is_local or (target.startswith("file://") or Path(target).exists()):
107:     local_candidate = Path(target.replace("file://", "")).resolve()
108:     if local_candidate.exists() and local_candidate.is_file():
109:         video_file = local_candidate
110:         is_local = True
116:     if 1 in operations:
117:         dest_video = job_dir / video_file.name
118:         if dest_video != video_file and not dest_video.exists():
119:             shutil.copy2(video_file, dest_video)
```
If an untrusted caller supplies `target: "/etc/passwd"` or `file:///etc/shadow` and requests operation 1, the orchestrator copies the file directly into `job_dir` as an artifact!

#### Artifact Storage Path Traversal Vulnerability
In `packages/video_intake_core/storage/__init__.py`:
- Line 183: `def get_job_dir(self, job_id: str) -> Path:` concatenates `self._jobs_dir / job_id` without checking if `job_id` contains `../`.
- Line 196: `save_artifact(self, job_id, artifact_type, content, filename=None)` accepts a custom `filename` and constructs `dest = job_dir / filename` without path traversal sanitization or containment checks.

### 2.3 Prompt & Subtitle Injection Sanitization

- `packages/video_intake_core/security/__init__.py` defines `sanitize_for_prompt()` and `PromptInjectionProtection`, and tests them in `tests/security/test_security.py`.
- However, **neither is called during actual knowledge extraction**.
- In `packages/video_intake_core/context/__init__.py`:
  - `generate_audio_context(transcript_segments, full_text, ...)` processes raw text directly into summaries, topics, and chapters.
  - No sanitization markers, XML boundary wrapping (`wrap_for_llm`), or injection stripping occur.
  - When an AI agent consumes `audio_context.md` or `extracted_knowledge.md`, any prompt injection embedded in subtitles is executed in the agent's context.

### 2.4 SQLite & Working Tree Cleanliness

- **Evidence of Working Tree Pollution**:
  - Found `/srv/video-intake-knowledge/jobs.db` (28,672 bytes) in the git root directory.
  - Direct inspection with python sqlite3 revealed table `jobs` with **22 recorded jobs**.
  - Root Cause: `packages/video_intake_core/jobs/__init__.py`:
    - Line 44: `def __init__(self, db_path: str | Path = "jobs.db") -> None:`
    - Line 724: `def get_default_manager(db_path: str | Path = "jobs.db") -> JobManager:`
    - Line 837: `_DEFAULT_DB_PATH = "jobs.db"`
    - Line 307 of `orchestrator.py`: `resolved_db = db_path or "jobs.db"`
  - Whenever CLI or orchestrator runs, it creates `jobs.db` in `Path.cwd()`, polluting the user's workspace.
- **Memory Provider Isolation**:
  - `packages/video_intake_core/memory/__init__.py` correctly uses `_default_memory_path()` targeting `~/.video-intake/memory.db`.
  - However, documentation (`docs/architecture.md:227`, `docs/memory-integration.md:57`, `examples/memory-integration/README.md:15`) still instructs users to use `./video_intake_memory.db` or `/srv/video-intake-knowledge/memory/memory.db`.
  - Git history previously had `.memory/` committed (`git log --all --name-only | grep .memory`).

---

## 3. QA, Testing & CI/CD Deep Dive (R4)

### 3.1 Test Suite & Coverage Status

#### Global Coverage Reality
Running `pytest --cov=video_intake_core`:
```
Name                                                   Stmts   Miss  Cover
--------------------------------------------------------------------------
video_intake_core/__init__.py                              5      0   100%
video_intake_core/acquisition/__init__.py                161     29    82%
video_intake_core/artifacts/__init__.py                   97     67    31%
video_intake_core/audio/__init__.py                      163    126    23%
video_intake_core/cli/__init__.py                        599    283    53%
video_intake_core/cli/__main__.py                          5      5     0%
video_intake_core/cli/artifacts.py                        45     36    20%
video_intake_core/cli/cleanup.py                          54     34    37%
video_intake_core/cli/config_cmd.py                       48     40    17%
video_intake_core/cli/doctor.py                           81     48    41%
video_intake_core/cli/export.py                           55     44    20%
video_intake_core/cli/extract.py                          37     29    22%
video_intake_core/cli/memory.py                           61     29    52%
video_intake_core/cli/menu.py                             29      7    76%
video_intake_core/cli/models.py                           45     36    20%
video_intake_core/cli/proposals.py                        76     21    72%
video_intake_core/cli/status.py                           50     43    14%
video_intake_core/context/__init__.py                   1541   1458     5%  <-- 3342 lines of core logic!
video_intake_core/inspection/__init__.py                 151     67    56%
video_intake_core/jobs/__init__.py                       276    101    63%
video_intake_core/memory/__init__.py                     217     18    92%
video_intake_core/ocr/__init__.py                        182    135    26%
video_intake_core/orchestrator.py                        354    127    64%
video_intake_core/policies/__init__.py                   173     79    54%
video_intake_core/schemas/__init__.py                     37      9    76%
video_intake_core/schemas/job.py                         133     30    77%
video_intake_core/schemas/source.py                       52     10    81%
video_intake_core/security/__init__.py                   184     87    53%
video_intake_core/storage/__init__.py                    332    163    51%
video_intake_core/transcription/__init__.py              461    404    12%
video_intake_core/utils/__init__.py                       79     31    61%
video_intake_core/utils/fs.py                             54     17    69%
video_intake_core/utils/text.py                           84     63    25%
video_intake_core/utils/validation.py                     74     38    49%
video_intake_core/visual/__init__.py                     174    155    11%
--------------------------------------------------------------------------
TOTAL                                                   6169   3869    37%
```
- **Total Real Coverage: 37%** (Target: >95%).
- **Gap: 58 percentage points below requirement**.
- `pyproject.toml` lines 146–150 contained:
  ```toml
  [tool.coverage.run]
  source = ["video_intake_core"]
  branch = true
  omit = ["**/__init__.py", "**/cli.py", "**/__main__.py"]
  ```
  This configuration omitted virtually the entire package from coverage calculation, producing a deceptive 47% reported figure while hiding the un-tested 3,869 lines.

#### Test Quality & Test Smells
- **No shared fixture suite**: `tests/conftest.py` does not exist.
- **Trivial tests**: `tests/unit/test_cli.py` tests `assert callable(run_doctor)`, `assert callable(cleanup_command)`.
- **Tautology assertions**: `tests/security/test_security.py` line 79:
  `assert result is False or result is True  # depends on implementation`
- **Resource leaks**: `ResourceWarning: unclosed database in <sqlite3.Connection object>` triggered during test runs due to missing `db.close()` in fixtures.

### 3.2 Linting & Typing Status

- **Ruff**: `ruff check .` passes with 0 errors.
- **Typing / Mypy**:
  - `mypy` is not installed in `/srv/video-intake-knowledge/venv/bin/mypy`.
  - `pyproject.toml` configures `[tool.mypy]` with `strict = true`, but running it is currently impossible without installing the dependency.

### 3.3 CI/CD Workflows (`.github/workflows`)

- `.github/workflows/ci.yml` contains broken commands:
  - Line 52: `uv sync --group dev`
  - Line 120: `uv sync --group core`
  - Line 190: `uv sync --group build`
  - Line 225: `uv sync --group full`
  - Line 260: `uv sync --group docs`
- In `pyproject.toml`, dependencies are specified under `[project.optional-dependencies]` (using PEP 621 extras: `core`, `full`, `development`), NOT under `[dependency-groups]`.
- Testing `uv sync --dry-run --group core` in terminal failed with:
  `error: Group core is not defined in the project's dependency-groups table`
- Result: **All GitHub Actions jobs (`unit`, `build`, `integration`, `docs`) will fail on execution**.
- In addition, `tool.uv.dev-dependencies` in `pyproject.toml` triggers deprecation warnings in UV.

### 3.4 Doctor Scripts Diagnostic

There are three distinct doctor implementations that violate SSoT:
1. `video_intake_core.cli.__init__:cmd_doctor`: Checks python, ffmpeg, ffprobe, yt-dlp, tesseract, disk_space, write_permission, config.
2. `video_intake_core.cli.doctor:run_doctor`: Checks python version, PyYAML, sqlite3, json, pathlib, dataclasses, package version.
3. `./scripts/doctor.sh`: Shell script checking system tools and python packages.
   - **Critical Bug in `scripts/doctor.sh`**:
     Lines 184–190 iterate over python packages and print `  ✗ {pkg_name}` when `openai-whisper`, `pytesseract`, `scenedetect`, or `questionary` fails to import.
     However, it never calls `check_fail` or `check_warn`, leaving `FAILURES=0`.
     It finishes by announcing `Estado: ✓ Saludable, Fallos: 0` despite 4 failed packages!

---

## 4. World-Class Documentation Survey (R5)

### 4.1 README & Visual Standard
- **Badges**: 0 badges present in `README.md`. Missing build status, coverage %, license, python versions, ruff, stars.
- **Mermaid Diagrams**: 0 Mermaid diagrams in `README.md` or any docs file.
- **CLI Quickstart**: Contains high-level commands, but lacks concrete output examples, edge case guidance, and agent integration walk-throughs.

### 4.2 Formal Schema Specifications
- 10 JSON Schema files reside in `packages/video_intake_core/schemas/`:
  - `artifact_manifest.json`
  - `audio_context.json`
  - `build_proposal.json`
  - `job.json`
  - `knowledge_extraction.json`
  - `memory_bank.json`
  - `memory_entry.json`
  - `ocr_block.json`
  - `source.json`
  - `transcript_segment.json`
  - `visual_context.json`
- None of these are documented with field-level descriptions, constraints, examples, or entity relationship diagrams in `docs/` or `README.md`.

### 4.3 Documentation Drift vs Ground Truth
- `docs/security-model.md` lines 49–50 claims: `security.scan_downloaded_files permite escanear con ClamAV si está disponible. Los archivos sospechosos se aíslan en quarantine/`.
- Reality: ClamAV and `quarantine/` are 100% nonexistent in the codebase.
- `docs/architecture.md` line 227 claims: `SQLite en ./video_intake_memory.db`.
- Reality: Core memory provider defaults to `~/.video-intake/memory.db`.

---

## 5. Concrete Gap Matrix against Acceptance Criteria

| Requirement | Acceptance Criteria | Current Ground Truth | Status | Primary Remediation Required |
|---|---|---|---|---|
| **R3: SSRF** | All fuzzing and simulated SSRF attacks neutralized | Bypassed via DNS names (`127.0.0.1.nip.io`), octal/decimal IPs. `validate_url` is never called before `yt-dlp`. | ❌ **FAIL** | Implement socket DNS resolution + IP address range validation; invoke validation unconditionally before network calls. |
| **R3: Path Traversal** | Path traversal attacks neutralized in media/cache | `sanitize_path` and `validate_local_file` are never called. Arbitrary local file copy allowed in `orchestrator.py`. | ❌ **FAIL** | Integrate `sanitize_path` and `validate_local_file` into `orchestrator.py` and `storage/__init__.py`. |
| **R3: Injection** | Prompt/subtitle injections neutralized | `sanitize_for_prompt` never called in context generation or proposal scaffolding. | ❌ **FAIL** | Apply `sanitize_for_prompt` and LLM wrapper markers to transcripts and OCR text before exposing to agents. |
| **R3: Memory Isolation** | Git tree 100% free of SQLite `.db`, `.memory/`, or cache | `/srv/video-intake-knowledge/jobs.db` created in root (22 jobs). `JobManager` defaults to `"jobs.db"`. | ❌ **FAIL** | Point `JobManager` default to `~/.video-intake/jobs.db`; delete root `jobs.db`; update docs. |
| **R4: Coverage** | Global pytest coverage > 95% demonstrated | Global coverage is **37%** (masked as 47% via `omit = ["**/__init__.py"]`). `context` is at 5%. | ❌ **FAIL** | Remove deceptive coverage omit; create `tests/conftest.py`; build comprehensive unit/integration test suites for `context`, `visual`, `audio`, `transcription`. |
| **R4: Linting & Typing** | 0 ruff errors, 0 typing errors | `ruff` passes (0 errors). `mypy` not installed in venv. | ⚠️ **PARTIAL** | Install `mypy` and verify strict type compliance across all packages. |
| **R4: CI/CD** | Multi-platform CI/CD workflows functional | `.github/workflows/ci.yml` crashes due to undefined `dependency-groups`. | ❌ **FAIL** | Align `pyproject.toml` `[dependency-groups]` with `ci.yml` invocations. |
| **R4: Doctor** | Health check scripts 100% healthy (0 failures) | `cli` has 2 conflicting doctor commands; `doctor.sh` silently ignores missing packages and reports 0 failures. | ❌ **FAIL** | Unify doctor into single SSoT engine; fix failure counting and exit codes in `doctor.sh`. |
| **R5: Documentation** | World-class README with badges, Mermaid diagrams, formal schemas | 0 badges, 0 Mermaid diagrams, undocumented JSON schemas, ClamAV doc drift. | ❌ **FAIL** | Overhaul `README.md` with badges, 3 Mermaid architecture diagrams, data schema catalog, and prune doc drift. |

---

## 6. Actionable Elevation Plan & Architectural Recommendations

Applying Tony's Problem-Solving Methodology ("Menos es Más", SSoT, Cero Parches, Protección Nativa):

1. **Unify and Enforce Security at the Pipeline Gateways**:
   - Create a single canonical `validate_and_resolve_source(source: dict | str)` entrypoint in `acquisition/`.
   - Perform deterministic SSRF validation: extract host, resolve DNS addresses via `socket.getaddrinfo`, inspect every resolved IPv4/IPv6 against `ipaddress.ip_address(addr).is_private or is_loopback or is_link_local`.
   - Wire `validate_local_file` to strictly block access outside permitted workspaces or to sensitive paths.
2. **Eliminate Repository SQLite Pollution**:
   - Change `_DEFAULT_DB_PATH` in `video_intake_core/jobs/__init__.py` to `Path.home() / ".video-intake" / "jobs.db"`.
   - Remove `/srv/video-intake-knowledge/jobs.db` from root.
   - Synchronize all docs and examples to reference `~/.video-intake/`.
3. **Harmonize UV Dependency Groups & Fix CI/CD**:
   - Update `pyproject.toml` to define modern `[dependency-groups]` matching `ci.yml` (`dev`, `core`, `full`, `docs`, `build`).
   - Remove deprecated `tool.uv.dev-dependencies`.
4. **Unify Doctor Diagnostics (SSoT)**:
   - Make `video_intake_core.cli.doctor` the sole engine for health checks.
   - Have `cmd_doctor` and `doctor.sh` call this single engine.
   - Fix `scripts/doctor.sh` so missing dependencies properly trigger `FAILURES` and non-zero exit codes.
5. **Elevate Test Coverage from 37% to >95%**:
   - Create `tests/conftest.py` with reusable mock fixtures for `ffprobe`, `ffmpeg`, `yt-dlp`, `whisper`, and `tesseract`.
   - Add parameterized unit tests for `context/__init__.py` (covering all 15 knowledge extractors).
   - Add comprehensive tests for `transcription`, `visual`, `audio`, and `storage`.
   - Remove the deceptive `omit = ["**/__init__.py"]` from `pyproject.toml`.
6. **Elevate Documentation to 100k+ Star Tier**:
   - Add status badges (CI, Coverage, Python, License, Ruff).
   - Add Mermaid diagrams for:
     1. End-to-End 2-Phase Flow (Inspection -> Extraction -> Routing).
     2. Security & Isolation Architecture (SSRF, Path Traversal, Memory Isolation).
     3. Storage & Artifact Hierarchy.
   - Add a formal Data Contracts section documenting the 10 JSON schemas with field definitions.
   - Clean up speculative doc entries (ClamAV, `quarantine/`).
