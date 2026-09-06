from __future__ import annotations

import json
import re
from typing import Any

from agent.prompts import MEMORY_SYSTEM, SUPERVISOR_SYSTEM, TOOL_PICKER_SYSTEM
from agent.state import AgentState
from llm.gateway import LLMGateway
from llm.types import ChatMessage, ToolCallRequest
from tools.schemas import TOOL_SCHEMAS


def _extract_json(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise
        return json.loads(match.group(0))


def decide_next(gateway: LLMGateway, state: AgentState) -> tuple[dict[str, Any], int, int]:
    pending = [s.description for s in state.plan if s.status == "pending"]
    payload = {
        "question": state.question,
        "memory": state.memory,
        "pending_steps": pending[:5],
        "observations": [o.summary for o in state.observations[-5:]],
        "step_count": state.step_count,
        "used_non_python_tool": state.used_non_python_tool,
    }
    result = gateway.chat(
        [
            ChatMessage("system", SUPERVISOR_SYSTEM),
            ChatMessage("user", json.dumps(payload, ensure_ascii=False)),
        ],
        response_format={"type": "json_object"},
    )
    data = _extract_json(result.content)
    action = str(data.get("action") or "call_tool")
    if action not in {"call_tool", "insight", "finish", "replan"}:
        action = "call_tool"
    # encourage non-python tool early if none used yet
    preferred = data.get("preferred_tool")
    if not state.used_non_python_tool and not preferred and pending:
        preferred = "sql_query"
    return (
        {
            "action": action,
            "reason": str(data.get("reason") or ""),
            "preferred_tool": preferred,
        },
        result.usage.input_tokens,
        result.usage.output_tokens,
    )


def pick_tool_call(
    gateway: LLMGateway,
    state: AgentState,
    step_description: str,
    preferred_tool: str | None = None,
) -> tuple[ToolCallRequest | None, int, int]:
    user = json.dumps(
        {
            "question": state.question,
            "step": step_description,
            "preferred_tool": preferred_tool,
            "schema": state.schema_info,
            "memory": state.memory,
            "prior_observations": [o.summary for o in state.observations[-3:]],
            "hint": "Call exactly one tool. For SQL use table name data.",
        },
        ensure_ascii=False,
    )
    try:
        result = gateway.chat(
            [ChatMessage("system", TOOL_PICKER_SYSTEM), ChatMessage("user", user)],
            tools=TOOL_SCHEMAS,
            tool_choice="required",
        )
        if result.tool_calls:
            return result.tool_calls[0], result.usage.input_tokens, result.usage.output_tokens
        # some models put tool json in content
        return None, result.usage.input_tokens, result.usage.output_tokens
    except Exception:  # noqa: BLE001
        # fallback without tools API
        result = gateway.chat(
            [
                ChatMessage(
                    "system",
                    TOOL_PICKER_SYSTEM
                    + '\nReturn STRICT JSON: {"tool_name":"...","arguments":{...}}',
                ),
                ChatMessage("user", user),
            ],
            response_format={"type": "json_object"},
        )
        data = _extract_json(result.content)
        name = str(data.get("tool_name") or preferred_tool or "python_execute")
        args = data.get("arguments") if isinstance(data.get("arguments"), dict) else {}
        return (
            ToolCallRequest(id="fallback", name=name, arguments=args),
            result.usage.input_tokens,
            result.usage.output_tokens,
        )


def update_memory(
    gateway: LLMGateway,
    *,
    previous: dict[str, Any],
    message: str,
) -> tuple[dict[str, Any], int, int]:
    result = gateway.chat(
        [
            ChatMessage("system", MEMORY_SYSTEM),
            ChatMessage(
                "user",
                json.dumps({"previous": previous, "message": message}, ensure_ascii=False),
            ),
        ],
        response_format={"type": "json_object"},
    )
    data = _extract_json(result.content)
    filters = data.get("filters") if isinstance(data.get("filters"), dict) else {}
    # drop empty values
    filters = {k: v for k, v in filters.items() if v not in (None, "", [])}
    return filters, result.usage.input_tokens, result.usage.output_tokens
