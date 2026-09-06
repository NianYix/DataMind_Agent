from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from knowledge.chunking import chunk_text
from knowledge.embeddings import mock_embed
from knowledge.extract import extract_text
from server.core.config import reload_settings
from server.core.db import init_db
from server.main import app
from tools.knowledge_search import knowledge_search

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "samples" / "knowledge" / "east_china_metric.md"


def test_chunking_and_mock_embed():
    chunks = chunk_text("华东口径 " * 50, chunk_size=40, overlap=10)
    assert len(chunks) >= 2
    v1 = mock_embed(["华东口径"])[0]
    v2 = mock_embed(["华东口径"])[0]
    assert v1 == v2
    assert len(v1) == 64


def test_extract_md():
    text = extract_text(SAMPLE)
    assert "华东" in text


def test_knowledge_api_ingest_and_search(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "mock")
    reload_settings()
    init_db()
    client = TestClient(app)

    kb = client.post("/api/knowledge-bases", json={"name": "口径库"}).json()
    assert kb["id"]
    with SAMPLE.open("rb") as f:
        up = client.post(
            f"/api/knowledge-bases/{kb['id']}/documents",
            files={"file": ("east_china_metric.md", f, "text/markdown")},
        )
    assert up.status_code == 200, up.text
    body = up.json()
    assert body["status"] == "ready"
    assert body["chunk_count"] >= 1

    search = client.post(
        f"/api/knowledge-bases/{kb['id']}/search",
        json={"query": "华东口径包含哪些省市", "top_k": 3},
    )
    assert search.status_code == 200, search.text
    data = search.json()
    assert data["success"] is True
    assert data["results"]
    assert any("华东" in (r.get("text") or "") for r in data["results"])

    empty = knowledge_search(query="anything", workspace_id="nonexistent-ws")
    assert empty["success"] is True
    assert empty["results"] == []
