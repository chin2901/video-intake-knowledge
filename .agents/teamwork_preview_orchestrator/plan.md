# Orchestration Plan: video-intake-knowledge Engineering Elevation

## 1. Objectives & Scope
Elevate `video-intake-knowledge` to world-class open-source excellence across all requirements R1-R5:
- R1: High-performance ingestion & extraction engine (sub-300ms metadata inspection, efficient parallel batch processing, low memory/CPU footprint, robust native fallbacks).
- R2: Top-tier universal agent experience (SKILL.md and multi-platform adapters for Hermes, AGY, Claude Code, OpenCode, Codex, Cursor with 2-phase interactive workflow and proposal scaffolding).
- R3: Hardened security & strict memory isolation (SSRF defense, path traversal prevention, prompt/subtitle injection sanitization, memory.db strictly isolated to ~/.video-intake/memory.db, git working tree clean of db/cache files).
- R4: Code quality, strict typing, and elite test suite (>95% test coverage, 0 ruff errors, strict typing without errors, CI workflows).
- R5: World-class developer documentation (badges, Mermaid architecture diagrams, formal data schemas, quickstart and integration guides).

## 2. Orchestration Architecture
Following the Project Pattern with Dual Track:
- **Phase 0: Survey**:
  Spawn 3 Explorers in parallel to inspect the full codebase, existing test harness, CLI, dependencies, security surface, and documentation.
  Synthesize findings into `PROJECT.md` (Feature Inventory, Architecture, Milestones, Interface Contracts, Code Layout).
- **Phase 1: Dual Track Execution**:
  - **E2E Testing Track**: Build comprehensive 4-tier opaque-box test suite + runner + `TEST_INFRA.md` -> `TEST_READY.md`.
  - **Implementation Track**:
    - Milestone M1: Core ingestion & extraction engine optimization (R1)
    - Milestone M2: Universal Agent Experience, 2-phase dialogue & scaffolding (R2)
    - Milestone M3: Security hardening, SSRF, injection sanitization, memory isolation (R3)
    - Milestone M4: Code quality, typing, ruff, CI workflows (>95% coverage) (R4)
    - Milestone M5: Documentation, README badges, Mermaid diagrams, schemas (R5)
- **Phase 2: Final Milestone & Adversarial Hardening**:
  - Phase 2A: Verify 100% pass rate on E2E test suite (Tiers 1-4).
  - Phase 2B: Challenger-driven adversarial coverage hardening (Tier 5).
  - Phase 2C: Full doctor and acceptance criteria verification.
  - Final report to Sentinel / Parent.

## 3. Governance & Quality Gates
- Dispatch-only: Orchestrator writes zero implementation code and runs zero build/tests directly.
- Every milestone runs Explorer -> Worker -> Reviewers (x2) -> Challengers (x2) -> Forensic Auditor -> Gate.
- Zero tolerance on forensic audit failures (instant binary veto).
- Strict adherence to AibOS Constitution (/home/aibos/AGENTS.md): "Menos es Más", zero speculation, ground truth verification.
