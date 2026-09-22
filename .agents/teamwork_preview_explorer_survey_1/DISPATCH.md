# Task Assignment: Survey Explorer 1 (Core Architecture, Performance & Ingestion Engine - R1)

## Context
- Project Root: `/srv/video-intake-knowledge`
- Working Directory: `/srv/video-intake-knowledge/.agents/teamwork_preview_explorer_survey_1`
- Authoritative Requirements: `/srv/video-intake-knowledge/.agents/ORIGINAL_REQUEST.md` (MUST read in full)
- System Constitution: `/home/aibos/AGENTS.md` (MUST adhere strictly)

## Objectives
Map the full scope and current state of the codebase focusing on R1 (Core Engine & Performance):
1. Analyze repository layout, entry points, packages, and dependency graph.
2. Investigate the media acquisition & extraction core (YouTube, Facebook, Instagram, TikTok, and local files).
3. Evaluate current metadata inspection mechanism and why it may not meet sub-300ms latency.
4. Evaluate batch processing, concurrency, memory/CPU consumption, streaming `ffprobe` opportunities.
5. Audit native fallbacks (yt-dlp, ffmpeg) and optional AI fallbacks (Whisper, Tesseract OCR).
6. Document concrete gaps between current implementation and R1 requirements & acceptance criteria.
7. Deliver a comprehensive survey report in `/srv/video-intake-knowledge/.agents/teamwork_preview_explorer_survey_1/survey_report.md` and complete handoff.md.

## 2026-09-21T23:00:19Z
You are Explorer 1 for the video-intake-knowledge engineering elevation project.
Your Working Directory: /srv/video-intake-knowledge/.agents/teamwork_preview_explorer_survey_1
Project Root: /srv/video-intake-knowledge
Authoritative Requirements: Read /srv/video-intake-knowledge/.agents/ORIGINAL_REQUEST.md
System Constitution: Read and adhere strictly to /home/aibos/AGENTS.md
Your Dispatch Brief: Read /srv/video-intake-knowledge/.agents/teamwork_preview_explorer_survey_1/DISPATCH.md

Your mission:
Survey the codebase focusing on R1 (Core Architecture, Performance & Platform Ingestion):
1. Codebase layout, entry points, dependencies, packaging.
2. Media acquisition core (YouTube, Facebook, Instagram, TikTok, local files).
3. Metadata inspection mechanism and latency benchmarks/bottlenecks (<300ms requirement).
4. Batch processing, concurrency, memory/CPU consumption, streaming ffprobe.
5. Native fallbacks (yt-dlp, ffmpeg) and optional AI fallbacks (Whisper, Tesseract).
6. Concrete gaps against R1 requirements and acceptance criteria.

Write your findings to:
`/srv/video-intake-knowledge/.agents/teamwork_preview_explorer_survey_1/survey_report.md`
and complete your `handoff.md`. Send a message when finished with key highlights.
