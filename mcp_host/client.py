from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
import time
from typing import Any

from mcp_host.types import CallResult, ToolDescriptor
from mcp_host.config_loader import bridged_tool_name, sanitize_id

logger = logging.getLogger("datamind.mcp")


class McpProtocolError(RuntimeError):
    pass


def _encode_message(payload: dict[str, Any]) -> bytes:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    return header + body


def _read_message(stdout: Any, timeout_sec: float) -> dict[str, Any]:
    """Read one MCP Content-Length framed JSON-RPC message from a binary stream."""
    deadline = time.time() + timeout_sec
    headers: dict[str, str] = {}
    while True:
        remaining = deadline - time.time()
        if remaining <= 0:
            raise TimeoutError("Timed out waiting for MCP headers")
        line = _readline_with_timeout(stdout, remaining)
        if line is None:
            raise McpProtocolError("MCP server closed stdout")
        if line == b"\r\n" or line == b"\n":
            break
        try:
            text = line.decode("ascii", errors="replace").strip()
        except Exception as exc:  # noqa: BLE001
            raise McpProtocolError(f"Bad MCP header: {exc}") from exc
        if ":" in text:
            k, v = text.split(":", 1)
            headers[k.strip().lower()] = v.strip()
    length = int(headers.get("content-length") or "0")
    if length <= 0:
        raise McpProtocolError(f"Missing Content-Length: {headers}")
    remaining = deadline - time.time()
    if remaining <= 0:
        raise TimeoutError("Timed out waiting for MCP body")
    body = _readexact_with_timeout(stdout, length, remaining)
    try:
        return json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise McpProtocolError(f"Invalid JSON from MCP server: {exc}") from exc


def _readline_with_timeout(stream: Any, timeout_sec: float) -> bytes | None:
    result: list[bytes | None] = [None]
    error: list[BaseException] = []

    def _worker() -> None:
        try:
            result[0] = stream.readline()
        except BaseException as exc:  # noqa: BLE001
            error.append(exc)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout_sec)
    if t.is_alive():
        raise TimeoutError("readline timeout")
    if error:
        raise error[0]
    return result[0]


def _readexact_with_timeout(stream: Any, n: int, timeout_sec: float) -> bytes:
    result: list[bytes] = []
    error: list[BaseException] = []

    def _worker() -> None:
        try:
            buf = b""
            while len(buf) < n:
                chunk = stream.read(n - len(buf))
                if not chunk:
                    break
                buf += chunk
            result.append(buf)
        except BaseException as exc:  # noqa: BLE001
            error.append(exc)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout_sec)
    if t.is_alive():
        raise TimeoutError("readexact timeout")
    if error:
        raise error[0]
    data = result[0] if result else b""
    if len(data) < n:
        raise McpProtocolError(f"Short MCP body: got {len(data)} want {n}")
    return data


class StdioMcpClient:
    """Minimal sync MCP client (initialize / tools/list / tools/call) over stdio."""

    def __init__(
        self,
        server_id: str,
        command: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
        timeout_sec: float = 30,
    ) -> None:
        self.server_id = sanitize_id(server_id)
        self.command = command
        self.args = list(args or [])
        self.env = dict(env or {})
        self.timeout_sec = timeout_sec
        self._proc: subprocess.Popen[bytes] | None = None
        self._next_id = 1
        self._lock = threading.Lock()
        self._tools: list[ToolDescriptor] = []
        self._name_map: dict[str, str] = {}  # sanitized -> original
        self.status = "idle"
        self.error: str | None = None

    @property
    def tools(self) -> list[ToolDescriptor]:
        return list(self._tools)

    def connect(self) -> None:
        with self._lock:
            self._connect_unlocked()

    def _connect_unlocked(self) -> None:
        self.close_unlocked()
        self.status = "connecting"
        self.error = None
        full_env = os.environ.copy()
        full_env.update(self.env)
        # Avoid UTF-8 issues on Windows child consoles
        full_env.setdefault("PYTHONIOENCODING", "utf-8")
        full_env.setdefault("PYTHONUTF8", "1")
        try:
            self._proc = subprocess.Popen(
                [self.command, *self.args],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=full_env,
                cwd=str(__import__("pathlib").Path(__file__).resolve().parents[1]),
            )
            self._request_unlocked(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "datamind-agent", "version": "0.7.0"},
                },
            )
            self._notify_unlocked("notifications/initialized", {})
            listed = self._request_unlocked("tools/list", {})
            tools_raw = (listed or {}).get("tools") or []
            self._tools = []
            self._name_map = {}
            for t in tools_raw:
                if not isinstance(t, dict):
                    continue
                name = str(t.get("name") or "")
                if not name:
                    continue
                bridged = bridged_tool_name(self.server_id, name)
                self._name_map[sanitize_id(name)] = name
                # also map full original sanitize path used in bridged name
                self._name_map[bridged.split("_", 2)[-1] if bridged.count("_") >= 2 else sanitize_id(name)] = name
                self._tools.append(
                    ToolDescriptor(
                        server_id=self.server_id,
                        name=name,
                        bridged_name=bridged,
                        description=str(t.get("description") or ""),
                        input_schema=dict(t.get("inputSchema") or {}),
                    )
                )
            self.status = "connected"
        except Exception as exc:  # noqa: BLE001
            self.status = "error"
            self.error = str(exc)
            self.close_unlocked()
            raise

    def list_tools(self) -> list[ToolDescriptor]:
        with self._lock:
            if self.status != "connected":
                self._connect_unlocked()
            return list(self._tools)

    def call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> CallResult:
        with self._lock:
            try:
                if self.status != "connected":
                    self._connect_unlocked()
                original = self._resolve_tool_name(tool_name)
                result = self._request_unlocked(
                    "tools/call",
                    {"name": original, "arguments": arguments or {}},
                )
                is_error = bool((result or {}).get("isError"))
                content = (result or {}).get("content")
                text_bits: list[str] = []
                if isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            text_bits.append(str(part.get("text") or ""))
                flat: Any = "\n".join(text_bits) if text_bits else content
                if is_error:
                    return CallResult(success=False, content=flat, is_error=True, error=str(flat), raw=result)
                return CallResult(success=True, content=flat, is_error=False, raw=result)
            except Exception as exc:  # noqa: BLE001
                self.status = "error"
                self.error = str(exc)
                return CallResult(success=False, content=None, is_error=True, error=str(exc))

    def _resolve_tool_name(self, tool_name: str) -> str:
        if tool_name in {t.name for t in self._tools}:
            return tool_name
        key = sanitize_id(tool_name)
        if key in self._name_map:
            return self._name_map[key]
        # bridged form mcp_sid_tool
        if tool_name.startswith("mcp_"):
            parts = tool_name.split("_", 2)
            if len(parts) == 3:
                key = parts[2]
                if key in self._name_map:
                    return self._name_map[key]
        raise McpProtocolError(f"Unknown MCP tool: {tool_name}")

    def close(self) -> None:
        with self._lock:
            self.close_unlocked()

    def close_unlocked(self) -> None:
        proc = self._proc
        self._proc = None
        if not proc:
            if self.status == "connected":
                self.status = "stopped"
            return
        try:
            if proc.stdin:
                proc.stdin.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:  # noqa: BLE001
            try:
                proc.kill()
            except Exception:  # noqa: BLE001
                pass
        if self.status not in {"error"}:
            self.status = "stopped"

    def _notify_unlocked(self, method: str, params: dict[str, Any]) -> None:
        assert self._proc and self._proc.stdin
        self._proc.stdin.write(_encode_message({"jsonrpc": "2.0", "method": method, "params": params}))
        self._proc.stdin.flush()

    def _request_unlocked(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        assert self._proc and self._proc.stdin and self._proc.stdout
        req_id = self._next_id
        self._next_id += 1
        self._proc.stdin.write(_encode_message({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}))
        self._proc.stdin.flush()
        deadline = time.time() + self.timeout_sec
        while True:
            remaining = max(0.1, deadline - time.time())
            msg = _read_message(self._proc.stdout, remaining)
            if msg.get("id") != req_id:
                # skip notifications / unmatched
                if "method" in msg and "id" not in msg:
                    continue
                if msg.get("id") is not None:
                    continue
                continue
            if "error" in msg:
                err = msg["error"]
                raise McpProtocolError(str(err))
            result = msg.get("result")
            return result if isinstance(result, dict) else {"value": result}
