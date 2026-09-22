# Task Assignment: Worker M2 (Universal Agent Experience, Adapters & Scaffolding - R2)

## Context
- Project Root: `/srv/video-intake-knowledge`
- Working Directory: `/srv/video-intake-knowledge/.agents/teamwork_preview_worker_m2`
- Authoritative Requirements: `/srv/video-intake-knowledge/.agents/ORIGINAL_REQUEST.md` (MUST read in full)
- System Constitution: `/home/aibos/AGENTS.md` (MUST adhere strictly)
- Scope & Architecture: `/srv/video-intake-knowledge/.agents/PROJECT.md`
- Survey Findings: Read `/srv/video-intake-knowledge/.agents/teamwork_preview_explorer_survey_2/survey_report.md`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Write Ownership
You EXCLUSIVELY own and may modify:
- `/srv/video-intake-knowledge/SKILL.md` (Root SSoT specification)
- `/srv/video-intake-knowledge/install.sh`
- `adapters/` (all subdirectories: `cursor/`, `codex/`, `hermes/`, `agy/`, `claude-code/`, `opencode/`)
- `packages/video_intake_core/cli/menu.py` (SSoT menu parser)
- `packages/video_intake_core/cli/proposals.py`
- `scripts/interactive.py`
- `skill/` (remove or symlink obsolete duplicate)
DO NOT modify files outside your ownership boundary.

## Objectives & Implementation Directives
1. **Canonical Single Source of Truth for SKILL.md (F7)**:
   - Root `/srv/video-intake-knowledge/SKILL.md` must be the absolute SSoT.
   - Add standard YAML frontmatter:
     ```yaml
     ---
     name: video-intake-knowledge
     description: Universal skill for video detection, multi-layered extraction, and knowledge routing for AI agents.
     version: 1.0.0
     ---
     ```
   - Structure protocol strictly around **2 Phases**:
     - **FASE 1: Menú interactivo de capas de extracción** (1. Vídeo, 2. Audio, 3. Transcripción con marcas temporales, 4. Contexto de audio, 5. Contexto visual y OCR de diagramas, 6. Todo).
     - **FASE 2: Enrutamiento inteligente de conocimiento** (1. Mensaje en sesión, 2. Inyección de contexto compacto, 3. Banco de memoria externo existente, 4. Nuevo banco de memoria dedicado, 5. Idear y construir herramientas/skills/agentes mediante análisis inteligente y scaffolding automático, 6. Mantener solo artefactos locales).
   - Document `video-intake proposals --scaffold {skill,tool,agent}` clearly in Section 5 CLI reference.
   - Purge all references to obsolete binary `vitk` across all files.
   - Remove or replace `skill/SKILL.md` with a symlink to root `SKILL.md`.
2. **Complete & Modernize Agent Adapters (F8)**:
   - **Cursor**: Create `adapters/cursor/` with canonical `SKILL.md` symlink, `.cursorrules` system instructions for video intake, and installation targeting `~/.cursor` and workspace `.cursor/skills/`.
   - **Codex**: Completely rewrite `adapters/codex/`: create dedicated Codex `SKILL.md`, rewrite `install.sh` targeting `~/.codex/skills/video-intake` without any Hermes or unrelated references.
   - **Hermes**: Fix relative path bug in `adapters/hermes/install.sh:95` (`../../scripts/standalone_hermes.sh`), modernize `plugin.yaml` to invoke `video-intake` directly, remove git repository memory references.
   - **AGY**: Update `adapters/agy/SKILL.md` to include Phase 2 Knowledge Routing and modern CLI syntax.
   - **Claude Code & OpenCode**: Replace 507-line legacy duplicates with clean manifests linking to canonical `SKILL.md`.
3. **Universal `install.sh` (F9)**:
   - Update root `install.sh` to fully support:
     `--hermes`, `--agy`, `--claude-code`, `--opencode`, `--codex`, `--cursor`, and `--all`.
   - Ensure `--cursor` and `--codex` work seamlessly and verify installation.
4. **2-Phase Conversational Flow CLI Integration (F10)**:
   - Integrate interactive flow so running `video-intake` in interactive environments easily presents Phase 1 and Phase 2.
   - Provide `video-intake interactive [URL]` and support interactive TTY detection in `video-intake extract`.
5. **SSoT Selection & Menu Parser (F11)**:
   - Consolidate selection parsing into single authoritative `parse_menu_selection` in `packages/video_intake_core/cli/menu.py`.
6. **Dynamic Scaffolding Elevation (F12)**:
   - Elevate `video-intake proposals --scaffold {skill,tool,agent}`: derive step-by-step instructions, capabilities, tool CLI flags, and agent prompts dynamically from the extracted transcript, chapters, and topics rather than static generic placeholders.
7. **Verification**:
   - Test `install.sh` with all adapter flags.
   - Test `video-intake proposals --scaffold {skill,tool,agent}` and verify generated files.
   - Deliver `handoff.md` with all verification steps and passing test outputs.

## 2026-09-22T01:06:52Z
<USER_REQUEST>
You are Worker M2 for Milestone M2 (Universal Agent Experience, Adapters & Scaffolding - R2).
Working Directory: /srv/video-intake-knowledge/.agents/teamwork_preview_worker_m2
Project Root: /srv/video-intake-knowledge
Authoritative Requirements: Read /srv/video-intake-knowledge/.agents/ORIGINAL_REQUEST.md
System Constitution: Read and adhere strictly to /home/aibos/AGENTS.md
Scope & Architecture: Read /srv/video-intake-knowledge/.agents/PROJECT.md
Survey Findings: Read /srv/video-intake-knowledge/.agents/teamwork_preview_explorer_survey_2/survey_report.md
Your Dispatch Brief: Read /srv/video-intake-knowledge/.agents/teamwork_preview_worker_m2/DISPATCH.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Implement features F7, F8, F9, F10, F11, F12. Run tests and verify your implementation. Deliver handoff.md and notify the orchestrator via send_message.
</USER_REQUEST>
