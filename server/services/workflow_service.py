from __future__ import annotations

import copy
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from server.models import Workflow, WorkflowRun, WorkflowRunStep
from workflow.engine import run_workflow
from workflow.templates import BUILTIN_TEMPLATES, get_template
from workflow.validate import validate_graph


def serialize_workflow(w: Workflow) -> dict[str, Any]:
    return {
        "id": w.id,
        "workspace_id": w.workspace_id,
        "name": w.name,
        "description": w.description,
        "version": w.version,
        "enabled": w.enabled,
        "graph": w.graph_json,
        "is_template": w.is_template,
        "created_at": w.created_at.isoformat() if w.created_at else None,
    }


def serialize_run(r: WorkflowRun) -> dict[str, Any]:
    return {
        "id": r.id,
        "workflow_id": r.workflow_id,
        "workspace_id": r.workspace_id,
        "status": r.status,
        "context": r.context_json or {},
        "error": r.error,
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "finished_at": r.finished_at.isoformat() if r.finished_at else None,
    }


def serialize_step(s: WorkflowRunStep) -> dict[str, Any]:
    return {
        "id": s.id,
        "run_id": s.run_id,
        "seq": s.seq,
        "node_id": s.node_id,
        "node_type": s.node_type,
        "status": s.status,
        "input": s.input_json,
        "output": s.output_json,
        "error": s.error,
        "agent_run_id": s.agent_run_id,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


def list_templates() -> list[dict[str, Any]]:
    return [
        {
            "id": t["id"],
            "name": t["name"],
            "description": t.get("description"),
            "graph": t["graph"],
        }
        for t in BUILTIN_TEMPLATES
    ]


def list_workflows(db: Session, workspace_id: str) -> list[Workflow]:
    return (
        db.query(Workflow)
        .filter(Workflow.workspace_id == workspace_id, Workflow.is_template.is_(False))
        .order_by(Workflow.created_at.desc())
        .all()
    )


def get_workflow(db: Session, workflow_id: str) -> Workflow:
    w = db.get(Workflow, workflow_id)
    if not w:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return w


def create_workflow(
    db: Session,
    *,
    workspace_id: str,
    name: str,
    description: str | None = None,
    graph: dict[str, Any] | None = None,
    template_id: str | None = None,
) -> Workflow:
    if template_id:
        tpl = get_template(template_id)
        if not tpl:
            raise HTTPException(status_code=404, detail="Template not found")
        graph = copy.deepcopy(tpl["graph"])
        if not name:
            name = str(tpl["name"])
    if not graph:
        raise HTTPException(status_code=400, detail="graph or template_id required")
    errs = validate_graph(graph)
    if errs:
        raise HTTPException(status_code=400, detail={"validation_errors": errs})
    w = Workflow(
        workspace_id=workspace_id,
        name=name or "Untitled workflow",
        description=description,
        graph_json=graph,
        enabled=True,
        is_template=False,
        version=1,
    )
    db.add(w)
    db.commit()
    db.refresh(w)
    return w


def update_workflow(
    db: Session,
    workflow_id: str,
    *,
    name: str | None = None,
    description: str | None = None,
    graph: dict[str, Any] | None = None,
    enabled: bool | None = None,
) -> Workflow:
    w = get_workflow(db, workflow_id)
    if name is not None:
        w.name = name
    if description is not None:
        w.description = description
    if enabled is not None:
        w.enabled = enabled
    if graph is not None:
        errs = validate_graph(graph)
        if errs:
            raise HTTPException(status_code=400, detail={"validation_errors": errs})
        w.graph_json = graph
        w.version = int(w.version or 1) + 1
    db.commit()
    db.refresh(w)
    return w


def delete_workflow(db: Session, workflow_id: str) -> None:
    w = get_workflow(db, workflow_id)
    db.delete(w)
    db.commit()


def start_run(
    db: Session,
    workflow_id: str,
    *,
    question: str | None = None,
    dataset_id: str | None = None,
) -> WorkflowRun:
    w = get_workflow(db, workflow_id)
    if not w.enabled:
        raise HTTPException(status_code=400, detail="Workflow disabled")
    overrides: dict[str, Any] = {}
    if question:
        overrides["question"] = question
    if dataset_id:
        overrides["dataset_id"] = dataset_id
    try:
        return run_workflow(db, w, overrides=overrides)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def get_run(db: Session, run_id: str) -> WorkflowRun:
    r = db.get(WorkflowRun, run_id)
    if not r:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return r


def list_steps(db: Session, run_id: str) -> list[WorkflowRunStep]:
    get_run(db, run_id)
    return (
        db.query(WorkflowRunStep)
        .filter(WorkflowRunStep.run_id == run_id)
        .order_by(WorkflowRunStep.seq.asc())
        .all()
    )
