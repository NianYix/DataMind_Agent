from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from mcp_host.bridge import call_mcp_tool
from mcp_host.manager import reset_mcp_manager
from server.core.config import reload_settings
from server.core.db import init_db
from tools.registry import run_tool
from tools.registry import ToolContext

ROOT = Path(__file__).resolve().parents[1]


def _write_demo_config(tmp_path: Path) -> Path:
    cfg = {
        "servers": [
            {
                "id": "demo",
                "enabled": True,
                "transport": "stdio",
                "command": sys.executable,
                "args": ["-m", "mcp_host.mock_server"],
                "env": {},
            }
        ]
    }
    path = tmp_path / "mcp_servers.json"
    path.write_text(json.dumps(cfg), encoding="utf-8")
    return path


def test_mcp_disabled_by_default(monkeypatch, tmp_path):
    monkeypatch.setenv("MCP_ENABLED", "false")
    monkeypatch.setenv("MCP_CONFIG_PATH", str(tmp_path / "missing.json"))
    reload_settings()
    reset_mcp_manager()
    init_db()

    from server.main import app

    client = TestClient(app)
    st = client.get("/api/mcp/status").json()
    assert st["enabled"] is False
    tools = client.get("/api/mcp/tools").json()["tools"]
    assert tools == []
    ctx = ToolContext(dataset_path="")
    unknown = run_tool("mcp_demo_echo", {"text": "x"}, ctx)
    assert unknown["success"] is False
    from tools.registry import TOOL_HANDLERS

    assert "sql_query" in TOOL_HANDLERS


def test_mcp_mock_list_and_call(monkeypatch, tmp_path):
    cfg = _write_demo_config(tmp_path)
    monkeypatch.setenv("MCP_ENABLED", "true")
    monkeypatch.setenv("MCP_CONFIG_PATH", str(cfg))
    reload_settings()
    mgr = reset_mcp_manager()
    mgr.configure(enabled=True, config_path=str(cfg), timeout_sec=20)
    mgr.start_all()

    tools = mgr.list_tools()
    names = [t.bridged_name for t in tools]
    assert "mcp_demo_echo" in names

    result = call_mcp_tool("mcp_demo_echo", {"text": "hello-mcp"})
    assert result["success"] is True
    assert "hello-mcp" in str(result.get("content"))

    ctx = ToolContext(dataset_path="")
    via_registry = run_tool("mcp_demo_echo", {"text": "via-reg"}, ctx)
    assert via_registry["success"] is True
    assert "via-reg" in str(via_registry.get("content"))

    # prefix must not steal builtins
    assert "sql_query" in __import__("tools.registry", fromlist=["TOOL_HANDLERS"]).TOOL_HANDLERS


def test_mcp_api_with_mock(monkeypatch, tmp_path):
    cfg = _write_demo_config(tmp_path)
    monkeypatch.setenv("MCP_ENABLED", "true")
    monkeypatch.setenv("MCP_CONFIG_PATH", str(cfg))
    reload_settings()
    reset_mcp_manager()
    init_db()

    # Re-import app settings already cached — lifespan will configure on TestClient enter
    from server.main import app
    from server.services import mcp_service

    mcp_service.configure_from_settings()
    mcp_service.ensure_started()

    client = TestClient(app)
    st = client.get("/api/mcp/status").json()
    assert st["enabled"] is True
    assert any(s["id"] == "demo" and s["status"] == "connected" for s in st["servers"])

    tools = client.get("/api/mcp/tools").json()["tools"]
    assert any(t["name"] == "mcp_demo_echo" for t in tools)

    reloaded = client.post("/api/mcp/reload")
    assert reloaded.status_code == 200
    assert reloaded.json()["enabled"] is True


def test_datamind_mcp_server_lists_tools():
    from mcp_host.client import StdioMcpClient

    client = StdioMcpClient(
        server_id="dm",
        command=sys.executable,
        args=["-m", "server.mcp_server"],
        timeout_sec=30,
    )
    try:
        client.connect()
        names = {t.name for t in client.tools}
        assert "ping" in names
        assert "knowledge_search" in names
        ping = client.call_tool("ping", {})
        assert ping.success is True
        assert "DataMind" in str(ping.content)
    finally:
        client.close()
