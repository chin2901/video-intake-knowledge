"""
video_intake_core — Video content extraction, transcription, and knowledge generation.

This package provides a portable core for extracting content from videos across
multiple platforms (YouTube, Facebook, Instagram, TikTok) and local files.
It is designed to be integrated into agent environments via plugins, skills, or
direct CLI usage.

Architecture:
    acquisition/   — Source detection and URL resolution
    inspection/    — Video metadata inspection via ffprobe
    audio/         — Audio extraction and normalization
    transcription/ — Audio-to-text transcription (whisper, captions)
    visual/        — Scene detection, keyframe extraction, visual analysis
    ocr/           — Optical character recognition on video frames
    context/       — Knowledge extraction from audio and visual content
    artifacts/     — Artifact generation and management
    jobs/          — Job orchestration and state management
    schemas/       — JSON schema definitions
    policies/      — Model and processing policy configuration
    storage/       — Local storage and caching
    security/      — Security validation and sanitization
    memory/        — Memory provider abstraction
    cli/           — Command-line interface
"""

from __future__ import annotations

__version__ = "0.1.0"
__author__ = "Video Intake Knowledge Project"
