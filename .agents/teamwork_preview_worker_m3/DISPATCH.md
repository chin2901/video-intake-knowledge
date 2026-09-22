# Task Assignment: Worker M3 (Hardened Security & Strict Memory Isolation - R3)

## Context
- Project Root: `/srv/video-intake-knowledge`
- Working Directory: `/srv/video-intake-knowledge/.agents/teamwork_preview_worker_m3`
- Authoritative Requirements: `/srv/video-intake-knowledge/.agents/ORIGINAL_REQUEST.md` (MUST read in full)
- System Constitution: `/home/aibos/AGENTS.md` (MUST adhere strictly)
- Scope & Architecture: `/srv/video-intake-knowledge/.agents/PROJECT.md`
- Survey Findings: Read `/srv/video-intake-knowledge/.agents/teamwork_preview_explorer_survey_3/survey_report.md`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Write Ownership
You EXCLUSIVELY own and may modify:
- `packages/video_intake_core/security/`
- `packages/video_intake_core/utils/validation.py`
- `packages/video_intake_core/utils/fs.py`
- `packages/video_intake_core/context/` (prompt boundary wrapping & subtitle injection sanitization)
- `packages/video_intake_core/storage/` (containment & path sanitization)
- `packages/video_intake_core/jobs/` (default db path to `~/.video-intake/jobs.db`)
- `packages/video_intake_core/memory/` (memory isolation enforcement)
- Remove `/srv/video-intake-knowledge/jobs.db` from repository root
DO NOT modify files outside your ownership boundary.

## Objectives & Implementation Directives
1. **Deterministic SSRF Prevention (F13)**:
   - In `packages/video_intake_core/security/__init__.py` and `utils/validation.py`:
     - Implement comprehensive socket-level DNS resolution using `socket.getaddrinfo(host, None)`.
     - Parse every resolved IP address using `ipaddress.ip_address(addr)` (both IPv4 and IPv6).
     - Deterministically block:
       - Loopback: `127.0.0.0/8`, `::1`
       - Private: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `fc00::/7`
       - Link-local: `169.254.0.0/16`, `fe80::/10`
       - Cloud metadata: `169.254.169.254`, `metadata.google.internal`
       - Carrier-grade NAT: `100.64.0.0/10`
       - Unspecified / broadcast: `0.0.0.0`, `255.255.255.255`
     - Neutralize non-canonical encodings: octal (e.g. `0177.0.0.1`), decimal integer (`2130706433`), hexadecimal, and DNS aliases/rebinding (`*.nip.io`, `localtest.me`).
2. **Security Gateway Enforcement (F14)**:
   - Wire `validate_video_url` into `acquisition` and `orchestrator.py` so NO target URL is ever passed to `yt-dlp` or any network call without passing SSRF validation.
3. **Path Traversal Defenses in File Ingestion & Storage (F15)**:
   - Wire `validate_local_file` and `sanitize_path` into `orchestrator.py` local file intake and `storage/__init__.py` artifact saving.
   - Forbid intake of sensitive system files (`/etc`, `/proc`, `/sys`, `/dev`, `/root`, `/var/run`).
   - Ensure `get_job_dir(job_id)` and `save_artifact(..., filename=...)` strictly prevent `../` traversal outside the designated storage root.
4. **Prompt & Subtitle Injection Sanitization (F16)**:
   - In `packages/video_intake_core/context/__init__.py`:
     - Apply `sanitize_for_prompt` to all raw transcripts, subtitle lines, and OCR texts.
     - Enclose LLM-bound knowledge inside explicit XML boundaries (`<video_transcript>`, `<ocr_extracted_content>`) to prevent indirect prompt injection attacks against consuming agents.
5. **Strict SQLite & Working Tree Cleanliness (F17)**:
   - In `packages/video_intake_core/jobs/__init__.py`:
     - Change default database path `_DEFAULT_DB_PATH` from `"jobs.db"` to `Path.home() / ".video-intake" / "jobs.db"`.
     - Ensure the directory `~/.video-intake` is created with secure permissions (`0o700`).
   - Remove `/srv/video-intake-knowledge/jobs.db` from the project root.
   - Ensure working tree is 100% free of `.db` files, `.memory/`, or cache artifacts.
6. **Verification**:
   - Run security tests: `pytest tests/security/ -v`.
   - Verify SSRF defenses against simulated attacks (`127.0.0.1`, `0177.0.0.1`, `2130706433`, `127.0.0.1.nip.io`, `metadata.google.internal`).
   - Verify git status shows NO `jobs.db` or SQLite binaries.
   - Deliver `handoff.md` with verification commands and passing results.

## 2026-09-21T23:06:52Z
You are Worker M3 for Milestone M3 (Hardened Security & Strict Memory Isolation - R3).
Working Directory: /srv/video-intake-knowledge/.agents/teamwork_preview_worker_m3
Project Root: /srv/video-intake-knowledge
Authoritative Requirements: Read /srv/video-intake-knowledge/.agents/ORIGINAL_REQUEST.md
System Constitution: Read and adhere strictly to /home/aibos/AGENTS.md
Scope & Architecture: Read /srv/video-intake-knowledge/.agents/PROJECT.md
Survey Findings: Read /srv/video-intake-knowledge/.agents/teamwork_preview_explorer_survey_3/survey_report.md
Your Dispatch Brief: Read /srv/video-intake-knowledge/.agents/teamwork_preview_worker_m3/DISPATCH.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Implement features F13, F14, F15, F16, F17. Run tests and verify your implementation. Deliver handoff.md and notify the orchestrator via send_message.
