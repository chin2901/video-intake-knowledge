# Task Assignment: Survey Explorer 3 (Security, Isolation, QA, Testing & Docs - R3, R4, R5)

## Context
- Project Root: `/srv/video-intake-knowledge`
- Working Directory: `/srv/video-intake-knowledge/.agents/teamwork_preview_explorer_survey_3`
- Authoritative Requirements: `/srv/video-intake-knowledge/.agents/ORIGINAL_REQUEST.md` (MUST read in full)
- System Constitution: `/home/aibos/AGENTS.md` (MUST adhere strictly)

## Objectives
Map the full scope and current state of the codebase focusing on R3, R4, and R5:
1. Security & Isolation (R3):
   - Current URL validation & SSRF prevention mechanisms (loopback/private IP blocking).
   - Path traversal prevention in media saving/cache handling.
   - Prompt & subtitle injection sanitization.
   - Memory storage location and git repository cleanliness: verify if any SQLite or `.memory/` files exist in working tree, verify `~/.video-intake/memory.db` enforcement.
2. QA & Test Suite (R4):
   - Current test files, pytest coverage, test framework, mock fixtures.
   - Ruff linting configuration and current violations.
   - Type checking configuration and typing errors.
   - CI/CD workflows (.github/workflows).
   - Doctor scripts (`video-intake doctor`, `./scripts/doctor.sh`).
3. Documentation & Developer Experience (R5):
   - README structure, badges, Mermaid diagrams, schemas, guides.
4. Document gaps between current implementation and R3, R4, R5 requirements & acceptance criteria.
5. Deliver a comprehensive survey report in `/srv/video-intake-knowledge/.agents/teamwork_preview_explorer_survey_3/survey_report.md` and complete handoff.md.
