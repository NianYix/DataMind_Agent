from __future__ import annotations

from typing import Any

from server.core.config import get_settings
from mcp_host.manager import get_mcp_manager


def configure_from_settings() -> None:
    settings = get_settings()
    mgr = get_mcp_manager()
    mgr.configure(
        enabled=bool(settings.mcp_enabled),
        config_path=str(settings.mcp_config_file),
        timeout_sec=float(settings.tool_timeout_sec),
    )


def ensure_started() -> None:
    configure_from_settings()
    mgr = get_mcp_manager()
    if mgr.enabled and not mgr.status().get("servers"):
        mgr.start_all()


def status() -> dict[str, Any]:
    configure_from_settings()
    mgr = get_mcp_manager()
    # If enabled but never started (e.g. tests), start lazily
    if mgr.enabled and not mgr.status().get("servers"):
        mgr.start_all()
    return mgr.status()


def list_tools() -> list[dict[str, Any]]:
    st = status()
    tools: list[dict[str, Any]] = []
    for server in st.get("servers") or []:
        for t in server.get("tools") or []:
            tools.append(
                {
                    "name": t.get("name"),
                    "original_name": t.get("original_name"),
                    "description": t.get("description"),
                    "input_schema": t.get("input_schema"),
                    "server_id": server.get("id"),
                }
            )
    return tools


def reload() -> dict[str, Any]:
    configure_from_settings()
    return get_mcp_manager().reload()


def shutdown() -> None:
    get_mcp_manager().stop_all()
