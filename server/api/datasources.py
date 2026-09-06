from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from server.core.db import get_db
from server.services import auth_service, datasource_service
from server.services.dataset_service import ensure_default_workspace

router = APIRouter(prefix="/api/data-sources", tags=["data-sources"])


class SourceCreate(BaseModel):
    workspace_id: str | None = None
    name: str
    db_type: str = Field(description="mysql | postgresql | mock")
    host: str = "localhost"
    port: int = 5432
    database: str
    username: str
    password: str = ""
    ssl: bool = False


class RegisterTable(BaseModel):
    table_name: str
    name: str | None = None


@router.get("")
def list_sources(workspace_id: str | None = None, db: Session = Depends(get_db)):
    ws = workspace_id or ensure_default_workspace(db).id
    return [datasource_service.serialize_source(s) for s in datasource_service.list_sources(db, ws)]


@router.post("")
def create_source(
    body: SourceCreate,
    db: Session = Depends(get_db),
    user=Depends(auth_service.require_admin),
):
    ws = body.workspace_id or ensure_default_workspace(db).id
    ds = datasource_service.create_source(
        db,
        workspace_id=ws,
        name=body.name,
        db_type=body.db_type,
        host=body.host,
        port=body.port,
        database=body.database,
        username=body.username,
        password=body.password,
        ssl=body.ssl,
        created_by=getattr(user, "id", None) if user else None,
    )
    return datasource_service.serialize_source(ds)


@router.delete("/{source_id}")
def delete_source(source_id: str, db: Session = Depends(get_db), _=Depends(auth_service.require_admin)):
    datasource_service.delete_source(db, source_id)
    return {"ok": True}


@router.post("/{source_id}/test")
def test_source(source_id: str, db: Session = Depends(get_db)):
    return datasource_service.test_source(db, source_id)


@router.get("/{source_id}/tables")
def tables(source_id: str, db: Session = Depends(get_db)):
    return {"tables": datasource_service.list_tables(db, source_id)}


@router.post("/{source_id}/datasets")
def register_dataset(source_id: str, body: RegisterTable, db: Session = Depends(get_db)):
    ds = datasource_service.register_table_as_dataset(
        db, source_id=source_id, table_name=body.table_name, name=body.name
    )
    return {
        "id": ds.id,
        "name": ds.name,
        "workspace_id": ds.workspace_id,
        "source_type": ds.source_type,
        "table_name": ds.table_name,
        "connection_id": ds.connection_id,
        "row_count": ds.row_count,
        "col_count": ds.col_count,
        "status": ds.status,
    }
