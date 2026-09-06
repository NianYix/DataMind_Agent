"""mcp_host — DataMind MCP Client bridge (minimal JSON-RPC stdio subset)."""

from mcp_host.manager import get_mcp_manager, reset_mcp_manager

__all__ = ["get_mcp_manager", "reset_mcp_manager"]
