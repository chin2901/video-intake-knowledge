"""Shared configuration and fixtures for stress test battery."""
import os
import pytest
import pytest_asyncio
import httpx

TARGET_URL = os.getenv("TARGET_URL", "http://127.0.0.1:8090")

# Verified open media URLs (Fast, stable, no datacenter bot-blocking)
MEDIA_FAST_DIRECT = "https://www.w3schools.com/html/mov_bbb.mp4"
MEDIA_ARCHIVE_ORG = "https://archive.org/details/BigBuckBunny_124"

CONCURRENCY_TIERS = [5, 10, 25, 50]

@pytest.fixture
def target_url():
    return TARGET_URL

@pytest_asyncio.fixture
async def async_client():
    limits = httpx.Limits(max_connections=150, max_keepalive_connections=75, keepalive_expiry=30.0)
    async with httpx.AsyncClient(base_url=TARGET_URL, http2=True, limits=limits, timeout=60.0) as client:
        yield client
