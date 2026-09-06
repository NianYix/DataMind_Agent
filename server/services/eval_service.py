from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from evaluation import list_suites, load_suite
from evaluation.runner import run_suite
from server.models import EvalCaseResult, EvalRun


def start_evaluation(db: Session, suite_id: str, mode: str = "mock") -> EvalRun:
    load_suite(suite_id)  # validate early
    if mode not in {"mock", "live"}:
        raise ValueError("mode must be mock or live")
    return run_suite(db, suite_id, mode=mode)


def list_evaluations(db: Session, limit: int = 50) -> list[EvalRun]:
    return db.query(EvalRun).order_by(EvalRun.created_at.desc()).limit(min(limit, 200)).all()


def get_evaluation(db: Session, eval_id: str) -> EvalRun | None:
    return db.get(EvalRun, eval_id)


def list_case_results(db: Session, eval_id: str) -> list[EvalCaseResult]:
    return (
        db.query(EvalCaseResult)
        .filter(EvalCaseResult.eval_run_id == eval_id)
        .order_by(EvalCaseResult.created_at.asc())
        .all()
    )


def serialize_run(run: EvalRun, *, cases: list[EvalCaseResult] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": run.id,
        "suite_id": run.suite_id,
        "mode": run.mode,
        "status": run.status,
        "summary_json": run.summary_json,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }
    if cases is not None:
        payload["cases"] = [serialize_case(c) for c in cases]
    return payload


def serialize_case(c: EvalCaseResult) -> dict[str, Any]:
    return {
        "id": c.id,
        "case_id": c.case_id,
        "agent_run_id": c.agent_run_id,
        "status": c.status,
        "scores_json": c.scores_json,
        "final_answer": c.final_answer,
        "latency_ms": c.latency_ms,
        "input_tokens": c.input_tokens,
        "output_tokens": c.output_tokens,
        "steps": c.steps,
        "tool_stats_json": c.tool_stats_json,
        "error": c.error,
    }


def available_suites() -> list[dict[str, Any]]:
    return list_suites()
