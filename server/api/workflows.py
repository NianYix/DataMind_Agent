from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from server.core.db import get_db
from server.services import auth_service, workflow_service

router = APIRouter(prefix="/api", tags=["workflows"])


class WorkflowCreate(BaseModel):
    workspace_id: str
    name: str = "Untitled workflow"
    description: str | None = None
    graph: dict[str, Any] | None = None
    template_id: str | None = None


class WorkflowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    graph: dict[str, Any] | None = None
    enabled: bool | None = None


class WorkflowRunBody(BaseModel):
    question: str | None = None
    dataset_id: str | None = Field(default=None)


@router.get("/workflow-templates")
def list_templates():
    return workflow_service.list_templates()


@router.get("/workflows")
def list_workflows(workspace_id: str, db: Session = Depends(get_db)):
    return [workflow_service.serialize_workflow(w) for w in workflow_service.list_workflows(db, workspace_id)]


@router.post("/workflows")
def create_workflow(
    body: WorkflowCreate,
    db: Session = Depends(get_db),
    _=Depends(auth_service.require_admin),
):
    w = workflow_service.create_workflow(
        db,
        workspace_id=body.workspace_id,
        name=body.name,
        description=body.description,
        graph=body.graph,
        template_id=body.template_id,
    )
    return workflow_service.serialize_workflow(w)


@router.get("/workflows/{workflow_id}")
def get_workflow(workflow_id: str, db: Session = Depends(get_db)):
    return workflow_service.serialize_workflow(workflow_service.get_workflow(db, workflow_id))


@router.put("/workflows/{workflow_id}")
def update_workflow(
    workflow_id: str,
    body: WorkflowUpdate,
    db: Session = Depends(get_db),
    _=Depends(auth_service.require_admin),
):
    w = workflow_service.update_workflow(
        db,
        workflow_id,
        name=body.name,
        description=body.description,
        graph=body.graph,
        enabled=body.enabled,
    )
    return workflow_service.serialize_workflow(w)


@router.delete("/workflows/{workflow_id}")
def delete_workflow(
    workflow_id: str,
    db: Session = Depends(get_db),
    _=Depends(auth_service.require_admin),
):
    workflow_service.delete_workflow(db, workflow_id)
    return {"ok": True}


@router.post("/workflows/{workflow_id}/runs")
def start_run(workflow_id: str, body: WorkflowRunBody, db: Session = Depends(get_db)):
    run = workflow_service.start_run(
        db,
        workflow_id,
        question=body.question,
        dataset_id=body.dataset_id,
    )
    return workflow_service.serialize_run(run)


@router.get("/workflow-runs/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db)):
    return workflow_service.serialize_run(workflow_service.get_run(db, run_id))


@router.get("/workflow-runs/{run_id}/steps")
def list_steps(run_id: str, db: Session = Depends(get_db)):
    return [workflow_service.serialize_step(s) for s in workflow_service.list_steps(db, run_id)]
