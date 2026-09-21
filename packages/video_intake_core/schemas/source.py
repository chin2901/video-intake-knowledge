"""
Source data models for video_intake_core.

Defines data classes for representing video sources, source types, and
resolved URLs used throughout the acquisition and processing pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class SourceType(str, Enum):
    """Types of video sources supported by the system."""

    YOUTUBE = "youtube"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    LOCAL_FILE = "local_file"


@dataclass
class Source:
    """
    Represents a video source (URL or local file).

    Attributes:
        source_type: Type of video source (youtube, facebook, instagram, tiktok, local_file).
        url: Canonical URL of the video.
        raw_url: Original URL as provided by the user (may differ from canonical).
        platform: Platform name (e.g., 'youtube', 'facebook').
        title: Video title if known.
        author: Author/channel/creator if known.
        duration_seconds: Duration in seconds if known.
        thumbnail_url: Thumbnail URL if available.
        metadata: Additional platform-specific metadata.
    """

    source_type: SourceType
    url: str
    raw_url: str = ""
    platform: str = ""
    title: str = ""
    author: str = ""
    duration_seconds: float = 0.0
    thumbnail_url: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "source_type": self.source_type.value,
            "url": self.url,
            "raw_url": self.raw_url,
            "platform": self.platform,
            "title": self.title,
            "author": self.author,
            "duration_seconds": self.duration_seconds,
            "thumbnail_url": self.thumbnail_url,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Source:
        """Create a Source from dictionary representation."""
        source_type = data.get("source_type", "local_file")
        if isinstance(source_type, str):
            source_type = SourceType(source_type)
        return cls(
            source_type=source_type,
            url=data.get("url", ""),
            raw_url=data.get("raw_url", ""),
            platform=data.get("platform", ""),
            title=data.get("title", ""),
            author=data.get("author", ""),
            duration_seconds=float(data.get("duration_seconds", 0)),
            thumbnail_url=data.get("thumbnail_url", ""),
            metadata=data.get("metadata", {}),
        )

    def __str__(self) -> str:
        return f"Source({self.source_type.value}: {self.url})"


@dataclass
class ResolvedURL:
    """
    Represents a resolved video URL with metadata.

    Attributes:
        original_url: The original URL as provided.
        resolved_url: The resolved/canonical URL.
        source_type: Type of source.
        canonical_id: Canonical video ID if extractable.
        title: Video title if known.
        duration_seconds: Duration in seconds if known.
        thumbnail_url: Thumbnail URL if available.
        resolved_at: Timestamp when the URL was resolved.
        error: Error message if resolution failed.
        redirect_chain: List of URLs in the redirect chain.
    """

    original_url: str
    resolved_url: str
    source_type: SourceType
    canonical_id: str = ""
    title: str = ""
    duration_seconds: float = 0.0
    thumbnail_url: str = ""
    resolved_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    error: str | None = None
    redirect_chain: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Check if the URL was resolved successfully."""
        return self.error is None and self.resolved_url

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "original_url": self.original_url,
            "resolved_url": self.resolved_url,
            "source_type": self.source_type.value,
            "canonical_id": self.canonical_id,
            "title": self.title,
            "duration_seconds": self.duration_seconds,
            "thumbnail_url": self.thumbnail_url,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "error": self.error,
            "redirect_chain": self.redirect_chain,
        }

    def __str__(self) -> str:
        status = "OK" if self.is_valid else f"FAILED: {self.error}"
        return f"ResolvedURL({self.source_type.value}: {self.original_url} -> {self.resolved_url} [{status}])"
