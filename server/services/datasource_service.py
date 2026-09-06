from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from data.connectors import ConnectionConfig, get_connector
from data.profiler import profile_dataframe
from server.core.config import get_settings
from server.core.crypto import decrypt_secret, encrypt_secret, mask_password
from server.models import DataSource, Dataset, DatasetField, Workspace
from server.services import audit_service
import pandas as pd


def _cfg(ds: DataSource, password: str | None = None) -> ConnectionConfig:
    settings = get_settings()
    return ConnectionConfig(
        db_type=ds.db_type,
        host=ds.host,
        port=ds.port,
        database=ds.database,
        username=ds.username,
        password=password if password is not None else decrypt_secret(ds.password_enc),
        ssl=bool(ds.ssl),
        timeout_sec=settings.db_connect_timeout_sec,
    )


def serialize_source(ds: DataSource) -> dict[str, Any]:
    return {
        "id": ds.id,
        "workspace_id": ds.workspace_id,
        "name": ds.name,
        "db_type": ds.db_type,
        "host": ds.host,
        "port": ds.port,
        "database": ds.database,
        "username": ds.username,
        "password": mask_password(),
        "ssl": ds.ssl,
        "created_at": ds.created_at.isoformat() if ds.created_at else None,
    }


def list_sources(db: Session, workspace_id: str) -> list[DataSource]:
    return db.query(DataSource).filter(DataSource.workspace_id == workspace_id).order_by(DataSource.created_at.desc()).all()


def create_source(
    db: Session,
    *,
    workspace_id: str,
    name: str,
    db_type: str,
    host: str,
    port: int,
    database: str,
    username: str,
    password: str,
    ssl: bool = False,
    created_by: str | None = None,
) -> DataSource:
    if db_type not in {"mysql", "postgresql", "mock"}:
        raise HTTPException(status_code=400, detail="db_type must be mysql, postgresql, or mock")
    ws = db.get(Workspace, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    ds = DataSource(
        workspace_id=workspace_id,
        name=name,
        db_type=db_type,
        host=host,
        port=port,
        database=database,
        username=username,
        password_enc=encrypt_secret(password or "mock"),
        ssl=ssl,
        created_by=created_by,
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)
    audit_service.record(db, event_type="datasource_create", message=f"Created data source {name}", payload={"id": ds.id, "db_type": db_type})
    return ds


def get_source(db: Session, source_id: str) -> DataSource:
    ds = db.get(DataSource, source_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Data source not found")
    return ds


def delete_source(db: Session, source_id: str) -> None:
    ds = get_source(db, source_id)
    db.delete(ds)
    db.commit()
    audit_service.record(db, event_type="datasource_delete", message=f"Deleted data source {source_id}")


def test_source(db: Session, source_id: str) -> dict[str, Any]:
    ds = get_source(db, source_id)
    connector = get_connector(ds.db_type, force_mock=ds.db_type == "mock")
    result = connector.test_connection(_cfg(ds))
    audit_service.record(
        db,
        event_type="datasource_test",
        message=f"Test connection {ds.name}",
        level="info" if result.get("ok") else "error",
        payload={"id": ds.id, "ok": result.get("ok"), "error": result.get("error")},
    )
    return result


def list_tables(db: Session, source_id: str) -> list[str]:
    ds = get_source(db, source_id)
    connector = get_connector(ds.db_type, force_mock=ds.db_type == "mock")
    return connector.list_tables(_cfg(ds))


def register_table_as_dataset(
    db: Session,
    *,
    source_id: str,
    table_name: str,
    name: str | None = None,
) -> Dataset:
    ds = get_source(db, source_id)
    connector = get_connector(ds.db_type, force_mock=ds.db_type == "mock")
    sample = connector.fetch_sample(_cfg(ds), table_name, limit=min(1000, get_settings().profile_sample_rows))
    if not sample.get("success"):
        raise HTTPException(status_code=400, detail=sample.get("error") or "Failed to sample table")
    rows = sample.get("rows") or []
    df = pd.DataFrame(rows)
    profile = profile_dataframe(df, name or table_name) if len(df) else {
        "fields": [{"name": c, "inferred_type": "string", "null_ratio": 0, "nunique": 0} for c in (sample.get("columns") or [])],
        "row_count": 0,
        "col_count": len(sample.get("columns") or []),
        "summary_text": f"Remote table {table_name}",
        "numeric_fields": [],
        "time_range": None,
    }
    dataset_id = str(uuid.uuid4())
    dataset = Dataset(
        id=dataset_id,
        workspace_id=ds.workspace_id,
        name=name or f"{ds.name}.{table_name}",
        file_path=f"remote://{ds.id}/{table_name}",
        source_type=ds.db_type if ds.db_type != "mock" else "mock",
        table_name=table_name,
        connection_id=ds.id,
        row_count=int(profile.get("row_count") or len(rows)),
        col_count=int(profile.get("col_count") or len(df.columns)),
        profile_json=profile,
        status="ready",
    )
    db.add(dataset)
    for field in profile.get("fields") or []:
        db.add(
            DatasetField(
                dataset_id=dataset_id,
                name=field["name"],
                inferred_type=field.get("inferred_type") or "string",
                null_ratio=float(field.get("null_ratio") or 0),
                nunique=int(field.get("nunique") or 0),
                meta_json=field.get("meta"),
            )
        )
    db.commit()
    db.refresh(dataset)
    audit_service.record(
        db,
        event_type="datasource_register_table",
        message=f"Registered {table_name} as dataset",
        payload={"source_id": ds.id, "dataset_id": dataset.id},
    )
    return dataset


def execute_remote_sql(db: Session, connection_id: str, sql: str, max_rows: int | None = None) -> dict[str, Any]:
    ds = get_source(db, connection_id)
    connector = get_connector(ds.db_type, force_mock=ds.db_type == "mock")
    limit = max_rows or get_settings().sql_max_rows
    return connector.execute_readonly(_cfg(ds), sql, max_rows=limit)
