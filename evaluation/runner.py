from __future__ import annotations

import json
import time
import uuid
from io import BytesIO
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from agent.facade import create_runtime
from agent.state import AgentState
from evaluation import load_suite, resolve_dataset_path
from evaluation.mock_runtime import MockRuntime
from evaluation.scorers import aggregate_summary, score_case
from server.models import AgentRun, AgentStep, Dataset, EvalCaseResult, EvalRun, ToolCall
from server.services.chat_service import create_conversation
from server.services.dataset_service import ensure_default_workspace, save_dataset


class _Upload:
    def __init__(self, path: Path) -> None:
        self.filename = path.name
        self.file = BytesIO(path.read_bytes())


def _ensure_dataset(db: Session, rel_path: str) -> Dataset:
    path = resolve_dataset_path(rel_path)
    ws = ensure_default_workspace(db)
    existing = (
        db.query(Dataset)
        .filter(Dataset.workspace_id == ws.id, Dataset.name == path.name)
        .order_by(Dataset.created_at.desc())
        .first()
    )
    if existing:
        return existing
    return save_dataset(db, ws.id, _Upload(path))  # type: ignore[arg-type]


def _tool_stats(db: Session, agent_run_id: str | None) -> tuple[dict[str, Any], str]:
    if not agent_run_id:
        return (
            {
                "total": 0,
                "success": 0,
                "python_total": 0,
                "python_success": 0,
                "sql_total": 0,
                "sql_success": 0,
            },
            "",
        )
    rows = db.query(ToolCall).filter(ToolCall.run_id == agent_run_id).all()
    total = len(rows)
    success = sum(1 for r in rows if r.success)
    py = [r for r in rows if r.tool_name == "python_execute"]
    sql = [r for r in rows if r.tool_name == "sql_query"]
    blob_parts: list[str] = []
    for r in rows:
        blob_parts.append(json.dumps(r.result, ensure_ascii=False, default=str))
        if r.arguments:
            blob_parts.append(json.dumps(r.arguments, ensure_ascii=False, default=str))
    stats = {
        "total": total,
        "success": success,
        "python_total": len(py),
        "python_success": sum(1 for r in py if r.success),
        "sql_total": len(sql),
        "sql_success": sum(1 for r in sql if r.success),
    }
    return stats, "\n".join(blob_parts)


def run_suite(db: Session, suite_id: str, mode: str = "mock") -> EvalRun:
    suite = load_suite(suite_id)
    eval_id = str(uuid.uuid4())
    run = EvalRun(id=eval_id, suite_id=suite.get("id") or suite_id, mode=mode, status="running")
    db.add(run)
    db.commit()

    case_rows: list[dict[str, Any]] = []
    try:
        for case in suite.get("cases") or []:
            case_rows.append(_run_case(db, eval_id, case, mode=mode))

        summary_inputs: list[dict[str, Any]] = []
        for c in case_rows:
            scores = dict(c.get("scores") or {})
            scores["steps"] = c.get("steps")
            scores["latency_ms"] = c.get("latency_ms")
            scores["tokens"] = (c.get("input_tokens") or 0) + (c.get("output_tokens") or 0)
            scores["cost"] = c.get("cost")
            summary_inputs.append(scores)

        run.summary_json = aggregate_summary(summary_inputs)
        run.status = "done"
        db.commit()
        db.refresh(run)
        return run
    except Exception as exc:  # noqa: BLE001
        run.status = "error"
        run.summary_json = {"error": str(exc)}
        db.commit()
        raise


def _run_case(db: Session, eval_run_id: str, case: dict[str, Any], *, mode: str) -> dict[str, Any]:
    case_id = str(case.get("id") or uuid.uuid4())
    expect = dict(case.get("expect") or {})
    started = time.perf_counter()
    agent_run_id: str | None = None
    final_answer = ""
    input_tokens = 0
    output_tokens = 0
    steps = 0
    error: str | None = None
    status = "passed"
    tool_stats: dict[str, Any] = {
        "total": 0,
        "success": 0,
        "python_total": 0,
        "python_success": 0,
        "sql_total": 0,
        "sql_success": 0,
    }

    try:
        ds = _ensure_dataset(db, str(case.get("dataset")))
        ws = ensure_default_workspace(db)
        conv = create_conversation(db, ws.id, ds.id, title=f"eval:{case_id}")
        run_id = str(uuid.uuid4())
        state = AgentState(
            run_id=run_id,
            conversation_id=conv.id,
            question=str(case.get("question") or ""),
            dataset_id=ds.id,
            dataset_path=ds.file_path,
            source_type=getattr(ds, "source_type", None) or "file",
            table_name=getattr(ds, "table_name", None),
            connection_id=getattr(ds, "connection_id", None),
            schema_info=ds.profile_json if (ds.profile_json or {}).get("fields") else {},
            profile_summary=str((ds.profile_json or {}).get("summary_text") or ""),
            memory={},
        )

        if mode == "mock":
            runtime = MockRuntime(db, expect=expect)
            for event in runtime.run_stream(state):
                if event.event == "final":
                    final_answer = str(event.data.get("answer") or "")
                if event.event == "step" and event.data.get("type") in {
                    "execute",
                    "tool",
                    "Analysis",
                    "supervisor",
                }:
                    steps += 1
            prefer = list(expect.get("prefer_tools") or [])
            tool_stats = {
                "total": 1,
                "success": 1,
                "python_total": 1 if "python_execute" in prefer else 0,
                "python_success": 1 if "python_execute" in prefer else 0,
                "sql_total": 1 if "sql_query" in prefer else 0,
                "sql_success": 1 if "sql_query" in prefer else 0,
            }
            tool_blob = final_answer + " tool ok"
            steps = max(steps, 3)
            input_tokens, output_tokens = 100, 50
            agent_run_id = None
        else:
            agent_run_id = run_id
            db.add(
                AgentRun(
                    id=run_id,
                    conversation_id=conv.id,
                    question=state.question,
                    status="running",
                )
            )
            db.commit()
            runtime = create_runtime(db)
            for event in runtime.run_stream(state):
                if event.event == "final":
                    final_answer = str(event.data.get("answer") or "")
                if event.event == "step" and event.data.get("type") in {
                    "execute",
                    "tool",
                    "Analysis",
                    "supervisor",
                }:
                    steps += 1
                if event.event == "step" and event.data.get("type") == "metrics":
                    input_tokens = int(event.data.get("input_tokens") or 0)
                    output_tokens = int(event.data.get("output_tokens") or 0)

            tool_stats, tool_blob = _tool_stats(db, run_id)
            ar = db.get(AgentRun, run_id)
            if ar:
                input_tokens = ar.input_tokens or input_tokens
                output_tokens = ar.output_tokens or output_tokens
                if not final_answer:
                    final_answer = ar.final_answer or ""
                steps = max(steps, db.query(AgentStep).filter(AgentStep.run_id == run_id).count())

        scores = score_case(
            final_answer=final_answer,
            expect=expect,
            tool_stats=tool_stats,
            tool_blob=tool_blob,
            steps=steps,
        )
        status = "passed" if scores.get("task_success") == 1.0 else "failed"
    except Exception as exc:  # noqa: BLE001
        error = str(exc)
        status = "error"
        tool_stats = {
            "total": 0,
            "success": 0,
            "python_total": 0,
            "python_success": 0,
            "sql_total": 0,
            "sql_success": 0,
        }
        scores = score_case(
            final_answer="",
            expect=expect,
            tool_stats=tool_stats,
            tool_blob="",
            steps=steps,
        )
        scores["task_success"] = 0.0

    latency_ms = int((time.perf_counter() - started) * 1000)
    row = EvalCaseResult(
        eval_run_id=eval_run_id,
        case_id=case_id,
        agent_run_id=agent_run_id,
        status=status,
        scores_json=scores,
        final_answer=final_answer,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        steps=steps,
        tool_stats_json=tool_stats,
        error=error,
    )
    db.add(row)
    db.commit()
    return {
        "case_id": case_id,
        "status": status,
        "scores": scores,
        "latency_ms": latency_ms,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "steps": steps,
        "cost": None,
        "error": error,
    }
