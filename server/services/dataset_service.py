from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from data.parser import SUPPORTED_EXTENSIONS, parse_tabular_file
from data.profiler import profile_dataframe, profile_file_path
from server.core.config import get_settings
from server.models import Dataset, DatasetField, Workspace
from tools.statistics import _load_df


def ensure_default_workspace(db: Session) -> Workspace:
    ws = db.query(Workspace).order_by(Workspace.created_at.asc()).first()
    if ws:
        return ws
    ws = Workspace(name="默认工作空间")
    db.add(ws)
    db.commit()
    db.refresh(ws)
    return ws


def list_workspaces(db: Session) -> list[Workspace]:
    ensure_default_workspace(db)
    return db.query(Workspace).order_by(Workspace.created_at.asc()).all()


def create_workspace(db: Session, name: str) -> Workspace:
    ws = Workspace(name=name)
    db.add(ws)
    db.commit()
    db.refresh(ws)
    return ws


def _persist_profile_fields(db: Session, dataset_id: str, profile: dict) -> None:
    for field in profile["fields"]:
        db.add(
            DatasetField(
                dataset_id=dataset_id,
                name=field["name"],
                inferred_type=field["inferred_type"],
                null_ratio=field["null_ratio"],
                nunique=field["nunique"],
                meta_json=field.get("meta"),
            )
        )


def save_dataset(db: Session, workspace_id: str, file: UploadFile) -> Dataset:
    settings = get_settings()
    ws = db.get(Workspace, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    filename = file.filename or "upload.bin"
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")

    content = file.file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=400, detail=f"File exceeds {settings.max_upload_mb}MB limit")

    dataset_id = str(uuid.uuid4())
    dest_dir = settings.upload_path / workspace_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{dataset_id}{suffix}"
    dest.write_bytes(content)

    try:
        settings = get_settings()
        profile = profile_file_path(
            str(dest),
            filename,
            large_file_mb=settings.large_file_mb,
            sample_rows=settings.profile_sample_rows,
        )
    except Exception as exc:  # noqa: BLE001
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {exc}") from exc

    dataset = Dataset(
        id=dataset_id,
        workspace_id=workspace_id,
        name=filename,
        file_path=str(dest),
        source_type="file",
        row_count=profile["row_count"],
        col_count=profile["col_count"],
        profile_json=profile,
        status="ready",
    )
    db.add(dataset)
    _persist_profile_fields(db, dataset_id, profile)
    db.commit()
    db.refresh(dataset)
    return dataset


def save_sqlite_dataset(
    db: Session,
    workspace_id: str,
    file: UploadFile,
    table_name: str,
    name: str | None = None,
) -> Dataset:
    settings = get_settings()
    ws = db.get(Workspace, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if not table_name or not table_name.strip():
        raise HTTPException(status_code=400, detail="table_name is required")

    filename = file.filename or "data.sqlite"
    suffix = Path(filename).suffix.lower()
    if suffix not in {".db", ".sqlite", ".sqlite3"}:
        raise HTTPException(status_code=400, detail="Only .db/.sqlite/.sqlite3 files are supported")

    content = file.file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=400, detail=f"File exceeds {settings.max_upload_mb}MB limit")

    dataset_id = str(uuid.uuid4())
    dest_dir = settings.upload_path / workspace_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{dataset_id}{suffix}"
    dest.write_bytes(content)

    table = table_name.strip()
    try:
        with sqlite3.connect(dest) as conn:
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        if table not in tables:
            dest.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail=f"Table '{table}' not found. Available: {tables}")
        df = _load_df(str(dest), "sqlite", table)
        profile = profile_dataframe(df, name or f"{filename}:{table}")
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Failed to profile sqlite table: {exc}") from exc

    dataset = Dataset(
        id=dataset_id,
        workspace_id=workspace_id,
        name=name or f"{filename}:{table}",
        file_path=str(dest),
        source_type="sqlite",
        table_name=table,
        row_count=profile["row_count"],
        col_count=profile["col_count"],
        profile_json=profile,
        status="ready",
    )
    db.add(dataset)
    _persist_profile_fields(db, dataset_id, profile)
    db.commit()
    db.refresh(dataset)
    return dataset


def get_dataset(db: Session, dataset_id: str) -> Dataset:
    ds = db.get(Dataset, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return ds
