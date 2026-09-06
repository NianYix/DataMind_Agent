from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from agent.lc.collaboration import collaboration_snapshot, enter_role, patch_blackboard, record_handoff
from agent.lc.nodes import route_after_insight
from server.core.config import reload_settings
from server.core.db import SessionLocal, init_db
from server.main import app
from server.models import AgentRun, Conversation, Dataset, Workspace


def test_enter_role_and_handoffs(monkeypatch):
    monkeypatch.setenv("MULTI_AGENT_ENABLED", "true")
    reload_settings()
    state: dict = {"agents_involved": [], "handoffs": [], "last_agent": None, "blackboard": {}}
    s1 = enter_role(state, "Understand", reason="start")
    state = {**state, **s1}
    assert state["agents_involved"] == ["Understand"]
    assert state["handoffs"] == []

    s2 = enter_role(state, "Planner", reason="plan")
    state = {**state, **s2}
    assert state["agents_involved"] == ["Understand", "Planner"]
    assert len(state["handoffs"]) == 1
    assert state["handoffs"][0]["from_agent"] == "Understand"
    assert state["handoffs"][0]["to_agent"] == "Planner"

    board = patch_blackboard(state, {"key_metrics": "x=1"})
    state = {**state, **board}
    assert state["blackboard"]["key_metrics"] == "x=1"

    snap = collaboration_snapshot(state)
    assert snap["enabled"] is True
    assert "Planner" in snap["agents_involved"]


def test_multi_agent_disabled_skips_handoffs(monkeypatch):
    monkeypatch.setenv("MULTI_AGENT_ENABLED", "false")
    reload_settings()
    state = {"agents_involved": [], "handoffs": [], "last_agent": "A"}
    out = enter_role(state, "B", reason="x")
    assert out == {}
    hop = record_handoff(state, from_agent="A", to_agent="B", reason="x")
    assert hop == {}


def test_route_after_insight_critic_switch(monkeypatch):
    monkeypatch.setenv("CRITIC_ENABLED", "false")
    reload_settings()
    assert route_after_insight({}) == "report"

    monkeypatch.setenv("CRITIC_ENABLED", "true")
    reload_settings()
    assert route_after_insight({}) == "critic"


def test_collaboration_api(monkeypatch):
    monkeypatch.setenv("MULTI_AGENT_ENABLED", "true")
    reload_settings()
    init_db()
    db = SessionLocal()
    try:
        ws = Workspace(id=str(uuid.uuid4()), name="ma-ws")
        db.add(ws)
        db.commit()
        ds = Dataset(
            id=str(uuid.uuid4()),
            workspace_id=ws.id,
            name="ds",
            source_type="file",
            file_path="x.csv",
            row_count=1,
            col_count=1,
        )
        db.add(ds)
        db.commit()
        conv = Conversation(id=str(uuid.uuid4()), workspace_id=ws.id, dataset_id=ds.id, title="t")
        db.add(conv)
        db.commit()
        run = AgentRun(
            id=str(uuid.uuid4()),
            conversation_id=conv.id,
            question="q",
            status="done",
            state_json={
                "multi_agent": {
                    "enabled": True,
                    "critic_enabled": False,
                    "agents_involved": ["Understand", "Planner", "Supervisor"],
                    "handoffs": [
                        {
                            "id": "h1",
                            "from_agent": "Understand",
                            "to_agent": "Planner",
                            "reason": "plan",
                        }
                    ],
                    "blackboard": {"key_metrics": "ok"},
                    "critic_result": None,
                }
            },
        )
        db.add(run)
        db.commit()
        run_id = run.id
    finally:
        db.close()

    client = TestClient(app)
    res = client.get(f"/api/agent-runs/{run_id}/collaboration")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["agents_involved"][0] == "Understand"
    assert len(body["handoffs"]) == 1
    assert body["blackboard"]["key_metrics"] == "ok"

    settings = client.get("/api/settings").json()
    assert "multi_agent_enabled" in settings
    assert "critic_enabled" in settings

    health = client.get("/api/health").json()
    assert health["version"] == "0.8.0"
