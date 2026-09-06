"""Minimal MCP stdio server with an `echo` tool (for CI / local demo).

Run: python -m mcp_host.mock_server
"""

from __future__ import annotations

import json
import sys
from typing import Any


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
        "name": "echo",
        "description": "Echo back the provided text (DataMind MCP demo tool)",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string", "description": "Text to echo"}},
            "required": ["text"],
        },
    }
]


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
                    "serverInfo": {"name": "datamind-mock-mcp", "version": "0.7.0"},
                },
            }
        )
        return

    if method == "notifications/initialized" or method == "initialized":
        return

    if method == "tools/list":
        _write({"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}})
        return

    if method == "tools/call":
        name = str(params.get("name") or "")
        args = params.get("arguments") or {}
        if name == "echo":
            text = str(args.get("text") or "")
            _write(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": text}],
                        "isError": False,
                    },
                }
            )
            return
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

    if req_id is not None:
        _write(
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }
        )


def main() -> None:
    # Ensure binary-safe stdio on Windows
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
