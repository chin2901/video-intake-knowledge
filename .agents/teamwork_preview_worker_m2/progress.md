# Progress — Worker M2 (Universal Agent Experience, Adapters & Scaffolding)

Last visited: 2026-09-22T01:07:35Z
Status: In Progress

## Tasks
- [ ] 1. Investigate existing files within ownership boundary and existing test suite.
- [ ] 2. Consolidate SSoT Selection & Menu Parser in `packages/video_intake_core/cli/menu.py` (F11).
- [ ] 3. Canonicalize root `SKILL.md` (F7): frontmatter, 2-phase structure, proposals docs, purge vitk, symlink `skill/SKILL.md`.
- [ ] 4. Fix and modernize all Agent Adapters (F8):
  - [ ] Cursor adapter (`adapters/cursor/`, `.cursorrules`, `SKILL.md`, `install.sh`)
  - [ ] Codex adapter (`adapters/codex/`, `SKILL.md`, `install.sh`, `uninstall.sh`)
  - [ ] Hermes adapter (`adapters/hermes/install.sh` path bug, `plugin.yaml`, purge git memory)
  - [ ] AGY adapter (`adapters/agy/SKILL.md` Phase 2 routing, modern CLI)
  - [ ] Claude Code & OpenCode adapters (`adapters/claude-code/`, `adapters/opencode/`)
- [ ] 5. Universal `install.sh` (F9): `--hermes`, `--agy`, `--claude-code`, `--opencode`, `--codex`, `--cursor`, `--all`.
- [ ] 6. 2-Phase Conversational Flow CLI Integration & `scripts/interactive.py` (F10).
- [ ] 7. Dynamic Scaffolding Elevation in `packages/video_intake_core/cli/proposals.py` (F12).
- [ ] 8. Run tests, lint, verify installer and scaffolding.
- [ ] 9. Prepare and deliver `handoff.md`, send message to parent.
