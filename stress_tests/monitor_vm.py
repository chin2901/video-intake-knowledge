"""Telemetry Sampler for Oracle ARM64 VM and Docker Container."""
import os
import time
import subprocess
import asyncio
from typing import Dict, List, Any, Optional

def parse_memory_str(mem_str: str) -> float:
    """Parses memory string like '53.81MiB' or '1.2GiB' to MB."""
    clean = mem_str.strip()
    if clean.endswith("GiB"):
        return float(clean[:-3].strip()) * 1024.0
    elif clean.endswith("MiB"):
        return float(clean[:-3].strip())
    elif clean.endswith("KiB"):
        return float(clean[:-3].strip()) / 1024.0
    elif clean.endswith("B"):
        return float(clean[:-1].strip()) / (1024.0 * 1024.0)
    return 0.0

def get_container_metadata(container_name: str = "video-intake-web") -> Dict[str, Any]:
    """Captures container status, restart count, started_at, and health."""
    try:
        cmd = [
            "docker", "inspect", container_name,
            "--format", "{{.State.Status}}|{{.RestartCount}}|{{.State.StartedAt}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}"
        ]
        out = subprocess.check_output(cmd, text=True, timeout=3).strip()
        parts = out.split("|")
        return {
            "status": parts[0],
            "restart_count": int(parts[1]),
            "started_at": parts[2],
            "health_status": parts[3] if len(parts) > 3 else "unknown"
        }
    except Exception as e:
        return {"error": str(e), "status": "unknown", "restart_count": -1, "started_at": "", "health_status": "unknown"}

class TelemetryMonitor:
    def __init__(self, container_name: str = "video-intake-web", interval_sec: float = 0.25):
        self.container_name = container_name
        self.interval_sec = interval_sec
        self.samples: List[Dict[str, float]] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def sample_now(self) -> Dict[str, float]:
        sample = {
            "timestamp": time.time(),
            "cpu_perc": 0.0,
            "mem_mb": 0.0,
            "mem_perc": 0.0
        }
        try:
            cmd = [
                "docker", "stats", "--no-stream",
                "--format", "{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}}",
                self.container_name
            ]
            out = subprocess.check_output(cmd, text=True, timeout=2).strip()
            parts = out.split(",")
            if len(parts) >= 3:
                sample["cpu_perc"] = float(parts[0].replace("%", "").strip())
                mem_part = parts[1].split("/")[0].strip()
                sample["mem_mb"] = round(parse_memory_str(mem_part), 2)
                sample["mem_perc"] = float(parts[2].replace("%", "").strip())
        except Exception:
            pass
        return sample

    async def _loop(self):
        while self._running:
            s = self.sample_now()
            self.samples.append(s)
            await asyncio.sleep(self.interval_sec)

    def start(self):
        self._running = True
        self.samples = []
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> Dict[str, Any]:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        if not self.samples:
            # Take at least one sample
            s = self.sample_now()
            self.samples.append(s)

        cpus = [s["cpu_perc"] for s in self.samples]
        mems = [s["mem_mb"] for s in self.samples]

        return {
            "sample_count": len(self.samples),
            "baseline_cpu_perc": round(cpus[0], 2) if cpus else 0.0,
            "avg_cpu_perc": round(sum(cpus) / len(cpus), 2) if cpus else 0.0,
            "max_cpu_perc": round(max(cpus), 2) if cpus else 0.0,
            "baseline_mem_mb": round(mems[0], 2) if mems else 0.0,
            "avg_mem_mb": round(sum(mems) / len(mems), 2) if mems else 0.0,
            "max_mem_mb": round(max(mems), 2) if mems else 0.0,
            "mem_growth_mb": round(max(mems) - mems[0], 2) if mems else 0.0
        }
