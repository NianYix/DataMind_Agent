from __future__ import annotations

import json
from typing import Any

from llm import gateway as gateway_mod
from server.core.config import HOT_FIELDS, get_settings, reload_settings


def mask_secret(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return f"{value[:3]}***{value[-4:]}"


def get_public_settings() -> dict[str, Any]:
    s = get_settings()
    return {
        "llm_base_url": s.llm_base_url,
        "llm_api_key": mask_secret(s.llm_api_key),
        "llm_api_key_set": bool(s.llm_api_key),
        "llm_model": s.llm_model,
        "max_agent_steps": s.max_agent_steps,
        "max_tool_retries": s.max_tool_retries,
        "tool_timeout_sec": s.tool_timeout_sec,
        "run_timeout_sec": s.run_timeout_sec,
        "llm_input_price_per_1k": s.llm_input_price_per_1k,
        "llm_output_price_per_1k": s.llm_output_price_per_1k,
        "large_file_mb": s.large_file_mb,
        "profile_sample_rows": s.profile_sample_rows,
        "sql_max_rows": s.sql_max_rows,
        "duckdb_enabled": s.duckdb_enabled,
        "app_api_key_required": bool(s.app_api_key),
        "app_env": s.app_env,
        "auth_enabled": s.auth_enabled,
        "http_url_allowlist": s.http_url_allowlist,
        "http_max_response_bytes": s.http_max_response_bytes,
        "web_search_enabled": s.web_search_enabled,
        "multi_agent_enabled": s.multi_agent_enabled,
        "critic_enabled": s.critic_enabled,
    }


def update_settings(patch: dict[str, Any]) -> dict[str, Any]:
    s = get_settings()
    path = s.settings_file
    current: dict[str, Any] = {}
    if path.exists():
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            current = {}

    for key, value in patch.items():
        if key not in HOT_FIELDS:
            continue
        if key == "llm_api_key" and (
            value is None or value == "" or str(value).startswith("***") or "***" in str(value)
        ):
            continue
        current[key] = value

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")

    reload_settings()
    gateway_mod._gateway = None  # noqa: SLF001
    return get_public_settings()
