from __future__ import annotations

from typing import Any

from llm.providers.openai_compatible import OpenAICompatibleProvider
from llm.resolve import require_api_key_for_chat, resolved_chat_api_key, resolved_chat_base_url
from llm.types import ChatMessage, ChatResult
from server.core.config import get_settings


class LLMGateway:
    def __init__(self) -> None:
        settings = get_settings()
        self._provider = OpenAICompatibleProvider(
            base_url=resolved_chat_base_url(settings),
            api_key=resolved_chat_api_key(settings),
            default_model=settings.llm_model,
            require_api_key=require_api_key_for_chat(settings),
        )
        self.model = settings.llm_model
        self.provider_name = (settings.llm_provider or "api").strip().lower()

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


def reset_llm_gateway() -> None:
    global _gateway
    _gateway = None
