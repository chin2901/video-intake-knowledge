# BRIEFING — 2026-09-21T23:07:00Z

## Mission
Implement features F13 (Deterministic SSRF Prevention), F14 (Security Gateway Enforcement), F15 (Path Traversal Defenses), F16 (Prompt & Subtitle Injection Sanitization), and F17 (Strict SQLite & Memory Isolation).

## 🔒 My Identity
- Archetype: teamwork_preview_worker_m3
- Roles: implementer, qa, specialist
- Working directory: /srv/video-intake-knowledge/.agents/teamwork_preview_worker_m3
- Original parent: b72916b2-018f-4bba-9bd2-a657cf9de0ac
- Milestone: M3 (Hardened Security & Strict Memory Isolation - R3)

## 🔒 Key Constraints
- Write Ownership exclusively:
  - packages/video_intake_core/security/
  - packages/video_intake_core/utils/validation.py
  - packages/video_intake_core/utils/fs.py
  - packages/video_intake_core/context/ (prompt boundary wrapping & subtitle injection sanitization)
  - packages/video_intake_core/storage/ (containment & path sanitization)
  - packages/video_intake_core/jobs/ (default db path to ~/.video-intake/jobs.db)
  - packages/video_intake_core/memory/ (memory isolation enforcement)
  - Remove /srv/video-intake-knowledge/jobs.db from repository root
- DO NOT modify files outside write ownership boundary.
- Mandatory Integrity: No hardcoding test results, no facade implementations, genuine real state & logic.
- System Constitution (/home/aibos/AGENTS.md): "Menos es Más", SSoT, Ground Truth, Cero Chapuzas, Cero Especulación.
- .agents/ holds only metadata. Never place source code or data here.

## Current Parent
- Conversation ID: b72916b2-018f-4bba-9bd2-a657cf9de0ac
- Updated: not yet

## Task Summary
- **What to build**:
  1. Deterministic SSRF Prevention (F13): socket.getaddrinfo DNS resolution, IPv4/IPv6 address parsing, blocking loopback, private, link-local, carrier-grade NAT, cloud metadata IPs, neutralizing octal/hex/decimal IP bypasses and DNS rebinding.
  2. Security Gateway Enforcement (F14): Wire validate_video_url before yt-dlp or any network call in acquisition and orchestrator.py (or via acquisition entrypoints within ownership).
  3. Path Traversal Defenses in File Ingestion & Storage (F15): validate_local_file and sanitize_path enforcement in storage and file intake, block sensitive system directories, ensure get_job_dir and save_artifact prevent traversal.
  4. Prompt & Subtitle Injection Sanitization (F16): sanitize_for_prompt applied to raw transcripts, subtitle lines, OCR texts, enclosing LLM-bound knowledge in XML boundaries (<video_transcript>, <ocr_extracted_content>).
  5. Strict SQLite & Working Tree Cleanliness (F17): Default jobs.db to ~/.video-intake/jobs.db with 0o700 permissions, delete root jobs.db, ensure tree clean of .db/.memory.
- **Success criteria**:
  - Security test suite passing with 0 failures (`pytest tests/security/ -v`).
  - SSRF defenses withstand simulated attacks (127.0.0.1, 0177.0.0.1, 2130706433, 127.0.0.1.nip.io, metadata.google.internal).
  - Git status clean of jobs.db or SQLite binaries.
  - Handoff report delivered with passing verification commands.
- **Interface contracts**: /srv/video-intake-knowledge/.agents/PROJECT.md § Interface Contracts
- **Code layout**: /srv/video-intake-knowledge/.agents/PROJECT.md § Code Layout

## Key Decisions Made
- [Initial planning]: Review existing files within write boundary before making minimal compliant edits.

## Artifact Index
- /srv/video-intake-knowledge/.agents/teamwork_preview_worker_m3/DISPATCH.md — Assignment instructions
- /srv/video-intake-knowledge/.agents/teamwork_preview_worker_m3/BRIEFING.md — Persistent working memory
- /srv/video-intake-knowledge/.agents/teamwork_preview_worker_m3/progress.md — Liveness heartbeat & progress log

## Change Tracker
- **Files modified**: None yet
- **Build status**: Untested
- **Pending issues**: Implement F13-F17

## Quality Status
- **Build/test result**: Untested
- **Lint status**: 0 violations
- **Tests added/modified**: None yet

## Loaded Skills
- None specified in dispatch prompt.
