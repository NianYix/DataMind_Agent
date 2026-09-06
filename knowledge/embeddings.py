from __future__ import annotations

import hashlib
import math
from typing import Any

import httpx

from server.core.config import get_settings

MOCK_DIM = 64


def _normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def mock_embed(texts: list[str]) -> list[list[float]]:
    out: list[list[float]] = []
    for text in texts:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        raw = []
        for i in range(MOCK_DIM):
            b = digest[i % len(digest)]
            raw.append(((b / 255.0) * 2.0) - 1.0)
        out.append(_normalize(raw))
    return out


def openai_compatible_embed(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    base = settings.resolved_embedding_base_url
    key = settings.resolved_embedding_api_key
    if not base or not key:
        raise RuntimeError("Embedding API not configured (EMBEDDING_BASE_URL/API_KEY or LLM_*)")
    url = f"{base}/embeddings"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {"model": settings.embedding_model, "input": texts}
    with httpx.Client(timeout=settings.tool_timeout_sec) as client:
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
    items = sorted(data.get("data") or [], key=lambda x: int(x.get("index") or 0))
    return [list(map(float, it["embedding"])) for it in items]


def embed_texts(texts: list[str], *, provider: str | None = None) -> list[list[float]]:
    if not texts:
        return []
    settings = get_settings()
    mode = (provider or settings.embedding_provider or "mock").strip().lower()
    if mode == "mock":
        return mock_embed(texts)
    if mode in {"openai_compatible", "openai"}:
        # batch to avoid huge payloads
        batch_size = 16
        vectors: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            vectors.extend(openai_compatible_embed(texts[i : i + batch_size]))
        return vectors
    raise ValueError(f"Unknown embedding provider: {mode}")


def embed_query(text: str, *, provider: str | None = None) -> list[float]:
    return embed_texts([text], provider=provider)[0]
