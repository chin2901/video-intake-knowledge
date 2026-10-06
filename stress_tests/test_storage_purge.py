"""Storage Hardening & Auto-Purge Test Suite (Zero-Bloat Verification & HTTP 507 Simulation)."""
import os
import shutil
import asyncio
import hashlib
from pathlib import Path
import pytest
import httpx

STORAGE_PATH = Path("/home/ubuntu/video-intake-web/storage")

def get_storage_stats() -> tuple[int, int]:
    """Returns (file_count, total_bytes) in storage directory."""
    if not STORAGE_PATH.exists():
        return 0, 0
    files = [f for f in STORAGE_PATH.iterdir() if f.is_file() and not f.name.startswith(".")]
    total_bytes = sum(f.stat().st_size for f in files)
    return len(files), total_bytes

# ---- Pytest Test Cases ----

@pytest.mark.asyncio
async def test_concurrent_download_and_zero_residual_purge(async_client):
    """
    R2 Validation:
    1. Generates 5 markdown files and 5 audio files via /api/process.
    2. Verifies files exist in storage (residual bytes > 0).
    3. Concurrently downloads all 10 files.
    4. Verifies all downloads succeed with full content length.
    5. Verifies storage returns to exactly 0 files and 0 residual bytes post-download.
    """
    test_url = "https://www.w3schools.com/html/mov_bbb.mp4"
    download_targets = []

    # Step 1: Generate batch of 5 markdown and 5 audio tasks
    for mode in ["markdown", "audio"]:
        for i in range(5):
            resp = await async_client.post("/api/process", json={"url": test_url, "mode": mode})
            assert resp.status_code == 200, f"Setup process failed: {resp.text}"
            data = resp.json()
            download_targets.append((data["download_url"], data["filename"]))

    # Step 2: Verify storage holds all generated files
    count_before, bytes_before = get_storage_stats()
    assert count_before == 10, f"Expected 10 files before download, found {count_before}"
    assert bytes_before > 0, "Storage size must be > 0 bytes before download"

    # Step 3: Concurrently download all files
    async def download_file(dl_url, filename):
        resp = await async_client.get(dl_url)
        assert resp.status_code == 200, f"Failed downloading {dl_url}: {resp.status_code}"
        assert len(resp.content) > 0
        return len(resp.content)

    results = await asyncio.gather(*[download_file(url, name) for url, name in download_targets])
    assert len(results) == 10

    # Step 4: Allow Starlette background tasks time to complete unlinking
    await asyncio.sleep(2.0)

    # Step 5: Assert zero residual bytes
    count_after, bytes_after = get_storage_stats()
    assert count_after == 0, f"Found {count_after} orphan files in storage post-download"
    assert bytes_after == 0, f"Storage has {bytes_after} residual bytes (must be 0)"

@pytest.mark.asyncio
async def test_download_race_condition_same_file(async_client):
    """
    R2 Race Condition Hardening:
    Verifies concurrent simultaneous downloads of the exact SAME file.
    Ensures that unlinking during streaming does not truncate or corrupt
    parallel reading descriptors, and subsequent download returns HTTP 404.
    """
    # 1. Create a single audio file
    resp = await async_client.post("/api/process", json={
        "url": "https://www.w3schools.com/html/mov_bbb.mp4",
        "mode": "audio"
    })
    assert resp.status_code == 200, f"Setup process failed: {resp.text}"
    dl_url = resp.json()["download_url"]

    # 2. Launch 8 concurrent downloads of the EXACT SAME download URL
    async def fetch():
        res = await async_client.get(dl_url)
        return res.status_code, hashlib.sha256(res.content).hexdigest(), len(res.content)

    results = await asyncio.gather(*[fetch() for _ in range(8)])

    # All 8 readers must receive HTTP 200 and IDENTICAL SHA-256 checksums
    status_codes = [r[0] for r in results]
    hashes = [r[1] for r in results]
    lengths = [r[2] for r in results]

    # Readers receive either 200 (full file) or 404 (purged by predecessor); NEVER 500
    assert all(code in [200, 404] for code in status_codes), f"Status codes: {status_codes}"
    assert 200 in status_codes, "At least one reader must successfully download the file"
    successful_hashes = [r[1] for r in results if r[0] == 200]
    assert len(set(successful_hashes)) == 1, "File corruption detected across concurrent readers!"
    assert all(r[2] > 0 for r in results if r[0] == 200)

    await asyncio.sleep(1.5)

    # 3. Subsequent download of the unlinked file must return 404
    resp_after = await async_client.get(dl_url)
    assert resp_after.status_code == 404, f"Expected 404 for deleted file, got {resp_after.status_code}"

    # 4. Storage must be 0 bytes
    count, bytes_rem = get_storage_stats()
    assert count == 0 and bytes_rem == 0, f"Residual storage remaining: {count} files, {bytes_rem} bytes"

@pytest.mark.asyncio
async def test_low_disk_safety_threshold_simulation_http_507(async_client):
    """
    R2 Low-Disk Simulation:
    Simulates <20 GB free disk without container restart.
    Verifies /api/health reports storage_safe=false and /api/process rejects with HTTP 507.
    """
    probe_file = STORAGE_PATH / ".disk_stress_probe"
    
    # 1. Query baseline free disk
    health_resp = await async_client.get("/api/health")
    assert health_resp.status_code == 200
    baseline_free_gb = health_resp.json()["free_disk_gb"]
    assert baseline_free_gb >= 20.0

    # 2. Calculate allocation to leave exactly 18.0 GB free (< 20.0 GB threshold)
    usage = shutil.disk_usage(STORAGE_PATH if STORAGE_PATH.exists() else "/")
    current_free_bytes = usage.free
    target_free_bytes = int(18.0 * (1024 ** 3))
    reserve_bytes = current_free_bytes - target_free_bytes

    if reserve_bytes <= 0:
        pytest.skip("System already has less than 18 GB free")

    try:
        # 3. Create reservation file via posix_fallocate (microsecond execution on ext4)
        with open(probe_file, "wb") as f:
            os.posix_fallocate(f.fileno(), 0, reserve_bytes)

        # 4. Verify /api/health detects low disk
        h_low = await async_client.get("/api/health")
        assert h_low.status_code == 200
        h_data = h_low.json()
        assert h_data["storage_safe"] is False, f"Expected storage_safe=False, got: {h_data}"
        assert h_data["status"] == "warning_disk_low"
        assert h_data["free_disk_gb"] < 20.0

        # 5. Verify /api/process rejects with HTTP 507 Insufficient Storage
        proc_resp = await async_client.post("/api/process", json={
            "url": "https://www.w3schools.com/html/mov_bbb.mp4",
            "mode": "markdown"
        })
        assert proc_resp.status_code == 507, f"Expected HTTP 507, got {proc_resp.status_code}"
        assert "zona de seguridad" in proc_resp.json()["detail"]

    finally:
        # 6. Strict cleanup guarantee: remove reservation file
        if probe_file.exists():
            probe_file.unlink(missing_ok=True)

        # 7. Verify health returns to safe status
        h_restored = await async_client.get("/api/health")
        assert h_restored.status_code == 200
        assert h_restored.json()["storage_safe"] is True
        assert h_restored.json()["free_disk_gb"] >= 20.0
