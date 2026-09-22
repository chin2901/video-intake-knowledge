# Handoff Report: Explorer 3 Survey (R3, R4, R5)

## 1. Observation
1. **SSRF Bypass in URL Validation**:
   - In `packages/video_intake_core/utils/validation.py` lines 30–40 and `packages/video_intake_core/security/__init__.py` lines 80–86, `_is_blocked_ip(host)` parses host with `IPv4Address(host)` and does no DNS resolution.
   - Tested command:
     `/srv/video-intake-knowledge/venv/bin/python3 -c "from video_intake_core.utils.validation import is_safe_url; print(is_safe_url('http://127.0.0.1.nip.io/video.mp4')); print(is_safe_url('http://0177.0000.0000.0001/video.mp4')); print(is_safe_url('http://2130706433/video.mp4'))"`
   - Verbatim output:
     `True`
     `True`
     `True`
2. **Security Gateway Detachment in Pipeline**:
   - `packages/video_intake_core/orchestrator.py` lines 126–135 directly passes `target` URL to `subprocess.run(["yt-dlp", ..., target])` without any call to `validate_url` or `validate_video_url`.
   - `packages/video_intake_core/orchestrator.py` lines 106–120 directly executes `shutil.copy2(video_file, dest_video)` on any local file path matching `Path(target).exists()` without calling `validate_local_file` or `sanitize_path`.
   - `packages/video_intake_core/utils/fs.py`: `sanitize_path` (line 73) is imported in `utils/__init__.py` and `security/__init__.py` but never called in any operational module (`grep_search` returned 0 caller matches).
   - `packages/video_intake_core/security/__init__.py`: `validate_local_file` (line 165) has 0 caller matches across the entire repository.
3. **SQLite Database in Working Tree**:
   - Found `/srv/video-intake-knowledge/jobs.db` on disk (28,672 bytes).
   - Python inspection command:
     `sqlite3.connect('/srv/video-intake-knowledge/jobs.db').execute("SELECT count(*) FROM jobs").fetchone()`
   - Verbatim result: `(22,)`
   - In `packages/video_intake_core/jobs/__init__.py`:
     - Line 44: `def __init__(self, db_path: str | Path = "jobs.db") -> None:`
     - Line 837: `_DEFAULT_DB_PATH = "jobs.db"`
4. **Test Suite Coverage & Omission**:
   - Executed full test coverage:
     `/srv/video-intake-knowledge/venv/bin/pytest --cov=video_intake_core --cov-report=term --cov-config=/dev/null`
   - Verbatim result:
     `TOTAL: 6169 statements, 3869 missed, 37% coverage`
     `video_intake_core/context/__init__.py: 1541 statements, 1458 missed, 5% coverage`
   - In `pyproject.toml` line 149:
     `omit = ["**/__init__.py", "**/cli.py", "**/__main__.py"]`
     This masked almost all module implementations because all core logic resides in `__init__.py` files.
5. **CI/CD Workflow Breakage**:
   - `.github/workflows/ci.yml` contains lines 52, 120, 190, 225, 260 running `uv sync --group dev`, `core`, `build`, `full`, `docs`.
   - Executed: `uv sync --dry-run --group core`
   - Verbatim output:
     `error: Group core is not defined in the project's dependency-groups table`
6. **Doctor Script False Positive**:
   - Executed `bash ./scripts/doctor.sh`.
   - Verbatim output showed:
     `✗ openai-whisper`
     `✗ pytesseract`
     `✗ scenedetect`
     `✗ questionary`
     followed by:
     `Estado: ✓ Saludable`
     `Fallos: 0`
   - In `scripts/doctor.sh` lines 184–190, the loop prints `  ✗ {pkg_name}` but never calls `check_fail` or increments `FAILURES`.
7. **Documentation State**:
   - `grep -r "```mermaid" /srv/video-intake-knowledge` returned 0 results.
   - `README.md` contains 0 badge tags.
   - `docs/security-model.md` lines 49–50 refers to ClamAV scanning and `quarantine/` which do not exist in the codebase.

## 2. Logic Chain
1. From Observation 1 and 2, the security functions (`validate_url`, `validate_local_file`, `sanitize_path`) suffer from both internal algorithmic gaps (lack of DNS resolution and octal/decimal IP normalization) and systemic architectural detachment (neither the orchestrator nor the storage pipeline invokes them). Therefore, user-supplied inputs can cause SSRF via `yt-dlp` or local arbitrary file exposure via `shutil.copy2`.
2. From Observation 3, `JobManager` defaults to `"jobs.db"` in the current working directory, which caused `jobs.db` with 22 records to be created in the git project root. This directly violates the acceptance criterion that the git working tree must remain 100% free of SQLite databases.
3. From Observation 4, real test coverage is 37%, and the core 3,342-line knowledge extraction engine (`context`) has only 5% coverage. The prior reported 47% was artificially produced by an `omit = ["**/__init__.py"]` filter in `pyproject.toml`. This is 58 percentage points below the required >95% acceptance criterion.
4. From Observation 5, `ci.yml` relies on `uv sync --group <name>`, whereas `pyproject.toml` defines optional dependencies under PEP 621 `[project.optional-dependencies]`. Thus, any automated CI run on GitHub Actions will abort with an unhandled error.
5. From Observation 6, `doctor.sh` provides false assurance because its package checking loop bypasses the failure counter, masking missing dependencies while reporting a clean health state.
6. From Observation 7, the repository lacks visual and formal documentation (no badges, no Mermaid diagrams, undocumented schemas) and contains speculative documentation for non-existent components.

## 3. Caveats
- No changes to source code were executed during this investigation (read-only per Constitution and role instructions).
- Remote platform tests (e.g. active YouTube, TikTok downloads) were not executed to prevent network dependency interference during the survey.
- Fuzzing scripts were not yet generated; empirical verification was performed via direct script invocations with known bypass payloads.

## 4. Conclusion
The repository possesses solid foundational concepts and utilities, but has four critical structural issues:
1. **Security Detachment**: Security guards exist as orphaned utilities rather than active enforcement barriers at the pipeline entrance.
2. **Repository Pollution**: SQLite storage defaults to relative paths in cwd rather than `~/.video-intake/`.
3. **QA Deficit & CI Failure**: Real test coverage is 37% (masked by configuration) and GitHub Actions workflows are currently broken due to configuration syntax mismatch.
4. **Documentation Incompleteness**: Lack of visual architecture diagrams, missing badges, undocumented schemas, and presence of speculative features in docs.

Immediate structural elevation is required across R3, R4, and R5 to reach the 100k+ star standard.

## 5. Verification Method
To independently verify the observations:
1. **Verify SSRF bypass**:
   ```bash
   /srv/video-intake-knowledge/venv/bin/python3 -c "
   from video_intake_core.utils.validation import is_safe_url
   assert is_safe_url('http://127.0.0.1.nip.io/video.mp4') == True
   assert is_safe_url('http://0177.0000.0000.0001/video.mp4') == True
   "
   ```
2. **Verify root jobs.db**:
   ```bash
   test -f /srv/video-intake-knowledge/jobs.db && echo "jobs.db exists in root"
   ```
3. **Verify real test coverage**:
   ```bash
   /srv/video-intake-knowledge/venv/bin/pytest --cov=video_intake_core --cov-report=term --cov-config=/dev/null
   ```
4. **Verify CI failure**:
   ```bash
   uv sync --dry-run --group core
   ```
5. **Verify doctor.sh false reporting**:
   ```bash
   bash ./scripts/doctor.sh | grep -E "✗|Estado"
   ```
