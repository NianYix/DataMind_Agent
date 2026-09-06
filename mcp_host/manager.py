from __future__ import annotations

import logging
import threading
from typing import Any

from mcp_host.client import StdioMcpClient
from mcp_host.config_loader import load_server_configs, parse_bridged_name, sanitize_id
from mcp_host.types import CallResult, ServerConfig, ToolDescriptor

logger = logging.getLogger("datamind.mcp")


class McpManager:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._clients: dict[str, StdioMcpClient] = {}
        self._enabled = False
        self._config_path = ""
        self._timeout_sec = 30.0

    def configure(self, *, enabled: bool, config_path: str, timeout_sec: float = 30.0) -> None:
        with self._lock:
            self._enabled = enabled
            self._config_path = config_path
            self._timeout_sec = timeout_sec

    @property
    def enabled(self) -> bool:
        return self._enabled

    def start_all(self) -> None:
        with self._lock:
            self._stop_all_unlocked()
            if not self._enabled:
                return
            configs = load_server_configs(self._config_path)
            for cfg in configs:
                if not cfg.enabled:
                    continue
                self._start_one_unlocked(cfg)

    def reload(self) -> dict[str, Any]:
        with self._lock:
            self.start_all()
            return self.status_unlocked()

    def stop_all(self) -> None:
        with self._lock:
            self._stop_all_unlocked()

    def _stop_all_unlocked(self) -> None:
        for client in list(self._clients.values()):
            try:
                client.close()
            except Exception:  # noqa: BLE001
                pass
        self._clients.clear()

    def _start_one_unlocked(self, cfg: ServerConfig) -> None:
        if not cfg.command:
            logger.warning("MCP server %s missing command", cfg.id)
            client = StdioMcpClient(cfg.id, command="", timeout_sec=self._timeout_sec)
            client.status = "error"
            client.error = "missing command"
            self._clients[cfg.id] = client
            return
        client = StdioMcpClient(
            server_id=cfg.id,
            command=cfg.command,
            args=cfg.args,
            env=cfg.env,
            timeout_sec=self._timeout_sec,
        )
        self._clients[cfg.id] = client
        try:
            client.connect()
        except Exception as exc:  # noqa: BLE001
            logger.warning("MCP server %s failed: %s", cfg.id, exc)
            client.status = "error"
            client.error = str(exc)

    def list_tools(self) -> list[ToolDescriptor]:
        with self._lock:
            if not self._enabled:
                return []
            tools: list[ToolDescriptor] = []
            for client in self._clients.values():
                if client.status == "connected":
                    tools.extend(client.tools)
            return tools

    def call(self, bridged_or_server_tool: str, arguments: dict[str, Any] | None = None) -> CallResult:
        with self._lock:
            if not self._enabled:
                return CallResult(success=False, error="MCP_ENABLED=false", is_error=True)
            server_id, tool_key = self._resolve(bridged_or_server_tool)
            client = self._clients.get(server_id)
            if not client:
                return CallResult(success=False, error=f"Unknown MCP server: {server_id}", is_error=True)
            if client.status != "connected":
                try:
                    client.connect()
                except Exception as exc:  # noqa: BLE001
                    return CallResult(success=False, error=str(exc), is_error=True)
            return client.call_tool(tool_key, arguments)

    def _resolve(self, name: str) -> tuple[str, str]:
        parsed = parse_bridged_name(name)
        if parsed:
            server_id, tool_part = parsed
            return sanitize_id(server_id), tool_part
        # fallback: mcp_<sid>_<tool> already sanitized in parse
        if name.startswith("mcp_") and "_" in name[4:]:
            sid, rest = name[4:].split("_", 1)
            return sanitize_id(sid), rest
        raise ValueError(f"Not an MCP bridged tool: {name}")

    def status(self) -> dict[str, Any]:
        with self._lock:
            return self.status_unlocked()

    def status_unlocked(self) -> dict[str, Any]:
        servers = []
        for sid, client in self._clients.items():
            servers.append(
                {
                    "id": sid,
                    "status": client.status,
                    "error": client.error,
                    "tool_count": len(client.tools) if client.status == "connected" else 0,
                    "tools": [
                        {
                            "name": t.bridged_name,
                            "original_name": t.name,
                            "description": t.description,
                            "input_schema": t.input_schema,
                        }
                        for t in client.tools
                    ]
                    if client.status == "connected"
                    else [],
                }
            )
        # Also surface configured-but-not-started when disabled
        return {
            "enabled": self._enabled,
            "config_path": self._config_path,
            "servers": servers,
        }


_MANAGER: McpManager | None = None
_MANAGER_LOCK = threading.Lock()


def get_mcp_manager() -> McpManager:
    global _MANAGER
    with _MANAGER_LOCK:
        if _MANAGER is None:
            _MANAGER = McpManager()
        return _MANAGER


def reset_mcp_manager() -> McpManager:
    """Test helper: stop and replace singleton."""
    global _MANAGER
    with _MANAGER_LOCK:
        if _MANAGER is not None:
            try:
                _MANAGER.stop_all()
            except Exception:  # noqa: BLE001
                pass
        _MANAGER = McpManager()
        return _MANAGER
