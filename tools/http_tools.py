from __future__ import annotations

from typing import Any

import httpx

from server.core.config import get_settings


def http_request(
    *,
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    body: str | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    method_u = (method or "GET").upper()
    if method_u not in {"GET", "POST"}:
        return {"success": False, "error": "Only GET/POST allowed"}
    allowed = settings.http_allowlist_prefixes
    if not any(url.startswith(prefix) for prefix in allowed):
        return {"success": False, "error": "URL not in allowlist"}
    try:
        with httpx.Client(timeout=timeout or settings.tool_timeout_sec) as client:
            resp = client.request(method_u, url, headers=headers or {}, content=body)
        raw = resp.content[: settings.http_max_response_bytes]
        truncated = len(resp.content) > settings.http_max_response_bytes
        text = raw.decode("utf-8", errors="replace")
        return {
            "success": True,
            "status_code": resp.status_code,
            "headers": {k: v for k, v in list(resp.headers.items())[:20]},
            "body": text,
            "truncated": truncated,
        }
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": str(exc)}


def web_search(*, query: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.web_search_enabled:
        return {"success": False, "error": "web_search is disabled"}
    # Stub: no external search provider configured in V5 slice
    return {
        "success": True,
        "provider": "stub",
        "query": query,
        "results": [
            {
                "title": "Web search not configured",
                "snippet": "Enable a provider in a later release. This is a V5 stub response.",
                "url": "https://example.com",
            }
        ],
    }
