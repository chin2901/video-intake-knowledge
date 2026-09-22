# Survey Report: Universal Agent Experience, CLI & Scaffolding (R2)

**Author**: Explorer 2 (Survey & Codebase Investigation)  
**Date**: 2026-09-22T01:03:50+02:00  
**Project**: `video-intake-knowledge`  
**Working Directory**: `/srv/video-intake-knowledge/.agents/teamwork_preview_explorer_survey_2`  
**Authoritative Scope**: Requirement R2 & Acceptance Criteria from `/srv/video-intake-knowledge/.agents/ORIGINAL_REQUEST.md`  
**Governing Constitution**: `/home/aibos/AGENTS.md` (Tony's Radical Simplicity, Zero Speculation, Ground Truth, Single Source of Truth)

---

## Executive Summary

An exhaustive empirical survey of the `video-intake-knowledge` codebase was conducted focusing on **Requirement R2 (Universal Agent Experience, CLI & Scaffolding)**. The codebase possesses a functional foundational engine for media extraction, multi-layered processing (yt-dlp, ffmpeg, tesseract, whisper), and asset scaffolding (`video-intake proposals --scaffold`).

However, the repository currently suffers from severe architectural fragmentation, code duplication, and incomplete platform integrations:
1. **Critical Adapter Gaps**: The **Cursor** adapter is completely missing (no directory, no installer option, no `.cursorrules`). The **Codex** adapter is broken (contains a copy-pasted Hermes installer pointing to `~/.hermes` and has no `SKILL.md`).
2. **SSoT Violation in SKILL Specifications**: There are **seven different, divergent `SKILL.md` files** scattered across `skill/`, `skills/`, and `adapters/` with conflicting licenses (MIT vs. Apache-2.0), obsolete binary names (`vitk` instead of `video-intake`), and missing phases.
3. **Interactive Workflow Decoupled from Primary CLI**: The canonical 2-phase interactive experience is only implemented in `scripts/interactive.py`. Running `video-intake extract <URL>` runs strictly in batch/non-interactive mode defaulting to `--select 6` without prompting for Phase 1 or Phase 2.
4. **CLI Implementation Duplication**: `packages/video_intake_core/cli/__init__.py` contains an 1187-line monolith with duplicate inline command implementations that bypass the modular files in `packages/video_intake_core/cli/*.py`, leaving them as unreferenced dead code.
5. **Phase Numbering & Documentation Dissonance**: Root `SKILL.md` labels the workflow as "FASE 1, FASE 2, FASE 3" while the section header claims "Orquestación en 2 Fases", and fails to document the `video-intake proposals` command.

---

## 1. `SKILL.md` Specification Analysis

### 1.1 Ground Truth Inventory of SKILL Files

The codebase exhibits severe specification sprawl, directly violating the **Single Source of Truth (SSoT)** principle of Tony's Constitution:

| File Path | Lines | Version / Header | Command Name Used | Phase 2 Routing? | License Stated |
|---|---|---|---|---|---|
| `/srv/video-intake-knowledge/SKILL.md` | 154 | `# SKILL: Video Intake Knowledge` (No YAML frontmatter) | `video-intake` / `scripts/*.py` | Yes (labeled FASE 3) | MIT (repo root) |
| `/srv/video-intake-knowledge/skill/SKILL.md` | 586 | `# SKILL.md — Skill portable...` (No frontmatter) | `video-intake` | Yes (numbered 1-6) | Apache-2.0 (line 585) |
| `/srv/video-intake-knowledge/adapters/hermes/skill/SKILL.md` | 182 | Hermes Agent Specific | `vitk` / `video_intake_*` | Mentions memory, no scaffolding | Unspecified |
| `/srv/video-intake-knowledge/adapters/agy/SKILL.md` | 61 | `[[tool:video-intake-knowledge]]` | `vitk` | **NO** (Stops at Phase 1 menu) | Unspecified |
| `/srv/video-intake-knowledge/adapters/claude-code/SKILL.md` | 507 | Portable Skill for Claude Code | `video-intake` | Yes | MIT |
| `/srv/video-intake-knowledge/adapters/opencode/SKILL.md` | 507 | Portable Skill for OpenCode | `video-intake` | Yes | MIT |
| `/srv/video-intake-knowledge/adapters/generic-agent-skills/SKILL.md` | 192 | Generic Skill | `vitk` | Partial (`vitk knowledge`) | Apache-2.0 |
| `/srv/video-intake-knowledge/skills/video-intake-validation.SKILL.md` | 30 | Secondary Validation Skill | `scripts/verify-install.sh` | None | Unspecified |
| `/srv/video-intake-knowledge/adapters/codex/` | 0 | **NO SKILL.md EXISTS** | N/A | N/A | N/A |
| `/srv/video-intake-knowledge/adapters/cursor/` | 0 | **DIRECTORY DOES NOT EXIST** | N/A | N/A | N/A |

### 1.2 Canonical Specification Flaws in Root `SKILL.md`

1. **Absence of Standard YAML Frontmatter**:
   The modern Agent Skills specification (adopted across Anthropic Claude Code, AGY, OpenCode, and Codex) expects standard YAML frontmatter for machine parsing:
   ```yaml
   ---
   name: video-intake-knowledge
   description: Universal skill for video detection, multi-layered extraction, and knowledge routing for AI agents.
   version: 1.0.0
   ---
   ```
   The root `SKILL.md` has no frontmatter; parsing starts with raw markdown `# SKILL: Video Intake Knowledge`.

2. **Phase Numbering Dissonance**:
   In `SKILL.md` lines 27–67:
   - Line 27: `## 3. Protocolo Operativo del Agente (Orquestación en 2 Fases)`
   - Line 31: `### FASE 1: Preguntar qué extraer del vídeo`
   - Line 45: `### FASE 2: Ejecución autónoma con herramientas locales`
   - Line 57: `### FASE 3: Preguntar destino / enrutamiento del conocimiento`
   While the header specifies "2 Fases", the text defines three phases. In `ORIGINAL_REQUEST.md` (R2), the canonical specification is strictly **2 phases**:
   - **Phase 1**: Interactive extraction menu (layers: video, audio, transcript, audio context, visual context, all).
   - **Phase 2**: Knowledge routing (session message, session context injection, existing memory bank, new dedicated memory bank, build proposals & scaffolding).

3. **Omission of Scaffolding CLI in Reference**:
   Section 5 (`## 5. Referencia de Comandos CLI`, lines 104–130) lists `doctor`, `inspect`, `extract`, `interactive.py`, `status`, `artifacts`, `export`. It **completely omits** `video-intake proposals --scaffold {skill,tool,agent}`! An agent reading `SKILL.md` cannot discover the CLI command for scaffolding.

4. **Missing Cursor in Quick Install**:
   Section 4 (`## 4. Instalación Rápida`, lines 92–100) lists `--hermes`, `--agy`, `--claude-code`, `--opencode`, `--codex`, `--all`. `--cursor` is omitted.

---

## 2. `install.sh` & Agent Adapter Ecosystem Investigation

### 2.1 Analysis of Root `install.sh`

File: `/srv/video-intake-knowledge/install.sh` (182 lines)

1. **Option Handling (lines 38–50)**:
   - Recognizes: `--hermes`, `--agy`, `--claude-code`, `--opencode`, `--codex`, `--all`, `--skip-doctor`, `--help`.
   - **Missing**: `--cursor`.
   - `--all` (lines 52–58) does not enable Cursor.
2. **Symlink Strategy (lines 128–166)**:
   ```bash
   install_skill_to() {
       local target_dir="$1"
       local name="$2"
       mkdir -p "$target_dir"
       ln -sf "$ROOT_DIR/SKILL.md" "$target_dir/SKILL.md"
       echo "  [OK] $name: Skill vinculada en $target_dir"
   }
   ```
   - For AGY, Claude Code, OpenCode, and Codex, `install.sh` only symlinks the root `SKILL.md` into `~/.<host>/skills/video-intake/SKILL.md`.
   - It **ignores** the files located in `adapters/agy/`, `adapters/claude-code/`, `adapters/opencode/`, and `adapters/codex/`.
3. **Hermes Special Handling (lines 140–144)**:
   - For Hermes, it also symlinks `adapters/hermes` to `~/.hermes/plugins/video-intake`. However, as shown below, `adapters/hermes/install.sh` has its own fatal path bug.
4. **Execution of Doctor at Exit (line 180)**:
   - Invokes `"$PYTHON_EXEC" -m video_intake_core.cli doctor || true` instead of testing the linked `video-intake` command in PATH (`~/.local/bin/video-intake`).

---

### 2.2 Deep Dive into Agent Adapters

#### A. Hermes Agent (`adapters/hermes/`)
- **Components**: `plugin.yaml`, `skill/SKILL.md`, `install.sh`, `uninstall.sh`, `config.example.yaml`, `hooks/hook_video_intake.sh`, `plugin/register.py`, `tools/video_intake_harness.py`, `scripts/standalone_hermes.sh`.
- **Findings & Defects**:
  1. **Fatal Path Error in `adapters/hermes/install.sh` (line 95)**:
     ```bash
     if [[ -f "$SCRIPT_DIR/../scripts/standalone_hermes.sh" ]]; then
         cp "$SCRIPT_DIR/../scripts/standalone_hermes.sh" "$TARGET_DIR/"
     ```
     `$SCRIPT_DIR` is `.../adapters/hermes`. `$SCRIPT_DIR/../scripts/` evaluates to `.../adapters/scripts/`, which **does not exist** (the true path is `../../scripts/`). Consequently, `standalone_hermes.sh` is never copied!
  2. **Obsolete Command References (`vitk`)**:
     `plugin.yaml` registers commands `vitk` and `video-intake` pointing to `../../scripts/standalone_hermes.sh`, exposing subcommands `detectar`, `extraer`, `menu`, `list`, `status` rather than standard English `inspect`, `extract`, `batch`, `proposals`.
  3. **Violation of Zero Memory in Git (`adapters/hermes/skill/SKILL.md` line 141)**:
     Instructs fallback to `/srv/video-intake-knowledge/memory/`, violating R3 and the project constitution.

#### B. AGY (`adapters/agy/`)
- **Components**: `README.md`, `SKILL.md`, `config.example.yaml`.
- **Findings & Defects**:
  1. **Truncated Protocol**: `adapters/agy/SKILL.md` lists the extraction menu (Phase 1) but contains **no Phase 2 knowledge routing**, no mention of memory banks, and no proposals/scaffolding instructions.
  2. **Obsolete Binary**: Uses `vitk doctor`, `vitk inspect`, `vitk extract`, `vitk knowledge` (non-existent subcommand).
  3. **Bypassed by `install.sh`**: Running `./install.sh --agy` symlinks the root `SKILL.md`, leaving `adapters/agy/` completely unused.

#### C. Claude Code (`adapters/claude-code/`)
- **Components**: `SKILL.md` (507 lines), `install.sh`.
- **Findings & Defects**:
  1. **Bloated Duplicate**: A 507-line near-verbatim duplicate of `skill/SKILL.md`.
  2. **Obsolete Tool Check in `install.sh` line 98**: Tests `command -v vitk` instead of `command -v video-intake`.
  3. **Inaccurate Memory Claim (line 194)**: Claims Claude Code has no memory support, ignoring that `video-intake` handles local user memory persistence automatically via SQLite in `~/.video-intake/memory.db`.
  4. **Missing Scaffolding Documentation**: Does not mention `video-intake proposals --scaffold`.

#### D. OpenCode (`adapters/opencode/`)
- **Components**: `SKILL.md` (507 lines).
- **Findings & Defects**:
  1. **Bloated Duplicate**: Exactly identical to `adapters/claude-code/SKILL.md` except for three word substitutions (`OpenCode` vs `Claude Code`).
  2. **No Local Installer**: Unlike `claude-code`, `opencode` has no `install.sh` inside its adapter folder.

#### E. Codex (`adapters/codex/`)
- **Components**: `install.sh`, `uninstall.sh`.
- **CRITICAL DEFECTS**:
  1. **NO `SKILL.md` EXISTS** in `adapters/codex/`.
  2. **Erroneous Hermes Copy-Paste**: `adapters/codex/install.sh` lines 1–15:
     ```bash
     # install.sh — Instalador del plugin Hermes para video-intake-knowledge
     PREFIX="${PREFIX:-$HOME/.hermes}"
     ```
     It installs into `$HOME/.hermes`, writes Hermes `registry.yaml`, and has zero OpenAI Codex or Codex CLI logic! It is completely non-functional for Codex.

#### F. Cursor
- **Status**: **100% MISSING**.
- No `adapters/cursor/` directory exists.
- No `install.sh --cursor` flag exists.
- No `.cursorrules` or `.cursor/skills/` definition exists.
- R2 explicitly mandates support for Cursor: *"para que la experiencia conversacional interactiva en 2 fases sea 100% fluida y natural en todos los entornos de agentes (Hermes Agent, AGY, Claude Code, OpenCode, Codex, Cursor)"*.

---

## 3. Investigation of the 2-Phase Interactive Workflow

### 3.1 Specification vs Reality

R2 defines:
- **Phase 1 (Extraction Menu)**: Prompt the user for layers to extract:
  1. Video local download
  2. Audio local download
  3. Audio transcription with timestamps
  4. Audio context (summary, key points, topics)
  5. Visual context (keyframes & OCR for diagrams, schemas, workflows)
  6. All of the above
- **Phase 2 (Knowledge Routing)**: Interactive dialogue to route the extracted knowledge:
  1. Apply as visible message in current session
  2. Compact working context injection into current session
  3. Store into existing external memory bank (e.g., Ideas Bank)
  4. Create new dedicated memory bank
  5. Ideate and scaffold tools / skills / agents via intelligent analysis & scaffolding
  6. Keep local artifacts only

### 3.2 Where Phase 1 and Phase 2 Live in the Codebase

1. **Script Implementation**:
   - `scripts/interactive.py`: Implements Phase 1 interactive prompt (lines 151–168) and Phase 2 knowledge routing (line 176).
   - `packages/video_intake_core/orchestrator.py`:
     - `check_and_extract(sources, operations, output_dir)` executes the layers.
     - `route_extracted_knowledge(artifacts, choice, interactive, extra_input)` implements Phase 2 choices 1 through 6.
2. **CLI Decoupling Defect**:
   - When a user or agent invokes the primary CLI command:
     `video-intake extract <URL_OR_FILE>`
     In `packages/video_intake_core/cli/__init__.py` lines 430–459:
     ```python
     select_raw = getattr(args, "select", "6") or "6"
     operations = parse_extraction_choices(select_raw)
     artifacts = check_and_extract(sources, operations, Path(root_out))
     ```
     **It immediately executes full extraction (`--select 6`) without asking Phase 1 questions, and immediately terminates without presenting Phase 2 knowledge routing!**
   - The primary CLI does not expose an interactive conversational loop. The user is forced to run a separate script: `python3 scripts/interactive.py`.
   - **Elevation Requirement**: `video-intake` CLI must either have an `interactive` command (`video-intake interactive <URL>`) or auto-detect interactive TTY mode in `video-intake extract` when `--select` is not supplied.

### 3.3 Menu Parser Redundancy (SSoT Violation)

The codebase has three separate implementations of selection parsing:
1. `video_intake_core.cli.menu.parse_menu_selection`: Returns `list[int] | bool`. Supports `"todo"` -> `[1, 2, 3, 4, 5, 6]`.
2. `video_intake_core.orchestrator.parse_extraction_choices`: Returns `set[int]`. Supports `"todo"` / `"6"` -> `{1, 2, 3, 4, 5}`.
3. `video_intake_core.cli._parse_selections`: Returns `set[str]` (`{"1", "2", ...}`).

These must be consolidated into a single parser adhering to Ground Truth.

---

## 4. `video-intake proposals --scaffold {skill,tool,agent}` & Template Generation

### 4.1 CLI Command State

File: `packages/video_intake_core/cli/proposals.py` (151 lines)
- Registered as `video-intake proposals` in `video_intake_core/cli/__init__.py:1145`.
- Arguments:
  - `--job-id JOB_ID`: ID of the job or path to manifest. If omitted, finds the most recent job in `./artifacts`.
  - `--scaffold {skill,tool,agent,all}`: Directly generates scaffolding.
  - `--output, -o OUTPUT`: Output directory (default `./generated`).
  - `--artifacts-dir ARTIFACTS_DIR`: Base directory for artifacts (default `./artifacts`).

### 4.2 Template Generation Logic

File: `packages/video_intake_core/orchestrator.py:338` (`generate_asset_scaffold`)
- Inputs: `asset_type`, `asset_name`, `artifacts`, `output_base`.
- Outputs:
  1. **SKILL**:
     - Writes `<output_base>/<sanitized_name>/SKILL.md`.
     - Valid YAML frontmatter: `name`, `description`, `version: 1.0.0`.
     - Sections: Resumen, Instrucciones Paso a Paso, Conocimiento de Audio Extraído, Contexto Visual y Diagramas.
  2. **TOOL**:
     - Writes `<output_base>/<sanitized_name>/tool.py`.
     - Executable permissions (`0o755`).
     - CLI argument parsing (`argparse`).
  3. **AGENTE**:
     - Writes `<output_base>/<sanitized_name>/agent.yaml`.
     - Writes `<output_base>/<sanitized_name>/prompts/system.md`.
     - Includes operational context, mission, and video source reference.

### 4.3 Evaluation Against Acceptance Criteria

Criterion: *"El comando `video-intake proposals --scaffold {skill,tool,agent}` genera andamiajes funcionales y sintácticamente válidos basados en el contenido extraído."*

- **Syntactic Validity**: **PASS**. Verified by actual generation and inspection of `SKILL.md` (valid markdown/frontmatter), `tool.py` (valid Python 3 AST), `agent.yaml` (valid YAML parser).
- **Template Sophistication Gaps**:
  - The generated `tool.py` currently contains a placeholder execution print statement rather than scaffolding functions tailored to detected video verbs/actions.
  - `agent.yaml` hardcodes capabilities (`ejecucion_guiada`, `analisis_contextual`) rather than deriving capabilities from extracted keywords.
  - `SKILL.md` step instructions are static generic steps ("1. Preparación y Contexto...", "2. Ejecución del Flujo...") rather than breaking down timestamped chapter headings or audio context points.
- **Documentation Gap**:
  - The `video-intake proposals` command is completely missing from Section 5 of root `SKILL.md`.

---

## 5. CLI Architecture & Dual-Implementation Duplication

Investigation revealed a severe code organization defect in `packages/video_intake_core/cli/`:

```
packages/video_intake_core/cli/
├── __init__.py       <-- 1187-line MONOLITH with inline implementations of:
│                         cmd_doctor, cmd_inspect, cmd_extract, cmd_batch,
│                         cmd_status, cmd_cancel, cmd_artifacts, cmd_export,
│                         cmd_cleanup, cmd_config_validate, cmd_self_test,
│                         cmd_models_*
├── artifacts.py      <-- Parallel modular implementation (largely uncalled)
├── cleanup.py        <-- Parallel modular implementation (largely uncalled)
├── config_cmd.py     <-- Parallel modular implementation (largely uncalled)
├── doctor.py         <-- Parallel modular implementation (largely uncalled)
├── export.py         <-- Parallel modular implementation (largely uncalled)
├── extract.py        <-- Parallel modular implementation (largely uncalled)
├── memory.py         <-- Properly delegated from __init__.py
├── menu.py           <-- Helper module
├── models.py         <-- Parallel modular implementation (largely uncalled)
├── proposals.py      <-- Properly delegated from __init__.py
└── status.py         <-- Parallel modular implementation (largely uncalled)
```

### Consequences:
1. **SSoT Violation**: If an engineer modifies `packages/video_intake_core/cli/extract.py`, the CLI behavior does not change because `cli/__init__.py:1024` uses its own internal `cmd_extract`!
2. **Depressed Test Coverage**:
   - `cli/status.py`: 9% coverage
   - `cli/config_cmd.py`: 12% coverage
   - `cli/artifacts.py`: 15% coverage
   - `cli/export.py`: 15% coverage
   - `cli/extract.py`: 19% coverage
   - `cli/models.py`: 19% coverage
   Because these files are dead code bypassed by the monolith.
3. **Inconsistent Arguments**:
   - `cli/extract.py` defines arguments `url`, `--output`, `--operations`, `--no-wait`.
   - `cli/__init__.py` defines arguments `source`, `--select`, `--file`.
   They represent two conflicting interfaces for the exact same command.

---

## 6. Comprehensive Gap Analysis Matrix (R2)

| Requirement / Criterion | Status | Concrete Evidence / Finding | Impact & Priority |
|---|---|---|---|
| **R2.1: Canonical SKILL.md Specification** | **FAIL** | 7 conflicting `SKILL.md` files exist. Root `SKILL.md` lacks standard YAML frontmatter. References 3 phases under a "2 Fases" header. Section 5 omits `proposals`. | **HIGH**: Agents receive contradictory operational instructions and licenses. |
| **R2.2: Universal Multi-Agent Integration** | **FAIL** | - **Cursor**: Completely missing (no adapter, no installer flag).<br>- **Codex**: Broken (no SKILL.md, install.sh installs Hermes to `~/.hermes`).<br>- **AGY**: Lacks Phase 2 knowledge routing; uses obsolete `vitk`.<br>- **Hermes**: Broken relative path in `install.sh`; uses `vitk` instead of `video-intake`.<br>- **Claude Code & OpenCode**: 507-line legacy duplicate files. | **CRITICAL**: Universal agent portability claim fails acceptance criteria. |
| **R2.3: `install.sh` Agent Support** | **FAIL** | `--cursor` is missing. `--all` does not configure Cursor. Non-Hermes integrations only link root `SKILL.md` and ignore adapter directories. | **HIGH**: Agent setup fails or requires manual patching. |
| **R2.4: 2-Phase Conversational Workflow** | **PARTIAL** | Fully implemented in `scripts/interactive.py`, but completely absent from `video-intake extract` CLI (which runs non-interactively without prompting). | **HIGH**: Users/agents using CLI cannot access the conversational menu. |
| **R2.5: Scaffolding Command & Templates** | **PASS WITH GAPS** | `video-intake proposals --scaffold {skill,tool,agent}` is functional and produces valid syntax. However, templates rely on static placeholders and command is omitted from `SKILL.md`. | **MEDIUM**: Works mechanically, but lacks technical refinement and discoverability. |
| **R2.6: SSoT and Clean CLI Architecture** | **FAIL** | 1187-line monolith in `cli/__init__.py` duplicates 8 modular files (`extract.py`, `status.py`, etc.), causing 3 different menu parsers and dead code. | **HIGH**: Severe technical debt and barrier to achieving 95% test coverage (R4). |

---

## 7. Actionable Architectural Recommendations

To elevate `video-intake-knowledge` to world-class engineering standards according to Tony's Constitution:

### 1. Establish Absolute SSoT for `SKILL.md`
- Upgrade `/srv/video-intake-knowledge/SKILL.md` as the **Single Canonical Source of Truth**:
  - Add standard YAML frontmatter (`name`, `description`, `version: 1.0.0`).
  - Align numbering strictly to **2 Phases** (Phase 1: Extraction Menu; Phase 2: Knowledge Routing).
  - Add `video-intake proposals --scaffold {skill,tool,agent}` to Section 5.
  - Remove obsolete `skill/SKILL.md` (or replace with a symlink to root `SKILL.md`).
  - Eliminate all references to the obsolete command name `vitk` across all files.

### 2. Complete and Fix All Agent Adapters
- **Cursor**: Create `adapters/cursor/` with canonical `SKILL.md` symlink, `.cursorrules` integration prompt, and add `--cursor` to `install.sh` (targeting `~/.cursor` and workspace `.cursor/skills/`).
- **Codex**: Fix `adapters/codex/`: create Codex-tailored `SKILL.md`, rewrite `install.sh` to install to `~/.codex/skills/video-intake` without Hermes references.
- **Hermes**: Fix `adapters/hermes/install.sh` line 95 (fix path to `../../scripts/standalone_hermes.sh`), modernize `plugin.yaml` to invoke `video-intake` directly, remove Git memory references.
- **AGY**: Update `adapters/agy/SKILL.md` to include Phase 2 Knowledge Routing and `video-intake` command syntax.
- **Claude Code & OpenCode**: Replace 507-line duplicates with clean, concise host manifests referencing canonical `SKILL.md`.

### 3. Unify the CLI Architecture (Eliminate Monolith Duplication)
- Refactor `packages/video_intake_core/cli/__init__.py`:
  - Delegate all subcommands to their respective modular files (`cli/doctor.py`, `cli/extract.py`, `cli/status.py`, `cli/artifacts.py`, `cli/cleanup.py`, `cli/export.py`, `cli/models.py`, `cli/config_cmd.py`, `cli/proposals.py`, `cli/memory.py`).
  - Eliminate inline duplicate `cmd_*` functions.
  - Consolidate selection parsing into a single authoritative function in `cli/menu.py`.

### 4. Wire Interactive 2-Phase Flow into `video-intake` CLI
- Expose the interactive experience natively via CLI:
  - Add `video-intake interactive [URL]` or trigger interactive mode in `video-intake extract` when running in a TTY without `--select`.
  - Ensure Phase 2 routing is invoked immediately upon extraction completion in interactive mode.

### 5. Elevate Scaffolding Templates
- Enhance `generate_asset_scaffold` in `orchestrator.py`:
  - Dynamically populate `SKILL.md` step instructions using transcript timestamps or audio context summaries.
  - Include detected topic keywords in `agent.yaml` capabilities.
  - Generate clean docstrings and CLI flags in `tool.py` derived from the extracted metadata.

---

**Report verified against codebase Ground Truth at 2026-09-22T01:03:50+02:00.**
