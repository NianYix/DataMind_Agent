from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server.core.db import SessionLocal, init_db
from server.main import app
from server.models import Dataset, Workspace
from server.services.dataset_binding import normalize_dataset_ids
from tools.registry import ToolContext, run_tool


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "t.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()
    with TestClient(app) as c:
        yield c


def _seed_two_csv(tmp_path: Path) -> tuple[str, str, str]:
    ws_id = str(uuid.uuid4())
    a = tmp_path / "sales.csv"
    b = tmp_path / "targets.csv"
    a.write_text("region,amount\nEast,10\nWest,20\n", encoding="utf-8")
    b.write_text("region,target\nEast,15\nWest,18\n", encoding="utf-8")
    db = SessionLocal()
    try:
        ws = Workspace(id=ws_id, name="ws")
        db.add(ws)
        d1 = Dataset(
            id=str(uuid.uuid4()),
            workspace_id=ws_id,
            name="sales",
            file_path=str(a),
            source_type="file",
            row_count=2,
            col_count=2,
            profile_json={"fields": [{"name": "region", "inferred_type": "string"}, {"name": "amount", "inferred_type": "number"}]},
            status="ready",
        )
        d2 = Dataset(
            id=str(uuid.uuid4()),
            workspace_id=ws_id,
            name="targets",
            file_path=str(b),
            source_type="file",
            row_count=2,
            col_count=2,
            profile_json={"fields": [{"name": "region", "inferred_type": "string"}, {"name": "target", "inferred_type": "number"}]},
            status="ready",
        )
        db.add_all([d1, d2])
        db.commit()
        return ws_id, d1.id, d2.id
    finally:
        db.close()


def test_normalize_dataset_ids_compat():
    ids, primary = normalize_dataset_ids(dataset_id="a")
    assert ids == ["a"] and primary == "a"


def test_normalize_primary_and_limit():
    ids, primary = normalize_dataset_ids(dataset_ids=["a", "b", "a"], primary_dataset_id="b")
    assert primary == "b"
    assert ids == ["b", "a"]
    with pytest.raises(Exception):
        normalize_dataset_ids(dataset_ids=["1", "2", "3", "4", "5", "6"])


def test_create_conversation_multi(client, tmp_path):
    ws_id, d1, d2 = _seed_two_csv(tmp_path)
    r = client.post(
        f"/api/workspaces/{ws_id}/conversations",
        json={"dataset_ids": [d1, d2], "primary_dataset_id": d2},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["dataset_id"] == d2
    assert body["primary_dataset_id"] == d2
    assert body["dataset_ids"] == [d2, d1]
    assert body["context_json"]["dataset_ids"] == [d2, d1]


def test_create_conversation_single_compat(client, tmp_path):
    ws_id, d1, _d2 = _seed_two_csv(tmp_path)
    r = client.post(f"/api/workspaces/{ws_id}/conversations", json={"dataset_id": d1})
    assert r.status_code == 200
    body = r.json()
    assert body["dataset_ids"] == [d1]
    assert body["dataset_id"] == d1


def test_sql_join_and_python_frames(tmp_path):
    a = tmp_path / "sales.csv"
    b = tmp_path / "targets.csv"
    a.write_text("region,amount\nEast,10\nWest,20\n", encoding="utf-8")
    b.write_text("region,target\nEast,15\nWest,18\n", encoding="utf-8")
    sources = [
        {"id": "1", "alias": "data", "frame": "df", "path": str(a), "source_type": "file", "name": "sales"},
        {"id": "2", "alias": "data_2", "frame": "df_2", "path": str(b), "source_type": "file", "name": "targets"},
    ]
    ctx = ToolContext(dataset_path=str(a), source_type="file", sources=sources)
    sql = run_tool(
        "sql_query",
        {
            "sql": "SELECT s.region, s.amount, t.target FROM data s JOIN data_2 t ON s.region = t.region ORDER BY s.region"
        },
        ctx,
    )
    assert sql.get("success"), sql
    assert sql.get("row_count") == 2

    py = run_tool(
        "python_execute",
        {"code": "result = {'n': len(df), 'n2': len(df_2), 'cols': list(df_2.columns)}"},
        ctx,
    )
    assert py.get("success"), py
    assert py.get("result", {}).get("n") == 2
    assert py.get("result", {}).get("n2") == 2

    prev = run_tool("dataset_preview", {"n": 1, "alias": "data_2"}, ctx)
    assert prev.get("success"), prev
    assert prev.get("source", {}).get("alias") == "data_2"


def test_health_version(client):
    health = client.get("/api/health").json()
    assert health["version"] == "0.10.0"
