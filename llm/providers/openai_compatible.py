from __future__ import annotations

import json
from typing import Any

import httpx

from llm.types import ChatMessage, ChatResult, TokenUsage, ToolCallRequest


class OpenAICompatibleProvider:
    def __init__(self, base_url: str, api_key: str, default_model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.default_model = default_model

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        response_format: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        timeout: float = 120.0,
    ) -> ChatResult:
        if not self.api_key:
            raise RuntimeError("LLM_API_KEY is not configured. Set it in .env")

        payload: dict[str, Any] = {
            "model": model or self.default_model,
            "messages": [_serialize_message(m) for m in messages],
            "temperature": temperature,
        }
        if response_format and not tools:
            payload["response_format"] = response_format
        if tools:
            payload["tools"] = tools
            if tool_choice is not None:
                payload["tool_choice"] = tool_choice

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}/v1/chat/completions"
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        message = data["choices"][0]["message"]
        content = message.get("content") or ""
        tool_calls: list[ToolCallRequest] = []
        for tc in message.get("tool_calls") or []:
            fn = tc.get("function") or {}
            args_raw = fn.get("arguments") or "{}"
            try:
                args = json.loads(args_raw) if isinstance(args_raw, str) else dict(args_raw)
            except json.JSONDecodeError:
                args = {"raw": args_raw}
            tool_calls.append(
                ToolCallRequest(
                    id=str(tc.get("id") or ""),
                    name=str(fn.get("name") or ""),
                    arguments=args if isinstance(args, dict) else {"value": args},
                )
            )

        usage_raw = data.get("usage") or {}
        usage = TokenUsage(
            input_tokens=int(usage_raw.get("prompt_tokens") or 0),
            output_tokens=int(usage_raw.get("completion_tokens") or 0),
        )
        return ChatResult(content=content, usage=usage, tool_calls=tool_calls, raw=data)


def _serialize_message(m: ChatMessage) -> dict[str, Any]:
    payload: dict[str, Any] = {"role": m.role, "content": m.content or ""}
    if m.tool_call_id:
        payload["tool_call_id"] = m.tool_call_id
    if m.name and m.role == "tool":
        payload["name"] = m.name
    if m.tool_calls:
        payload["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.name,
                    "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                },
            }
            for tc in m.tool_calls
        ]
    return payload
