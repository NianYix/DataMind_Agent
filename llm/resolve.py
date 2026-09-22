from __future__ import annotations

from server.core.config import Settings, get_settings

ALLOWED_PROVIDERS = frozenset({"api", "ollama"})


def normalize_provider(value: str | None) -> str:
    provider = (value or "api").strip().lower()
    if provider not in ALLOWED_PROVIDERS:
        raise ValueError(f"llm_provider must be one of {sorted(ALLOWED_PROVIDERS)}, got {value!r}")
    return provider


def is_ollama(settings: Settings | None = None) -> bool:
    s = settings or get_settings()
    return normalize_provider(s.llm_provider) == "ollama"


def require_api_key_for_chat(settings: Settings | None = None) -> bool:
    return not is_ollama(settings)


def resolved_chat_base_url(settings: Settings | None = None) -> str:
    s = settings or get_settings()
    if is_ollama(s):
        return (s.ollama_base_url or "http://localhost:11434").rstrip("/")
    return (s.llm_base_url or "").rstrip("/")


def resolved_chat_api_key(settings: Settings | None = None) -> str:
    s = settings or get_settings()
    if is_ollama(s):
        return s.llm_api_key or "ollama"
    return s.llm_api_key or ""


def resolved_openai_v1_base(settings: Settings | None = None) -> str:
    base = resolved_chat_base_url(settings)
    if not base.endswith("/v1"):
        base = f"{base}/v1"
    return base
