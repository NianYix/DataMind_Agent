from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from server.core.config import get_settings
from server.models import Workflow, WorkflowRun, WorkflowRunStep
from workflow.analyze import run_analyze
from workflow.conditions import eval_condition
from workflow.validate import validate_graph


def _nodes_by_id(graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(n["id"]): n for n in graph.get("nodes") or [] if isinstance(n, dict) and n.get("id")}


def _out_edges(graph: dict[str, Any], node_id: str) -> list[dict[str, Any]]:
    return [e for e in (graph.get("edges") or []) if isinstance(e, dict) and str(e.get("from")) == node_id]


def _next_node_id(graph: dict[str, Any], node_id: str, *, branch: str | None = None) -> str | None:
    edges = _out_edges(graph, node_id)
    if not edges:
        return None
    if branch is None:
        # prefer edge without when
        plain = [e for e in edges if e.get("when") is None]
        pick = plain[0] if plain else edges[0]
        return str(pick.get("to"))
    matched = [e for e in edges if str(e.get("when")) == branch]
    if matched:
        return str(matched[0].get("to"))
    return None


def run_workflow(
    db: Session,
    workflow: Workflow,
    *,
    overrides: dict[str, Any] | None = None,
) -> WorkflowRun:
    settings = get_settings()
    graph = workflow.graph_json or {}
    errs = validate_graph(graph)
    if errs:
        raise ValueError("; ".join(errs))

    overrides = overrides or {}
    run = WorkflowRun(
        workflow_id=workflow.id,
        workspace_id=workflow.workspace_id,
        status="running",
        context_json={},
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    nodes = _nodes_by_id(graph)
    start = next(n for n in nodes.values() if n.get("type") == "start")
    context: dict[str, Any] = {}
    start_cfg = dict(start.get("config") or {})
    if start_cfg.get("question"):
        context["question"] = start_cfg["question"]
    if start_cfg.get("dataset_id"):
        context["dataset_id"] = start_cfg["dataset_id"]
    if overrides.get("question"):
        context["question"] = overrides["question"]
    if overrides.get("dataset_id"):
        context["dataset_id"] = overrides["dataset_id"]

    current_id: str | None = str(start["id"])
    seq = 0
    started = time.time()
    visited = 0

    try:
        while current_id:
            if time.time() - started > settings.workflow_timeout_sec:
                raise TimeoutError("WORKFLOW_TIMEOUT")
            visited += 1
            if visited > 50:
                raise RuntimeError("workflow walk exceeded max hops")

            node = nodes.get(current_id)
            if not node:
                raise RuntimeError(f"missing node {current_id}")
            ntype = str(node.get("type"))
            seq += 1
            step = WorkflowRunStep(
                run_id=run.id,
                seq=seq,
                node_id=current_id,
                node_type=ntype,
                status="running",
                input_json={"context": dict(context), "config": node.get("config") or {}},
            )
            db.add(step)
            db.commit()
            db.refresh(step)

            try:
                output: dict[str, Any] = {}
                branch: str | None = None

                if ntype == "start":
                    output = {"context": {"question": context.get("question"), "dataset_id": context.get("dataset_id")}}
                elif ntype == "analyze":
                    result = run_analyze(db, context, workflow.workspace_id)
                    context["final_answer"] = result.get("final_answer")
                    if result.get("agent_run_id"):
                        context["agent_run_id"] = result["agent_run_id"]
                        step.agent_run_id = str(result["agent_run_id"])
                    if result.get("conversation_id"):
                        context["conversation_id"] = result["conversation_id"]
                    output = result
                elif ntype == "condition":
                    ok = eval_condition(context, node.get("config") if isinstance(node.get("config"), dict) else {})
                    branch = "true" if ok else "false"
                    output = {"result": ok, "branch": branch}
                elif ntype == "end":
                    output = {"label": (node.get("config") or {}).get("label"), "final_answer": context.get("final_answer")}
                    step.status = "done"
                    step.output_json = output
                    db.commit()
                    run.status = "done"
                    run.context_json = context
                    run.finished_at = datetime.now(timezone.utc)
                    db.commit()
                    db.refresh(run)
                    return run
                else:
                    raise RuntimeError(f"unsupported node type: {ntype}")

                step.status = "done"
                step.output_json = output
                db.commit()

                nxt = _next_node_id(graph, current_id, branch=branch)
                if nxt is None:
                    raise RuntimeError(f"no outgoing edge from {current_id}" + (f" when={branch}" if branch else ""))
                current_id = nxt
            except Exception as exc:  # noqa: BLE001
                step.status = "error"
                step.error = str(exc)
                db.commit()
                raise

        raise RuntimeError("workflow ended without end node")
    except Exception as exc:  # noqa: BLE001
        run.status = "error"
        run.error = str(exc)
        run.context_json = context
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)
        return run
