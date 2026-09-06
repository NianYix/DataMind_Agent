from __future__ import annotations

from typing import Any

from llm.providers.openai_compatible import OpenAICompatibleProvider
from llm.types import ChatMessage, ChatResult
from server.core.config import get_settings


class LLMGateway:
    def __init__(self) -> None:
        settings = get_settings()
        self._provider = OpenAICompatibleProvider(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            default_model=settings.llm_model,
        )
        self.model = settings.llm_model

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        response_format: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
    ) -> ChatResult:
        return self._provider.chat(
            messages,
            model=model,
            temperature=temperature,
            response_format=response_format,
            tools=tools,
            tool_choice=tool_choice,
        )


_gateway: LLMGateway | None = None


def get_llm_gateway() -> LLMGateway:
    global _gateway
    if _gateway is None:
        _gateway = LLMGateway()
    return _gateway
