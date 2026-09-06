from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]

logger = logging.getLogger("datamind.config")

HOT_FIELDS = {
    "llm_base_url",
    "llm_api_key",
    "llm_model",
    "max_agent_steps",
    "max_tool_retries",
    "tool_timeout_sec",
    "run_timeout_sec",
    "llm_input_price_per_1k",
    "llm_output_price_per_1k",
    "large_file_mb",
    "profile_sample_rows",
    "sql_max_rows",
    "duckdb_enabled",
    "http_url_allowlist",
    "http_max_response_bytes",
    "web_search_enabled",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "dev"
    database_url: str = f"sqlite:///{(ROOT_DIR / 'storage' / 'database' / 'datamind.db').as_posix()}"
    upload_dir: str = str(ROOT_DIR / "storage" / "uploads")
    llm_base_url: str = "https://api.deepseek.com"
    llm_api_key: str = ""
    llm_model: str = "deepseek-chat"
    max_agent_steps: int = 20
    max_tool_retries: int = 2
    tool_timeout_sec: int = 30
    run_timeout_sec: int = 300
    max_upload_mb: int = 50
    cors_origins: str = "http://localhost:3000"
    llm_input_price_per_1k: float = 0.0
    llm_output_price_per_1k: float = 0.0
    duckdb_enabled: bool = True
    app_api_key: str = ""
    large_file_mb: int = 30
    profile_sample_rows: int = 200_000
    log_dir: str = str(ROOT_DIR / "storage" / "logs")
    settings_path: str = str(ROOT_DIR / "storage" / "settings.json")
    sql_max_rows: int = 5000
    agent_engine: str = "langchain"  # langchain | legacy
    auth_enabled: bool = False
    jwt_secret: str = "dev-datamind-secret-change-me-32chars!!"
    jwt_expire_min: int = 10080
    seed_admin_user: str = "admin"
    seed_admin_password: str = "admin"
    http_url_allowlist: str = "https://httpbin.org/,https://api.github.com/"
    http_max_response_bytes: int = 65536
    web_search_enabled: bool = False
    db_connect_timeout_sec: int = 8
    credential_secret: str = "dev-datamind-cred-key"
    embedding_provider: str = "openai_compatible"  # openai_compatible | mock
    embedding_model: str = "text-embedding-3-small"
    embedding_base_url: str = ""
    embedding_api_key: str = ""
    chroma_path: str = str(ROOT_DIR / "storage" / "chroma")
    knowledge_dir: str = str(ROOT_DIR / "storage" / "knowledge")
    rag_chunk_size: int = 800
    rag_chunk_overlap: int = 120
    rag_top_k: int = 5

    @property
    def http_allowlist_prefixes(self) -> list[str]:
        return [p.strip() for p in self.http_url_allowlist.split(",") if p.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float | None:
        if self.llm_input_price_per_1k <= 0 and self.llm_output_price_per_1k <= 0:
            return None
        return round(
            (input_tokens / 1000.0) * self.llm_input_price_per_1k
            + (output_tokens / 1000.0) * self.llm_output_price_per_1k,
            6,
        )

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        if not path.is_absolute():
            path = ROOT_DIR / path
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def settings_file(self) -> Path:
        path = Path(self.settings_path)
        if not path.is_absolute():
            path = ROOT_DIR / path
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def log_path(self) -> Path:
        path = Path(self.log_dir)
        if not path.is_absolute():
            path = ROOT_DIR / path
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def chroma_dir(self) -> Path:
        path = Path(self.chroma_path)
        if not path.is_absolute():
            path = ROOT_DIR / path
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def knowledge_path(self) -> Path:
        path = Path(self.knowledge_dir)
        if not path.is_absolute():
            path = ROOT_DIR / path
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def resolved_embedding_base_url(self) -> str:
        return (self.embedding_base_url or self.llm_base_url or "").rstrip("/")

    @property
    def resolved_embedding_api_key(self) -> str:
        return self.embedding_api_key or self.llm_api_key or ""


def _load_overrides() -> dict[str, Any]:
    # Read path from env defaults without full settings (avoid recursion)
    path = ROOT_DIR / "storage" / "settings.json"
    raw = Path(__file__).resolve().parents[2] / ".env"
    # Prefer SETTINGS_PATH from a lightweight parse if present
    settings_path = path
    if raw.exists():
        for line in raw.read_text(encoding="utf-8").splitlines():
            if line.startswith("SETTINGS_PATH="):
                candidate = line.split("=", 1)[1].strip()
                p = Path(candidate)
                settings_path = p if p.is_absolute() else ROOT_DIR / p
                break
    if not settings_path.exists():
        return {}
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
        return {k: v for k, v in data.items() if k in HOT_FIELDS}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to load settings.json: %s", exc)
        return {}


@lru_cache
def get_settings() -> Settings:
    base = Settings()
    overrides = _load_overrides()
    if not overrides:
        return base
    return Settings(**{**base.model_dump(), **overrides})


def reload_settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()
