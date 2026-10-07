"""Concurrency & Load Testing Suite for /api/health, /api/info, and /api/process."""
import time
import asyncio
import statistics
import pytest
import httpx
from typing import NamedTuple, List, Dict, Any, Optional

class LoadMetrics(NamedTuple):
    tier: int
    total_requests: int
    success_count: int
    error_count: int
    p50_ms: float
    p90_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float
    mean_ms: float
    throughput_rps: float
    status_codes: Dict[int, int]
    latencies: List[float]

def calculate_metrics(tier: int, latencies: List[float], status_codes: Dict[int, int], wall_clock_sec: float) -> LoadMetrics:
    if not latencies:
        return LoadMetrics(tier, 0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, {}, [])
    sorted_lats = sorted(latencies)
    n = len(sorted_lats)
    p50 = sorted_lats[int(0.50 * (n - 1))]
    p90 = sorted_lats[int(0.90 * (n - 1))]
    p95 = sorted_lats[int(0.95 * (n - 1))]
    p99 = sorted_lats[int(0.99 * (n - 1))]
    success = sum(count for code, count in status_codes.items() if 200 <= code < 300)
    errors = sum(count for code, count in status_codes.items() if code >= 400)
    return LoadMetrics(
        tier=tier,
        total_requests=n,
        success_count=success,
        error_count=errors,
        p50_ms=round(p50, 2),
        p90_ms=round(p90, 2),
        p95_ms=round(p95, 2),
        p99_ms=round(p99, 2),
        min_ms=round(sorted_lats[0], 2),
        max_ms=round(sorted_lats[-1], 2),
        mean_ms=round(statistics.mean(sorted_lats), 2),
        throughput_rps=round(n / wall_clock_sec, 2) if wall_clock_sec > 0 else 0.0,
        status_codes=status_codes,
        latencies=latencies
    )

async def run_concurrent_batch(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    json_data: Optional[dict],
    concurrency: int,
    total_requests: int,
    cleanup_downloads: bool = False
) -> LoadMetrics:
    sem = asyncio.Semaphore(concurrency)
    latencies: List[float] = []
    status_codes: Dict[int, int] = {}
    download_urls: List[str] = []
    lock = asyncio.Lock()

    async def worker():
        async with sem:
            t0 = time.perf_counter()
            code = 599
            dl_url = None
            try:
                if method.upper() == "GET":
                    resp = await client.get(path)
                else:
                    resp = await client.post(path, json=json_data)
                lat_ms = (time.perf_counter() - t0) * 1000.0
                code = resp.status_code
                if code == 200 and cleanup_downloads:
                    data = resp.json()
                    dl_url = data.get("download_url")
            except Exception:
                lat_ms = (time.perf_counter() - t0) * 1000.0
                code = 599

            async with lock:
                latencies.append(lat_ms)
                status_codes[code] = status_codes.get(code, 0) + 1
                if dl_url:
                    download_urls.append(dl_url)

    t_start = time.perf_counter()
    tasks = [asyncio.create_task(worker()) for _ in range(total_requests)]
    await asyncio.gather(*tasks)
    t_wall = time.perf_counter() - t_start

    # If cleanup requested, download all generated files to trigger auto-purge
    if cleanup_downloads and download_urls:
        async def dl_worker(u: str):
            try:
                await client.get(u)
            except Exception:
                pass
        await asyncio.gather(*[dl_worker(u) for u in download_urls])
        await asyncio.sleep(0.5)

    return calculate_metrics(concurrency, latencies, status_codes, t_wall)

# ---- Pytest Test Cases ----

@pytest.mark.asyncio
@pytest.mark.parametrize("concurrency,total_requests", [(5, 25), (10, 50), (25, 100), (50, 250)])
async def test_concurrency_health(async_client, concurrency, total_requests):
    """Evaluates /api/health across 5, 10, 25, 50 concurrency."""
    metrics = await run_concurrent_batch(
        client=async_client,
        method="GET",
        path="/api/health",
        json_data=None,
        concurrency=concurrency,
        total_requests=total_requests
    )
    assert metrics.success_count == total_requests, f"Expected 100% 200 OK on /api/health, got: {metrics.status_codes}"
    assert metrics.error_count == 0
    assert metrics.p95_ms < 1000.0

@pytest.mark.asyncio
@pytest.mark.parametrize("concurrency,total_requests", [(5, 5), (10, 10), (25, 25), (50, 50)])
async def test_concurrency_info(async_client, concurrency, total_requests):
    """Evaluates /api/info across 5, 10, 25, 50 concurrency using valid media URL."""
    payload = {"url": "https://www.w3schools.com/html/mov_bbb.mp4"}
    metrics = await run_concurrent_batch(
        client=async_client,
        method="POST",
        path="/api/info",
        json_data=payload,
        concurrency=concurrency,
        total_requests=total_requests
    )
    assert metrics.success_count == total_requests, f"Expected 100% 200 OK on /api/info, got: {metrics.status_codes}"
    assert metrics.error_count == 0

@pytest.mark.asyncio
@pytest.mark.parametrize("concurrency,total_requests", [(5, 5), (10, 10), (25, 25), (50, 50)])
async def test_concurrency_process_markdown(async_client, concurrency, total_requests):
    """Evaluates /api/process (markdown mode) measuring thread queue scaling."""
    payload = {
        "url": "https://www.w3schools.com/html/mov_bbb.mp4",
        "mode": "markdown"
    }
    metrics = await run_concurrent_batch(
        client=async_client,
        method="POST",
        path="/api/process",
        json_data=payload,
        concurrency=concurrency,
        total_requests=total_requests,
        cleanup_downloads=True
    )
    assert metrics.success_count == total_requests, f"Process markdown failed: {metrics.status_codes}"
    assert metrics.error_count == 0
