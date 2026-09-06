from __future__ import annotations

from fastapi.testclient import TestClient

from data.connectors import ConnectionConfig, MockConnector
from server.core.db import SessionLocal, init_db
from server.main import app
from server.services import auth_service, prompt_service
from server.services.dataset_service import ensure_default_workspace
from tools.http_tools import http_request


def test_mock_connector():
    c = MockConnector()
    cfg = ConnectionConfig("mock", "localhost", 0, "db", "u", "p")
    assert c.test_connection(cfg)["ok"] is True
    assert "sales" in c.list_tables(cfg)
    out = c.execute_readonly(cfg, "SELECT * FROM sales")
    assert out["success"] and out["rows"]


def test_http_allowlist_denies():
    denied = http_request(method="GET", url="https://evil.example/x")
    assert denied["success"] is False
    assert "allowlist" in str(denied.get("error") or "").lower()


def test_prompt_activate_and_datasource_api():
    init_db()
    db = SessionLocal()
    try:
        ensure_default_workspace(db)
        p1 = prompt_service.create_prompt_version(db, name="system_analyst", content="v1 content", activate=True)
        assert p1.is_active
        p2 = prompt_service.create_prompt_version(db, name="system_analyst", content="v2 content", activate=True)
        assert p2.is_active
        db.refresh(p1)
        assert p1.is_active is False
        assert prompt_service.resolve_planner_system(db) == "v2 content"
    finally:
        db.close()

    client = TestClient(app)
    res = client.post(
        "/api/data-sources",
        json={
            "name": "mock-src",
            "db_type": "mock",
            "host": "localhost",
            "port": 1,
            "database": "d",
            "username": "u",
            "password": "p",
        },
    )
    assert res.status_code == 200, res.text
    sid = res.json()["id"]
    assert client.post(f"/api/data-sources/{sid}/test").json()["ok"] is True
    tables = client.get(f"/api/data-sources/{sid}/tables").json()["tables"]
    assert "sales" in tables
    ds = client.post(f"/api/data-sources/{sid}/datasets", json={"table_name": "sales"}).json()
    assert ds["connection_id"] == sid


def test_jwt_roundtrip():
    init_db()
    db = SessionLocal()
    try:
        from server.models import User

        u = db.query(User).filter(User.username == "v5_test_user").first()
        if not u:
            u = User(
                username="v5_test_user",
                password_hash=auth_service.hash_password("secret123"),
                global_role="admin",
            )
            db.add(u)
            db.commit()
            db.refresh(u)
        token = auth_service.create_access_token(u)
        payload = auth_service.decode_token(token)
        assert payload["sub"] == u.id
        assert auth_service.verify_password("secret123", u.password_hash)
    finally:
        db.close()
