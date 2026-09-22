# Task Assignment: E2E Test Writer (Opaque-Box 4-Tier Test Suite)

## Context
- Project Root: `/srv/video-intake-knowledge`
- Working Directory: `/srv/video-intake-knowledge/.agents/teamwork_preview_test_writer_e2e`
- Authoritative Requirements: `/srv/video-intake-knowledge/.agents/ORIGINAL_REQUEST.md` (MUST read in full)
- System Constitution: `/home/aibos/AGENTS.md` (MUST adhere strictly)
- Scope & Architecture: `/srv/video-intake-knowledge/.agents/PROJECT.md`

## Objectives
Design and implement the comprehensive 4-Tier Opaque-Box E2E Test Suite and Infrastructure:
1. Methodology: Category-Partition + Boundary Value Analysis + Pairwise Combinatorial + Real-World Workload Testing.
2. Architecture:
   - Create `tests/e2e/` test suite that exercises `video-intake` CLI and public contracts as an end user / agent would.
   - Use mock fixtures and synthetic media in `tests/fixtures/` so tests run deterministically and fast without requiring external internet access or third-party API keys.
3. Test Tiers:
   - **Tier 1 (Feature Coverage)**: >=5 tests per core feature across inspection, extraction layers, CLI, agent adapters, security gateway, memory isolation, batch processing, and proposal scaffolding.
   - **Tier 2 (Boundary & Corner Cases)**: Edge cases, zero/empty inputs, non-standard URLs, malicious SSRF formats (DNS aliases, octal, decimal, IPv6), traversal strings, prompt injection payloads, missing tools graceful degradation.
   - **Tier 3 (Cross-Feature Combinations)**: Pairwise interactions (e.g. batch + memory isolation, extraction + dynamic proposal scaffolding, inspect + sanitize + extract).
   - **Tier 4 (Real-World Application Scenarios)**: Realistic end-to-end agent workflows (e.g., download video -> extract subtitles -> summarize -> scaffold skill/tool/agent -> verify generated syntax and execution).
4. Documentation & Publishing:
   - Create `/srv/video-intake-knowledge/TEST_INFRA.md` following the project template.
   - When test suite is complete and verified with pytest, publish `/srv/video-intake-knowledge/TEST_READY.md`.
5. Handoff
## 2026-09-22T01:06:52Z
You are the E2E Test Writer for video-intake-knowledge.
Working Directory: /srv/video-intake-knowledge/.agents/teamwork_preview_test_writer_e2e
Project Root: /srv/video-intake-knowledge
Authoritative Requirements: Read /srv/video-intake-knowledge/.agents/ORIGINAL_REQUEST.md
System Constitution: Read and adhere strictly to /home/aibos/AGENTS.md
Scope & Architecture: Read /srv/video-intake-knowledge/.agents/PROJECT.md
Your Dispatch Brief: Read /srv/video-intake-knowledge/.agents/teamwork_preview_test_writer_e2e/DISPATCH.md

Your mission:
Design and implement the complete 4-tier opaque-box E2E test suite in `tests/e2e/` (Tiers 1-4) covering all 28 features (F1-F28).
Create `/srv/video-intake-knowledge/TEST_INFRA.md`.
Run tests with `pytest tests/e2e -v`. When all tests pass, publish `/srv/video-intake-knowledge/TEST_READY.md`.
Deliver your report in `handoff.md` and notify the orchestrator via send_message.

## 2026-09-21T23:13:10Z
From: parent (b72916b2-018f-4bba-9bd2-a657cf9de0ac)
Context: Circular import between orchestrator.py and batch.py
Content: Worker M1 has been instructed to fix the circular import between orchestrator.py and batch.py immediately.
Action: Proceed with test structure and mock test definitions while Worker M1 completes the fix.
