from __future__ import annotations

from langchain_openai import ChatOpenAI

from llm.resolve import require_api_key_for_chat, resolved_chat_api_key, resolved_openai_v1_base
from server.core.config import get_settings


def get_chat_model(*, temperature: float = 0.2) -> ChatOpenAI:
    settings = get_settings()
    if require_api_key_for_chat(settings) and not settings.llm_api_key:
        raise RuntimeError("LLM_API_KEY is not configured. Set it in .env")
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=resolved_chat_api_key(settings),
        base_url=resolved_openai_v1_base(settings),
        temperature=temperature,
    )
