from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from mcp_host.types import ServerConfig

logger = logging.getLogger("datamind.mcp")

_ID_RE = re.compile(r"[^a-zA-Z0-9_]+")


def sanitize_id(value: str) -> str:
    cleaned = _ID_RE.sub("_", (value or "").strip())
    cleaned = cleaned.strip("_") or "tool"
    return cleaned[:64]


def bridged_tool_name(server_id: str, tool_name: str) -> str:
    return f"mcp_{sanitize_id(server_id)}_{sanitize_id(tool_name)}"


def parse_bridged_name(bridged: str) -> tuple[str, str] | None:
    """Return (server_id, tool_name_sanitized) — original tool name resolved by manager."""
    if not bridged.startswith("mcp_"):
        return None
    rest = bridged[4:]
    if "_" not in rest:
        return None
    server_id, tool_part = rest.split("_", 1)
    return server_id, tool_part


def load_server_configs(path: str | Path) -> list[ServerConfig]:
    p = Path(path)
    if not p.is_absolute():
        from server.core.config import ROOT_DIR

        p = ROOT_DIR / p
    if not p.exists():
        logger.warning("MCP config missing: %s", p)
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("MCP config invalid: %s", exc)
        return []
    servers = data.get("servers") if isinstance(data, dict) else None
    if not isinstance(servers, list):
        return []
    out: list[ServerConfig] = []
    for item in servers:
        if not isinstance(item, dict):
            continue
        sid = sanitize_id(str(item.get("id") or ""))
        if not sid:
            continue
        transport = str(item.get("transport") or "stdio").lower()
        if transport != "stdio":
            logger.warning("Skipping MCP server %s: transport %s not supported yet", sid, transport)
            continue
        out.append(
            ServerConfig(
                id=sid,
                enabled=bool(item.get("enabled", True)),
                transport=transport,
                command=str(item.get("command") or ""),
                args=[str(a) for a in (item.get("args") or [])],
                env={str(k): str(v) for k, v in (item.get("env") or {}).items()},
            )
        )
    return out


def dump_example_config() -> dict[str, Any]:
    return {
        "servers": [
            {
                "id": "demo",
                "enabled": True,
                "transport": "stdio",
                "command": "python",
                "args": ["-m", "mcp_host.mock_server"],
                "env": {},
            }
        ]
    }
