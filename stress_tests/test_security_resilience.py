"""
Security & Resilience Audit Test Suite (R3)
Validates 25+ malicious/SSRF vectors, 0% unhandled 500 errors, and 0 container restarts.
"""
import os
import subprocess
import pytest
import httpx

TARGET_URL = os.getenv("TARGET_URL", "http://127.0.0.1:8090")
TIMEOUT = float(os.getenv("TEST_TIMEOUT", "10.0"))

def get_container_inspect(container_name: str = "video-intake-web"):
    """Captures container inspect data if running on VM."""
    try:
        res = subprocess.run(
            ["docker", "inspect", container_name, "--format",
             "{{.State.Status}}|{{.RestartCount}}|{{.State.StartedAt}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}"],
            capture_output=True, text=True, check=True
        )
        parts = res.stdout.strip().split("|")
        return {
            "status": parts[0],
            "restart_count": int(parts[1]),
            "started_at": parts[2],
            "health_status": parts[3] if len(parts) > 3 else "unknown"
        }
    except Exception:
        return None

class TestBoundaryAndMalformedInputs:
    """Validates that boundary inputs and malformed payloads never leak HTTP 500."""

    @pytest.mark.asyncio
    async def test_info_empty_body(self, async_client):
        r = await async_client.post("/api/info", json={})
        assert r.status_code == 422
        assert r.status_code != 500

    @pytest.mark.asyncio
    async def test_info_null_url(self, async_client):
        r = await async_client.post("/api/info", json={"url": None})
        assert r.status_code == 422
        assert r.status_code != 500

    @pytest.mark.asyncio
    async def test_info_empty_url(self, async_client):
        r = await async_client.post("/api/info", json={"url": ""})
        assert r.status_code == 400
        assert r.status_code != 500

    @pytest.mark.asyncio
    async def test_info_whitespace_url(self, async_client):
        r = await async_client.post("/api/info", json={"url": "   \t\n  "})
        assert r.status_code == 400
        assert r.status_code != 500

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_val", [12345, True, ["https://example.com"], {"a": 1}])
    async def test_info_invalid_types(self, async_client, invalid_val):
        r = await async_client.post("/api/info", json={"url": invalid_val})
        assert r.status_code == 422
        assert r.status_code != 500

    @pytest.mark.asyncio
    async def test_info_malformed_url_garbage(self, async_client):
        r = await async_client.post("/api/info", json={"url": "not_a_valid_url_string"})
        assert r.status_code == 400
        assert r.status_code != 500

    @pytest.mark.asyncio
    async def test_info_scheme_only(self, async_client):
        r = await async_client.post("/api/info", json={"url": "https://"})
        assert r.status_code == 400
        assert r.status_code != 500

    @pytest.mark.asyncio
    @pytest.mark.parametrize("bad_proto", ["ftp://test.com/v.mp4", "javascript:alert(1)", "file:///etc/passwd"])
    async def test_info_unsupported_protocols(self, async_client, bad_proto):
        r = await async_client.post("/api/info", json={"url": bad_proto})
        assert r.status_code == 400
        assert r.status_code != 500

    @pytest.mark.asyncio
    async def test_info_oversized_url(self, async_client):
        oversized = "https://example.com/" + ("a" * 10000)
        r = await async_client.post("/api/info", json={"url": oversized})
        assert r.status_code in [400, 422]
        assert r.status_code != 500

    @pytest.mark.asyncio
    async def test_info_injection_strings(self, async_client):
        payloads = [
            "https://example.com/?q=<script>alert(1)</script>",
            "https://example.com/; rm -rf /; $(whoami)",
            "https://example.com/test' OR '1'='1"
        ]
        for p in payloads:
            r = await async_client.post("/api/info", json={"url": p})
            assert r.status_code in [400, 404]
            assert r.status_code != 500

    @pytest.mark.asyncio
    async def test_malformed_json_body(self, async_client):
        r = await async_client.post(
            "/api/info",
            content=b'{"url": "incomplete_json',
            headers={"Content-Type": "application/json"}
        )
        assert r.status_code in [400, 422]
        assert r.status_code != 500

class TestProcessEndpointResilience:
    """Validates /api/process input sanitization and exception normalization."""

    @pytest.mark.asyncio
    async def test_process_missing_mode(self, async_client):
        r = await async_client.post("/api/process", json={"url": "https://archive.org/details/test"})
        assert r.status_code == 422
        assert r.status_code != 500

    @pytest.mark.asyncio
    async def test_process_null_mode(self, async_client):
        r = await async_client.post("/api/process", json={"url": "https://archive.org/details/test", "mode": None})
        assert r.status_code == 422
        assert r.status_code != 500

    @pytest.mark.asyncio
    async def test_process_invalid_mode(self, async_client):
        r = await async_client.post("/api/process", json={"url": "https://archive.org/details/test", "mode": "invalid_mode"})
        assert r.status_code == 400
        assert r.status_code != 500

    @pytest.mark.asyncio
    async def test_process_empty_mode(self, async_client):
        r = await async_client.post("/api/process", json={"url": "https://archive.org/details/test", "mode": ""})
        assert r.status_code == 400
        assert r.status_code != 500

    @pytest.mark.asyncio
    async def test_process_empty_url(self, async_client):
        r = await async_client.post("/api/process", json={"url": "", "mode": "markdown"})
        assert r.status_code == 400
        assert r.status_code != 500

    @pytest.mark.asyncio
    async def test_process_malformed_url(self, async_client):
        r = await async_client.post("/api/process", json={"url": "xyz_not_a_url", "mode": "markdown"})
        assert r.status_code == 400
        assert r.status_code != 500

class TestSSRFResilience:
    """Validates that internal network probes are rejected cleanly without server errors."""

    @pytest.mark.asyncio
    async def test_ssrf_loopback_ipv4(self, async_client):
        r = await async_client.post("/api/info", json={"url": "http://127.0.0.1:8090"})
        assert r.status_code == 400
        assert r.status_code != 500

    @pytest.mark.asyncio
    async def test_ssrf_localhost(self, async_client):
        r = await async_client.post("/api/info", json={"url": "http://localhost:8090"})
        assert r.status_code == 400
        assert r.status_code != 500

    @pytest.mark.asyncio
    async def test_ssrf_loopback_ipv6(self, async_client):
        r = await async_client.post("/api/info", json={"url": "http://[::1]:8090"})
        assert r.status_code == 400
        assert r.status_code != 500

    @pytest.mark.asyncio
    async def test_ssrf_docker_bridge_gateway(self, async_client):
        r = await async_client.post("/api/info", json={"url": "http://172.18.0.1:8090"})
        assert r.status_code == 400
        assert r.status_code != 500

    @pytest.mark.asyncio
    async def test_ssrf_private_network(self, async_client):
        try:
            r = await async_client.post("/api/info", json={"url": "http://192.168.1.1:8090"})
            assert r.status_code in [400, 404]
            assert r.status_code != 500
        except httpx.TimeoutException:
            pytest.fail("SSRF probe triggered socket hang rather than clean rejection")

    @pytest.mark.asyncio
    async def test_ssrf_oracle_cloud_metadata(self, async_client):
        for path in ["/opc/v1/instance/", "/opc/v2/instance/"]:
            r = await async_client.post("/api/info", json={"url": f"http://169.254.169.254{path}"})
            assert r.status_code in [400, 403, 404]
            assert r.status_code != 500
            assert "compartmentId" not in r.text
            assert "canonicalName" not in r.text

class TestPathTraversalAndDownloadResilience:
    """Validates that download endpoints strictly reject traversal and non-existent files."""

    @pytest.mark.asyncio
    async def test_traversal_dot_dot(self, async_client):
        r = await async_client.get("/api/download/../../../../etc/passwd")
        assert r.status_code in [400, 404]
        assert "root:x:" not in r.text

    @pytest.mark.asyncio
    async def test_traversal_url_encoded(self, async_client):
        r = await async_client.get("/api/download/%2e%2e%2f%2e%2e%2fetc%2fpasswd")
        assert r.status_code in [400, 404]
        assert "root:x:" not in r.text

    @pytest.mark.asyncio
    async def test_traversal_env_secrets(self, async_client):
        r = await async_client.get("/api/download/.env")
        assert r.status_code == 404
        assert "TUNNEL_TOKEN" not in r.text

    @pytest.mark.asyncio
    async def test_download_nonexistent_file(self, async_client):
        r = await async_client.get("/api/download/00000000_nonexistent_video.mp4")
        assert r.status_code == 404
        assert r.json().get("detail") == "Archivo expirado o no encontrado"

class TestMethodAndRouteResilience:
    """Validates unhandled HTTP methods and non-existent paths."""

    @pytest.mark.asyncio
    async def test_method_not_allowed_post_health(self, async_client):
        r = await async_client.post("/api/health")
        assert r.status_code == 405
        assert r.status_code != 500

    @pytest.mark.asyncio
    async def test_method_not_allowed_delete_health(self, async_client):
        r = await async_client.delete("/api/health")
        assert r.status_code == 405
        assert r.status_code != 500

    @pytest.mark.asyncio
    async def test_nonexistent_route_404(self, async_client):
        r = await async_client.get("/api/nonexistent_path_probe_test")
        assert r.status_code == 404
        assert r.status_code != 500

class TestContainerStabilityAndZeroRestarts:
    """Validates container uptime, zero restarts, and immediate post-test liveness."""

    def test_container_zero_restarts(self):
        inspect_data = get_container_inspect()
        if inspect_data:
            assert inspect_data["status"] == "running"
            assert inspect_data["restart_count"] == 0
        else:
            pytest.skip("Docker CLI inspect not accessible in this context")

    @pytest.mark.asyncio
    async def test_post_audit_liveness(self, async_client):
        r = await async_client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") in ["healthy", "warning_disk_low"]
        assert data.get("storage_safe") is True
