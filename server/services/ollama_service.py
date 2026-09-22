from __future__ import annotations

import time
from typing import Any

import httpx

from server.core.config import get_settings


def check_ollama_health(*, timeout: float = 5.0) -> dict[str, Any]:
    """Probe configured Ollama base URL via /api/tags (SSRF-safe: settings only)."""
    settings = get_settings()
    base = (settings.ollama_base_url or "http://localhost:11434").rstrip("/")
    url = f"{base}/api/tags"
    started = time.perf_counter()
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url)
            latency_ms = int((time.perf_counter() - started) * 1000)
            if resp.status_code >= 400:
                return {
                    "ok": False,
                    "base_url": base,
                    "latency_ms": latency_ms,
                    "models": [],
                    "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
                }
            data = resp.json()
            models = []
            for item in data.get("models") or []:
                name = item.get("name") or item.get("model")
                if name:
                    models.append(str(name))
            return {
                "ok": True,
                "base_url": base,
                "latency_ms": latency_ms,
                "models": models,
                "error": None,
            }
    except Exception as exc:  # noqa: BLE001
        latency_ms = int((time.perf_counter() - started) * 1000)
        return {
            "ok": False,
            "base_url": base,
            "latency_ms": latency_ms,
            "models": [],
            "error": str(exc),
        }
