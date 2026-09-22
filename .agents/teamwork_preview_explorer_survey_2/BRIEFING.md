# BRIEFING — 2026-09-22T01:04:25+02:00

## Mission
Survey the codebase focusing on R2 (Universal Agent Experience, CLI & Scaffolding), investigate SKILL.md, install.sh, CLI commands, agent adapters, 2-phase interactive workflow, proposal scaffolding, and gaps against requirements.

## 🔒 My Identity
- Archetype: explorer
- Roles: codebase investigation, R2 analysis, architectural gap assessment, structured synthesis
- Working directory: /srv/video-intake-knowledge/.agents/teamwork_preview_explorer_survey_2
- Original parent: b72916b2-018f-4bba-9bd2-a657cf9de0ac
- Milestone: Survey R2 (Universal Agent Experience, CLI & Scaffolding)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Strictly adhere to /home/aibos/AGENTS.md constitution (Radical simplicity, Zero speculation, Single Source of Truth, Ground Truth)
- Write only to our assigned working directory: /srv/video-intake-knowledge/.agents/teamwork_preview_explorer_survey_2
- Use send_message to report back to parent (b72916b2-018f-4bba-9bd2-a657cf9de0ac)

## Current Parent
- Conversation ID: b72916b2-018f-4bba-9bd2-a657cf9de0ac
- Updated: 2026-09-22T01:04:25+02:00

## Investigation State
- **Explored paths**: `SKILL.md`, `skill/SKILL.md`, `install.sh`, `adapters/*` (hermes, agy, claude-code, opencode, codex), `packages/video_intake_core/cli/*`, `packages/video_intake_core/orchestrator.py`, `scripts/*` (interactive.py, extract.py, doctor.sh, standalone_hermes.sh), `tests/`
- **Key findings**:
  1. Cursor adapter is completely missing (no folder, no install flag, no rules).
  2. Codex adapter is broken (no SKILL.md, copy-paste of Hermes installing into ~/.hermes).
  3. 7 divergent SKILL.md files violate SSoT; obsolete `vitk` binary referenced.
  4. Monolithic `cli/__init__.py` duplicates modular CLI files, leaving them as dead code (9-19% coverage).
  5. 2-phase interactive flow is isolated in `scripts/interactive.py`; `video-intake extract` lacks interactive prompting.
  6. `video-intake proposals --scaffold` is syntactically valid and tested, but omitted from `SKILL.md` Section 5.
  7. Hermes `install.sh` has a fatal relative path bug preventing `standalone_hermes.sh` copy.
- **Unexplored areas**: None for R2. All 5 objectives fully surveyed and mapped.

## Key Decisions Made
- Established ground-truth findings based on empirical test execution and code analysis.
- Generated `survey_report.md` with complete gap matrix and actionable recommendations.
- Completed 5-component `handoff.md`.

## Artifact Index
- /srv/video-intake-knowledge/.agents/teamwork_preview_explorer_survey_2/survey_report.md — Comprehensive R2 Survey Report
- /srv/video-intake-knowledge/.agents/teamwork_preview_explorer_survey_2/handoff.md — 5-Component Handoff Report
- /srv/video-intake-knowledge/.agents/teamwork_preview_explorer_survey_2/progress.md — Liveness Heartbeat
- /srv/video-intake-knowledge/.agents/teamwork_preview_explorer_survey_2/DISPATCH.md — Dispatch log
