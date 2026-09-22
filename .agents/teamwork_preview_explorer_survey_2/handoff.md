# Handoff Report: Explorer 2 — Universal Agent Experience, CLI & Scaffolding (R2)

**Agent**: Explorer 2  
**Working Directory**: `/srv/video-intake-knowledge/.agents/teamwork_preview_explorer_survey_2`  
**Target Milestone**: Survey R2 (Universal Agent Experience, CLI & Scaffolding)  
**Date**: 2026-09-22T01:04:10+02:00  

---

## 1. Observation

Direct empirical observations made during read-only inspection of the codebase:

1. **Cursor Adapter is 100% Missing**:
   - `adapters/cursor/` does NOT exist in the filesystem.
   - `install.sh` (lines 13–18, 38–50) defines options `--hermes`, `--agy`, `--claude-code`, `--opencode`, `--codex`, `--all`, but has **no `--cursor` option**.
   - No `.cursorrules` or `.cursor/skills` configuration file exists anywhere in the repository.

2. **Codex Adapter is Broken and Inverted**:
   - `adapters/codex/` contains only `install.sh` and `uninstall.sh`. It contains **NO `SKILL.md`**.
   - `adapters/codex/install.sh` lines 1–15 state:
     ```bash
     # install.sh — Instalador del plugin Hermes para video-intake-knowledge
     PREFIX="${PREFIX:-$HOME/.hermes}"
     ```
     The script installs into `$HOME/.hermes` and edits `$PREFIX/plugin-data/registry.yaml`, which is an erroneous copy-paste of Hermes and completely useless for OpenAI Codex.

3. **SKILL Specification Sprawl (SSoT Violation)**:
   - 7 different `SKILL.md` files exist across the repository:
     * `/srv/video-intake-knowledge/SKILL.md` (154 lines, lacks YAML frontmatter, lists 3 phases under a "2 Fases" header).
     * `/srv/video-intake-knowledge/skill/SKILL.md` (586 lines, declares Apache-2.0 license conflicting with root MIT).
     * `/srv/video-intake-knowledge/adapters/hermes/skill/SKILL.md` (182 lines, references obsolete `vitk` and points to `/srv/video-intake-knowledge/memory/`, violating zero-database git rules).
     * `/srv/video-intake-knowledge/adapters/agy/SKILL.md` (61 lines, uses `[[tool:...]]`, references `vitk`, has NO Phase 2 knowledge routing).
     * `/srv/video-intake-knowledge/adapters/claude-code/SKILL.md` (507 lines, near-duplicate of `skill/SKILL.md`).
     * `/srv/video-intake-knowledge/adapters/opencode/SKILL.md` (507 lines, near-duplicate of `skill/SKILL.md`).
     * `/srv/video-intake-knowledge/adapters/generic-agent-skills/SKILL.md` (192 lines, references `vitk`).

4. **Fatal Path Error in Hermes Installer**:
   - `adapters/hermes/install.sh` line 95:
     ```bash
     if [[ -f "$SCRIPT_DIR/../scripts/standalone_hermes.sh" ]]; then
         cp "$SCRIPT_DIR/../scripts/standalone_hermes.sh" "$TARGET_DIR/"
     ```
     `$SCRIPT_DIR` is `/srv/video-intake-knowledge/adapters/hermes`. `$SCRIPT_DIR/../scripts/` evaluates to `/srv/video-intake-knowledge/adapters/scripts/` which does not exist. `standalone_hermes.sh` is never copied.

5. **2-Phase Conversational Flow Decoupled from CLI**:
   - `scripts/interactive.py` lines 151–176 implements Phase 1 and Phase 2.
   - However, in `packages/video_intake_core/cli/__init__.py:442`, `cmd_extract` defaults to `--select 6`, executes immediately, and terminates without prompting for Phase 1 or Phase 2.

6. **CLI Implementation Duplication and Dead Code**:
   - `packages/video_intake_core/cli/__init__.py` (1187 lines) contains monolithic duplicate implementations of `cmd_doctor`, `cmd_inspect`, `cmd_extract`, `cmd_batch`, `cmd_status`, `cmd_cancel`, `cmd_artifacts`, `cmd_export`, `cmd_cleanup`, `cmd_config_validate`, `cmd_self_test`, and `cmd_models_*`.
   - The parallel modular files (`cli/extract.py`, `cli/status.py`, `cli/artifacts.py`, `cli/cleanup.py`, `cli/export.py`, `cli/models.py`, `cli/config_cmd.py`) are bypassed and uncalled by `build_parser()`.
   - Consequently, test coverage on these modular files is artificially low (9% to 19%).

7. **Proposals & Scaffolding Execution**:
   - `video-intake proposals --scaffold {skill,tool,agent,all}` is implemented in `video_intake_core/cli/proposals.py` and `video_intake_core/orchestrator.py:338`.
   - Tested execution via `python3 -m video_intake_core.cli proposals --job-id job_20260921_225137_e778c0 --scaffold all --output /tmp/test_scaffold`. Generated `SKILL.md`, `tool.py`, `agent.yaml`, and `prompts/system.md`. All files were syntactically valid (valid YAML, valid Python AST, valid Markdown with frontmatter).
   - However, `video-intake proposals` is **completely missing** from Section 5 of root `SKILL.md`.

---

## 2. Logic Chain

1. **Premise**: Requirement R2 mandates universal agent support across Hermes, AGY, Claude Code, OpenCode, Codex, and Cursor, and acceptance criteria mandate that `SKILL.md` and `install.sh` integrate with all of them.
2. **Observation 1 & 2**: Cursor has no adapter directory, no `.cursorrules`, and no installer flag. Codex has no `SKILL.md` and its installer is an erroneous copy of Hermes installing into `~/.hermes`.
3. **Inference**: Acceptance Criterion *"La especificación SKILL.md y el script install.sh se integran y verifican con éxito en los entornos soportados"* currently **FAILS** for Cursor and Codex.
4. **Premise**: SSoT (Constitution, Section 1) dictates having exactly one authoritative source for any specification, rejecting duplicate files that drift.
5. **Observation 3**: Seven disparate `SKILL.md` files exist with conflicting command names (`vitk` vs `video-intake`), conflicting licenses (Apache-2.0 vs MIT), and inconsistent phases (AGY lacks Phase 2).
6. **Inference**: An AI agent reading any adapter other than the root file will receive obsolete instructions and invalid commands.
7. **Premise**: R2 mandates a seamless 2-phase conversational experience (Phase 1: Extraction Menu; Phase 2: Knowledge Routing).
8. **Observation 5**: Only `scripts/interactive.py` runs the 2-phase flow. The primary CLI binary (`video-intake extract`) runs strictly non-interactively, bypassing the menu.
9. **Inference**: CLI-driven agent interactions fail to deliver the conversational 2-phase experience.
10. **Premise**: R2 mandates `video-intake proposals --scaffold {skill,tool,agent}` generating functional, syntactically valid scaffolding.
11. **Observation 7**: The command works and syntax is valid, but is undocumented in `SKILL.md` and uses static boilerplate steps.
12. **Inference**: The scaffolding engine satisfies minimal syntax criteria but requires template elevation and documentation discoverability.

---

## 3. Caveats

1. **Networked Remote Platform Extraction**: Remote YouTube, Facebook, Instagram, and TikTok downloading was not tested with live authenticated URLs to avoid external API calls during read-only investigation. Analysis was conducted using local fixtures (`sample.mp4`).
2. **Host-Specific IDE Validation**: Live integration testing inside proprietary IDE host environments (actual Hermes runtime daemon, Cursor desktop client, OpenAI Codex production endpoint) was not executed; verification was performed against local configuration directory contracts (`~/.hermes`, `~/.agy`, `~/.claude`, `~/.opencode`, `~/.codex`).
3. **No Code Changes Performed**: In strict adherence to Explorer read-only constraints, no production files were modified.

---

## 4. Conclusion

The codebase possesses strong underlying algorithmic primitives for multi-layer extraction and scaffolding, but **fails R2 acceptance criteria** due to:
1. Complete absence of the Cursor adapter.
2. Defective Codex adapter (Hermes copy-paste without `SKILL.md`).
3. Specification fragmentation across 7 divergent `SKILL.md` files.
4. Architectural duplication between monolithic `cli/__init__.py` and modular `cli/*.py` files.
5. Decoupling of the 2-phase conversational flow from the primary `video-intake` CLI.
6. Absence of `video-intake proposals` in `SKILL.md` documentation.

All defects have clear, deterministic root causes and can be resolved during implementation by establishing root `SKILL.md` as SSoT, building the missing Cursor and Codex adapters, unifying the CLI parser, and wiring interactive mode into the primary CLI.

---

## 5. Verification Method

To independently reproduce and verify all findings:

1. **Verify missing Cursor and broken Codex adapters**:
   ```bash
   ls -la /srv/video-intake-knowledge/adapters/cursor
   # Returns: No such file or directory
   head -n 20 /srv/video-intake-knowledge/adapters/codex/install.sh
   # Confirms PREFIX="$HOME/.hermes" and Hermes plugin text
   ls -la /srv/video-intake-knowledge/adapters/codex/SKILL.md
   # Returns: No such file or directory
   ```

2. **Verify Hermes installer path bug**:
   ```bash
   grep -n "standalone_hermes.sh" /srv/video-intake-knowledge/adapters/hermes/install.sh
   # Shows line 95 targeting non-existent "$SCRIPT_DIR/../scripts/standalone_hermes.sh"
   ```

3. **Verify proposals scaffolding command**:
   ```bash
   python3 -m video_intake_core.cli proposals --job-id job_20260921_225137_e778c0 --scaffold all --output /tmp/verify_scaffold
   # Inspect generated files:
   python3 -m py_compile /tmp/verify_scaffold/tool_sample/tool.py
   python3 -c "import yaml; yaml.safe_load(open('/tmp/verify_scaffold/agente-sample/agent.yaml'))"
   rm -rf /tmp/verify_scaffold
   ```

4. **Verify test suite and coverage**:
   ```bash
   ./venv/bin/pytest
   # 153 passed
   ./venv/bin/pytest --cov=video_intake_core --cov-report=term-missing
   # Shows 47% total coverage, with dead modular CLI files at 9-19%
   ```

5. **Verify CLI extract lack of interactivity**:
   ```bash
   python3 -m video_intake_core.cli extract tests/fixtures/video/sample.mp4
   # Runs immediately with default operations without prompting for Phase 1 or Phase 2
   ```
