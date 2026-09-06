from __future__ import annotations

from typing import Any

from mcp_host.manager import get_mcp_manager
from mcp_host.types import ToolDescriptor


def list_mcp_tool_descriptors() -> list[ToolDescriptor]:
    return get_mcp_manager().list_tools()


def list_mcp_tool_summaries(limit: int = 20) -> list[dict[str, str]]:
    tools = list_mcp_tool_descriptors()[: max(0, limit)]
    return [{"name": t.bridged_name, "description": t.description or t.name} for t in tools]


def call_mcp_tool(name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
    result = get_mcp_manager().call(name, args or {})
    if not result.success:
        return {
            "success": False,
            "error": result.error or "MCP call failed",
            "is_error": True,
            "content": result.content,
            "raw": result.raw,
        }
    return {
        "success": True,
        "content": result.content,
        "is_error": False,
        "raw": result.raw,
    }


def mcp_tools_prompt_block(limit: int = 20) -> str:
    summaries = list_mcp_tool_summaries(limit=limit)
    if not summaries:
        return ""
    lines = ["Available MCP bridged tools:"]
    for s in summaries:
        lines.append(f"- {s['name']}: {s['description']}")
    return "\n".join(lines)
