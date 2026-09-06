from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from server.core.db import get_db
from server.core.security import require_api_key
from server.services import audit_service, metrics_service, settings_service

router = APIRouter(prefix="/api", tags=["ops"])


class SettingsUpdate(BaseModel):
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    max_agent_steps: int | None = Field(default=None, ge=1, le=100)
    max_tool_retries: int | None = Field(default=None, ge=0, le=10)
    tool_timeout_sec: int | None = Field(default=None, ge=5, le=600)
    run_timeout_sec: int | None = Field(default=None, ge=30, le=3600)
    llm_input_price_per_1k: float | None = None
    llm_output_price_per_1k: float | None = None
    large_file_mb: int | None = Field(default=None, ge=1, le=500)
    profile_sample_rows: int | None = Field(default=None, ge=1000)
    sql_max_rows: int | None = Field(default=None, ge=100, le=100000)
    duckdb_enabled: bool | None = None
    http_url_allowlist: str | None = None
    http_max_response_bytes: int | None = Field(default=None, ge=1024, le=2_000_000)
    web_search_enabled: bool | None = None


@router.get("/settings")
def get_settings_public():
    return settings_service.get_public_settings()


@router.put("/settings")
def put_settings(body: SettingsUpdate, db: Session = Depends(get_db), _: None = Depends(require_api_key)):
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    result = settings_service.update_settings(patch)
    audit_service.record(
        db,
        event_type="settings_update",
        message="Settings updated",
        payload={"keys": list(patch.keys())},
    )
    return result


@router.get("/metrics")
def get_metrics(db: Session = Depends(get_db)):
    return metrics_service.collect_metrics(db)


@router.get("/audit")
def get_audit(limit: int = 100, db: Session = Depends(get_db), _: None = Depends(require_api_key)):
    from server.services.export_service import list_audit_events

    events = list_audit_events(db, limit=min(limit, 500))
    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "run_id": e.run_id,
            "level": e.level,
            "message": e.message,
            "payload_json": e.payload_json,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in events
    ]
