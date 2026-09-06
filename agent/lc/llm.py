from __future__ import annotations

from langchain_openai import ChatOpenAI

from server.core.config import get_settings


def get_chat_model(*, temperature: float = 0.2) -> ChatOpenAI:
    settings = get_settings()
    if not settings.llm_api_key:
        raise RuntimeError("LLM_API_KEY is not configured. Set it in .env")
    base = settings.llm_base_url.rstrip("/")
    if not base.endswith("/v1"):
        base = f"{base}/v1"
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=base,
        temperature=temperature,
    )
