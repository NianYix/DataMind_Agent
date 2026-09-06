"""DataMind as MCP Server (stdio) — readonly tools: ping, knowledge_search.

Run: python -m server.mcp_server
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _encode(payload: dict[str, Any]) -> bytes:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body


def _read_message() -> dict[str, Any] | None:
    headers: dict[str, str] = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        text = line.decode("ascii", errors="replace").strip()
        if ":" in text:
            k, v = text.split(":", 1)
            headers[k.strip().lower()] = v.strip()
    length = int(headers.get("content-length") or "0")
    if length <= 0:
        return None
    body = sys.stdin.buffer.read(length)
    return json.loads(body.decode("utf-8"))


def _write(payload: dict[str, Any]) -> None:
    sys.stdout.buffer.write(_encode(payload))
    sys.stdout.buffer.flush()


TOOLS = [
    {
        "name": "ping",
        "description": "Health check for DataMind MCP server",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "knowledge_search",
        "description": "Search DataMind knowledge bases for definitions / 口径",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "knowledge_base_id": {"type": "string"},
                "top_k": {"type": "integer"},
                "workspace_id": {"type": "string"},
            },
            "required": ["query"],
        },
    },
]


def _call_knowledge_search(args: dict[str, Any]) -> dict[str, Any]:
    from server.core.db import SessionLocal, init_db
    from tools.knowledge_search import knowledge_search

    init_db()
    # Ensure ORM session factory is warm
    db = SessionLocal()
    try:
        return knowledge_search(
            query=str(args.get("query") or ""),
            knowledge_base_id=args.get("knowledge_base_id"),
            top_k=args.get("top_k"),
            workspace_id=args.get("workspace_id"),
        )
    finally:
        db.close()


def _handle(msg: dict[str, Any]) -> None:
    method = msg.get("method")
    req_id = msg.get("id")
    params = msg.get("params") or {}

    if method == "initialize":
        _write(
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "datamind-mcp-server", "version": "0.7.0"},
                },
            }
        )
        return

    if method in {"notifications/initialized", "initialized"}:
        return

    if method == "tools/list":
        _write({"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}})
        return

    if method == "tools/call":
        name = str(params.get("name") or "")
        args = params.get("arguments") or {}
        try:
            if name == "ping":
                payload = {"ok": True, "app": "DataMind Agent", "version": "0.7.0"}
            elif name == "knowledge_search":
                payload = _call_knowledge_search(args if isinstance(args, dict) else {})
            else:
                _write(
                    {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
                            "isError": True,
                        },
                    }
                )
                return
            text = json.dumps(payload, ensure_ascii=False, default=str)
            _write(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": text}], "isError": False},
                }
            )
        except Exception as exc:  # noqa: BLE001
            _write(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": str(exc)}],
                        "isError": True,
                    },
                }
            )
        return

    if req_id is not None:
        _write(
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }
        )


def main() -> None:
    try:
        sys.stdin.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    while True:
        msg = _read_message()
        if msg is None:
            break
        if "method" not in msg:
            continue
        _handle(msg)


if __name__ == "__main__":
    main()
