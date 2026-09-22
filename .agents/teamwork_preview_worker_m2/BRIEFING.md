# BRIEFING — 2026-09-22T01:07:30Z

## Mission
Implement Milestone M2: Universal Agent Experience, Adapters & Scaffolding (R2) covering Features F7, F8, F9, F10, F11, F12.

## 🔒 My Identity
- Archetype: worker
- Roles: implementer, qa, specialist
- Working directory: /srv/video-intake-knowledge/.agents/teamwork_preview_worker_m2
- Original parent: b72916b2-018f-4bba-9bd2-a657cf9de0ac
- Milestone: M2 (Universal Agent Experience, Adapters & Scaffolding - R2)

## 🔒 Key Constraints
- EXCLUSIVELY modify files within Write Ownership boundary:
  - `/srv/video-intake-knowledge/SKILL.md` (Root SSoT specification)
  - `/srv/video-intake-knowledge/install.sh`
  - `adapters/` (all subdirectories: `cursor/`, `codex/`, `hermes/`, `agy/`, `claude-code/`, `opencode/`)
  - `packages/video_intake_core/cli/menu.py` (SSoT menu parser)
  - `packages/video_intake_core/cli/proposals.py`
  - `scripts/interactive.py`
  - `skill/` (remove or symlink obsolete duplicate)
- DO NOT modify files outside write ownership boundary.
- Adhere strictly to `/home/aibos/AGENTS.md` (Radical simplicity, SSoT, Ground Truth, no facades, no hardcoding).
- Genuine implementations only: no dummy outputs, no hardcoded verification strings.

## Current Parent
- Conversation ID: b72916b2-018f-4bba-9bd2-a657cf9de0ac
- Updated: not yet

## Task Summary
- **What to build**:
  - F7: Canonical Single Source of Truth for SKILL.md (YAML frontmatter, strict 2-phase structure, document proposals CLI, purge vitk, symlink skill/SKILL.md).
  - F8: Complete & Modernize Agent Adapters (Cursor adapter with .cursorrules, Codex adapter rewrite, Hermes path fix & modernization, AGY Phase 2 routing & modern CLI, Claude Code & OpenCode manifests).
  - F9: Universal `install.sh` supporting `--hermes`, `--agy`, `--claude-code`, `--opencode`, `--codex`, `--cursor`, `--all`.
  - F10: 2-Phase Conversational Flow CLI Integration (`video-intake interactive [URL]` and interactive TTY detection in `video-intake extract`).
  - F11: SSoT Selection & Menu Parser in `packages/video_intake_core/cli/menu.py`.
  - F12: Dynamic Scaffolding Elevation (`video-intake proposals --scaffold {skill,tool,agent}` deriving steps, capabilities, and tools from transcript/chapters).
- **Success criteria**:
  - Passing build/lint/tests.
  - All adapter installations functional and verified.
  - Proposals scaffold tests passing with dynamic content.
  - Handoff report delivered to parent.
- **Interface contracts**: `/srv/video-intake-knowledge/.agents/PROJECT.md`
- **Code layout**: `/srv/video-intake-knowledge/.agents/PROJECT.md`

## Change Tracker
- **Files modified**: none yet
- **Build status**: pending
- **Pending issues**: none

## Quality Status
- **Build/test result**: pending initial run
- **Lint status**: pending
- **Tests added/modified**: pending

## Loaded Skills
- (None loaded via prompt)

## Key Decisions Made
- Follow Tony's Radical Simplicity and SSoT: Single canonical SKILL.md at repo root, adapters reference or link to it; single menu parser in `cli/menu.py`.

## Artifact Index
- `.agents/teamwork_preview_worker_m2/DISPATCH.md` — Assignment brief
- `.agents/teamwork_preview_worker_m2/BRIEFING.md` — Working memory and status
- `.agents/teamwork_preview_worker_m2/progress.md` — Execution progress and heartbeat
