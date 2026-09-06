from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from server.core.db import get_db
from server.models import Dataset
from server.schemas import AgentRunOut, DatasetOut, WorkspaceCreate, WorkspaceOut
from server.services import chat_service, dataset_service

router = APIRouter(prefix="/api", tags=["workspaces"])


@router.get("/workspaces", response_model=list[WorkspaceOut])
def get_workspaces(db: Session = Depends(get_db)):
    return dataset_service.list_workspaces(db)


@router.post("/workspaces", response_model=WorkspaceOut)
def post_workspace(body: WorkspaceCreate, db: Session = Depends(get_db)):
    return dataset_service.create_workspace(db, body.name)


@router.get("/workspaces/{workspace_id}/datasets", response_model=list[DatasetOut])
def list_datasets(workspace_id: str, db: Session = Depends(get_db)):
    return (
        db.query(Dataset)
        .filter(Dataset.workspace_id == workspace_id)
        .order_by(Dataset.created_at.desc())
        .all()
    )


@router.post("/workspaces/{workspace_id}/datasets", response_model=DatasetOut)
async def upload_dataset(workspace_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    return dataset_service.save_dataset(db, workspace_id, file)


@router.post("/workspaces/{workspace_id}/datasets/sqlite", response_model=DatasetOut)
async def upload_sqlite_dataset(
    workspace_id: str,
    table_name: str = Form(...),
    name: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    return dataset_service.save_sqlite_dataset(db, workspace_id, file, table_name, name)


@router.get("/workspaces/{workspace_id}/agent-runs", response_model=list[AgentRunOut])
def list_workspace_runs(workspace_id: str, db: Session = Depends(get_db)):
    return chat_service.list_runs_for_workspace(db, workspace_id)


@router.get("/datasets/{dataset_id}", response_model=DatasetOut)
def get_dataset(dataset_id: str, db: Session = Depends(get_db)):
    return dataset_service.get_dataset(db, dataset_id)
