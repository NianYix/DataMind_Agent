from __future__ import annotations

from fastapi.testclient import TestClient

from evaluation.scorers import aggregate_summary, hallucination_rate, mention_hits, number_hits, score_case
from server.core.db import init_db
from server.main import app


def test_mention_hits():
    score, missing = mention_hits("8月华东销售下降", ["8", "下降", "华东"])
    assert score == 1.0
    assert missing == []
    score2, missing2 = mention_hits("销量上涨", ["下降"])
    assert score2 == 0.0
    assert "下降" in missing2


def test_number_hits_tolerance():
    assert number_hits("约 17.4%", "", [{"value": 17.0, "tolerance": 1.0}]) == 1.0
    assert number_hits("约 30%", "", [{"value": 17.0, "tolerance": 1.0}]) == 0.0


def test_hallucination_heuristic():
    rate = hallucination_rate("下降 17.4 和 999", "tool result 17.4")
    assert rate > 0
    rate2 = hallucination_rate("下降 17.4", "tool 17.4")
    assert rate2 == 0.0


def test_score_case_and_aggregate():
    scores = score_case(
        final_answer="8月华东销售下降约17.4",
        expect={"must_mention": ["8", "下降", "华东"], "numbers": [{"value": 17.4, "tolerance": 1}]},
        tool_stats={"total": 2, "success": 2, "python_total": 1, "python_success": 1, "sql_total": 1, "sql_success": 1},
        tool_blob="17.4",
        steps=5,
    )
    assert scores["task_success"] == 1.0
    assert scores["heuristic"] is True
    summary = aggregate_summary([{**scores, "steps": 5, "latency_ms": 10, "tokens": 100, "cost": None}])
    assert summary["task_success_rate"] == 1.0
    assert summary["cases_total"] == 1


def test_list_suites_and_mock_evaluation():
    init_db()
    client = TestClient(app)
    suites = client.get("/api/evaluation-suites").json()
    assert any(s["id"] == "sales_suite" for s in suites)
    assert suites[0]["case_count"] >= 5

    res = client.post("/api/evaluations", json={"suite_id": "sales_suite", "mode": "mock"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "done"
    assert body["mode"] == "mock"
    assert body["summary_json"]["cases_total"] >= 5
    assert "task_success_rate" in body["summary_json"]
    assert len(body["cases"]) >= 5

    detail = client.get(f"/api/evaluations/{body['id']}").json()
    assert detail["id"] == body["id"]
    summary = client.get(f"/api/evaluations/{body['id']}/summary").json()
    assert summary["summary_json"]["cases_total"] == body["summary_json"]["cases_total"]
