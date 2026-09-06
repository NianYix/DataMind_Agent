from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ServerConfig:
    id: str
    enabled: bool = True
    transport: str = "stdio"
    command: str = ""
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)


@dataclass
class ToolDescriptor:
    server_id: str
    name: str  # original MCP tool name
    bridged_name: str  # mcp_<server_id>_<sanitized>
    description: str = ""
    input_schema: dict[str, Any] = field(default_factory=dict)


@dataclass
class CallResult:
    success: bool
    content: Any = None
    is_error: bool = False
    error: str | None = None
    raw: Any = None
