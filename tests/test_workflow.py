from __future__ import annotations

import copy

from fastapi.testclient import TestClient

from server.core.config import reload_settings
from server.core.db import SessionLocal, init_db
from server.main import app
from server.services.dataset_service import ensure_default_workspace
from workflow.conditions import eval_condition
from workflow.templates import CONDITION_BRANCH_GRAPH, STANDARD_ANALYSIS_GRAPH
from workflow.validate import validate_graph


def test_validate_graph_ok():
    assert validate_graph(STANDARD_ANALYSIS_GRAPH) == []


def test_validate_graph_missing_start():
    g = copy.deepcopy(STANDARD_ANALYSIS_GRAPH)
    g["nodes"] = [n for n in g["nodes"] if n["type"] != "start"]
    errs = validate_graph(g)
    assert any("start" in e for e in errs)


def test_condition_ops():
    ctx = {"final_answer": "8月销售下降明显", "meta": {"ok": True}}
    assert eval_condition(ctx, {"path": "final_answer", "op": "contains", "value": "下降"}) is True
    assert eval_condition(ctx, {"path": "final_answer", "op": "eq", "value": "x"}) is False
    assert eval_condition(ctx, {"path": "meta.ok", "op": "truthy"}) is True


def test_workflow_api_mock_run(monkeypatch):
    monkeypatch.setenv("WORKFLOW_MOCK_ANALYZE", "true")
    reload_settings()
    init_db()
    db = SessionLocal()
    try:
        ws = ensure_default_workspace(db)
        ws_id = ws.id
    finally:
        db.close()

    client = TestClient(app)
    templates = client.get("/api/workflow-templates").json()
    assert any(t["id"] == "standard_analysis" for t in templates)

    created = client.post(
        "/api/workflows",
        json={"workspace_id": ws_id, "template_id": "standard_analysis", "name": "demo-wf"},
    )
    assert created.status_code == 200, created.text
    wf = created.json()
    assert wf["id"]
    assert validate_graph(wf["graph"]) == []

    run_res = client.post(f"/api/workflows/{wf['id']}/runs", json={"question": "测试问题"})
    assert run_res.status_code == 200, run_res.text
    run = run_res.json()
    assert run["status"] == "done"
    assert "mock" in str(run.get("context", {}).get("final_answer", "")).lower() or "analysis" in str(
        run.get("context", {}).get("final_answer", "")
    ).lower()

    steps = client.get(f"/api/workflow-runs/{run['id']}/steps").json()
    types = [s["node_type"] for s in steps]
    assert types == ["start", "analyze", "end"]
    assert all(s["status"] == "done" for s in steps)

    health = client.get("/api/health").json()
    assert health["version"] == "0.10.0"


def test_workflow_condition_branch_mock(monkeypatch):
    monkeypatch.setenv("WORKFLOW_MOCK_ANALYZE", "true")
    reload_settings()
    init_db()
    db = SessionLocal()
    try:
        ws = ensure_default_workspace(db)
        ws_id = ws.id
    finally:
        db.close()

    client = TestClient(app)
    # mock answer contains 下降 — use custom graph with contains 下降, mock text has 下降? 
    # mock returns "[mock] analysis complete for: {question}" — put 下降 in question so contains works if we change condition
    # Better: update graph condition to contains "mock"
    graph = copy.deepcopy(CONDITION_BRANCH_GRAPH)
    graph["nodes"][2]["config"] = {"path": "final_answer", "op": "contains", "value": "mock"}

    created = client.post(
        "/api/workflows",
        json={"workspace_id": ws_id, "name": "branch-wf", "graph": graph},
    )
    assert created.status_code == 200, created.text
    wf_id = created.json()["id"]

    run = client.post(f"/api/workflows/{wf_id}/runs", json={"question": "q"}).json()
    assert run["status"] == "done"
    steps = client.get(f"/api/workflow-runs/{run['id']}/steps").json()
    end_steps = [s for s in steps if s["node_type"] == "end"]
    assert len(end_steps) == 1
    assert end_steps[0]["node_id"] == "e1"  # matched / true branch
