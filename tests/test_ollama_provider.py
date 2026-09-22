from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient

from llm.resolve import (
    normalize_provider,
    require_api_key_for_chat,
    resolved_chat_api_key,
    resolved_chat_base_url,
    resolved_openai_v1_base,
)
from server.core.config import reload_settings
from server.services import ollama_service


def _settings(**kwargs):
    base = dict(
        llm_provider="api",
        llm_base_url="https://api.deepseek.com",
        llm_api_key="",
        llm_model="deepseek-chat",
        ollama_base_url="http://localhost:11434",
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_normalize_provider():
    assert normalize_provider("API") == "api"
    assert normalize_provider("ollama") == "ollama"
    with pytest.raises(ValueError):
        normalize_provider("gemini")


def test_resolve_api_requires_key():
    s = _settings(llm_provider="api", llm_api_key="")
    assert require_api_key_for_chat(s) is True
    assert resolved_chat_api_key(s) == ""
    assert resolved_chat_base_url(s) == "https://api.deepseek.com"


def test_resolve_ollama_placeholder_key():
    s = _settings(llm_provider="ollama", llm_api_key="", ollama_base_url="http://127.0.0.1:11434/")
    assert require_api_key_for_chat(s) is False
    assert resolved_chat_api_key(s) == "ollama"
    assert resolved_chat_base_url(s) == "http://127.0.0.1:11434"
    assert resolved_openai_v1_base(s) == "http://127.0.0.1:11434/v1"


def test_ollama_health_ok(monkeypatch):
    class _Resp:
        status_code = 200

        def json(self):
            return {"models": [{"name": "qwen2.5:7b"}, {"name": "llama3.2"}]}

    class _Client:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url):
            assert url.endswith("/api/tags")
            return _Resp()

    monkeypatch.setattr(
        ollama_service,
        "get_settings",
        lambda: _settings(ollama_base_url="http://localhost:11434"),
    )
    monkeypatch.setattr(httpx, "Client", _Client)
    out = ollama_service.check_ollama_health()
    assert out["ok"] is True
    assert "qwen2.5:7b" in out["models"]
    assert out["error"] is None


def test_ollama_health_fail(monkeypatch):
    class _Client:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url):
            raise httpx.ConnectError("refused")

    monkeypatch.setattr(
        ollama_service,
        "get_settings",
        lambda: _settings(ollama_base_url="http://localhost:11434"),
    )
    monkeypatch.setattr(httpx, "Client", _Client)
    out = ollama_service.check_ollama_health()
    assert out["ok"] is False
    assert out["models"] == []
    assert out["error"]


def test_settings_exposes_provider():
    from server.main import app

    reload_settings()
    with TestClient(app) as client:
        data = client.get("/api/settings").json()
        assert data["llm_provider"] in {"api", "ollama"}
        assert "ollama_base_url" in data


def test_settings_put_ollama_provider(tmp_path, monkeypatch):
    from server.core import config as config_mod
    from server.main import app

    settings_file = tmp_path / "settings.json"
    monkeypatch.setenv("SETTINGS_PATH", str(settings_file))
    config_mod.get_settings.cache_clear()
    reload_settings()

    with TestClient(app) as client:
        res = client.put(
            "/api/settings",
            json={
                "llm_provider": "ollama",
                "ollama_base_url": "http://127.0.0.1:11434",
                "llm_model": "qwen2.5:7b",
            },
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["llm_provider"] == "ollama"
        assert body["ollama_base_url"] == "http://127.0.0.1:11434"
        assert body["llm_model"] == "qwen2.5:7b"

    monkeypatch.delenv("SETTINGS_PATH", raising=False)
    config_mod.get_settings.cache_clear()
    reload_settings()


def test_gateway_ollama_no_real_key(monkeypatch):
    from llm import gateway as gateway_mod

    monkeypatch.setattr(
        gateway_mod,
        "get_settings",
        lambda: _settings(
            llm_provider="ollama",
            llm_api_key="",
            llm_model="qwen2.5:7b",
            ollama_base_url="http://localhost:11434",
        ),
    )
    monkeypatch.setattr(gateway_mod, "require_api_key_for_chat", lambda s=None: False)
    monkeypatch.setattr(gateway_mod, "resolved_chat_api_key", lambda s=None: "ollama")
    monkeypatch.setattr(
        gateway_mod, "resolved_chat_base_url", lambda s=None: "http://localhost:11434"
    )
    gateway_mod.reset_llm_gateway()
    gw = gateway_mod.LLMGateway()
    assert gw._provider.require_api_key is False
    assert gw._provider.api_key == "ollama"
    assert gw._provider.base_url == "http://localhost:11434"
    gateway_mod.reset_llm_gateway()


def test_get_chat_model_ollama(monkeypatch):
    from agent.lc import llm as lc_llm

    fake = MagicMock()
    monkeypatch.setattr(
        lc_llm,
        "get_settings",
        lambda: _settings(llm_provider="ollama", llm_api_key="", llm_model="qwen2.5:7b"),
    )
    monkeypatch.setattr(lc_llm, "require_api_key_for_chat", lambda s=None: False)
    monkeypatch.setattr(lc_llm, "resolved_chat_api_key", lambda s=None: "ollama")
    monkeypatch.setattr(lc_llm, "resolved_openai_v1_base", lambda s=None: "http://localhost:11434/v1")
    monkeypatch.setattr(lc_llm, "ChatOpenAI", fake)
    lc_llm.get_chat_model()
    fake.assert_called_once()
    kwargs = fake.call_args.kwargs
    assert kwargs["api_key"] == "ollama"
    assert kwargs["base_url"] == "http://localhost:11434/v1"
    assert kwargs["model"] == "qwen2.5:7b"
