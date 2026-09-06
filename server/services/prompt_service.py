from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from agent.prompts import PLANNER_SYSTEM
from server.models import PromptTemplate
from server.services import audit_service

DEFAULT_PROMPT_NAME = "system_analyst"


def list_prompts(db: Session, name: str | None = None) -> list[PromptTemplate]:
    q = db.query(PromptTemplate)
    if name:
        q = q.filter(PromptTemplate.name == name)
    return q.order_by(PromptTemplate.name.asc(), PromptTemplate.version.desc()).all()


def serialize_prompt(p: PromptTemplate) -> dict[str, Any]:
    return {
        "id": p.id,
        "name": p.name,
        "role": p.role,
        "content": p.content,
        "version": p.version,
        "is_active": p.is_active,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


def create_prompt_version(
    db: Session,
    *,
    name: str,
    content: str,
    role: str = "system",
    activate: bool = False,
    created_by: str | None = None,
) -> PromptTemplate:
    latest = (
        db.query(PromptTemplate)
        .filter(PromptTemplate.name == name)
        .order_by(PromptTemplate.version.desc())
        .first()
    )
    version = (latest.version + 1) if latest else 1
    row = PromptTemplate(
        name=name,
        role=role,
        content=content,
        version=version,
        is_active=False,
        created_by=created_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    audit_service.record(
        db,
        event_type="prompt_create",
        message=f"Created prompt {name} v{version}",
        payload={"name": name, "version": version},
    )
    if activate:
        return activate_prompt(db, name=name, version=version, actor=created_by)
    return row


def activate_prompt(db: Session, *, name: str, version: int, actor: str | None = None) -> PromptTemplate:
    target = (
        db.query(PromptTemplate)
        .filter(PromptTemplate.name == name, PromptTemplate.version == version)
        .first()
    )
    if not target:
        raise HTTPException(status_code=404, detail="Prompt version not found")
    others = db.query(PromptTemplate).filter(PromptTemplate.name == name, PromptTemplate.is_active.is_(True)).all()
    for o in others:
        o.is_active = False
    target.is_active = True
    db.commit()
    db.refresh(target)
    audit_service.record(
        db,
        event_type="prompt_activate",
        message=f"Activated prompt {name} v{version}",
        payload={"name": name, "version": version, "actor": actor},
    )
    return target


def get_active_content(db: Session | None, name: str = DEFAULT_PROMPT_NAME) -> str | None:
    if db is None:
        return None
    row = (
        db.query(PromptTemplate)
        .filter(PromptTemplate.name == name, PromptTemplate.is_active.is_(True))
        .order_by(PromptTemplate.version.desc())
        .first()
    )
    return row.content if row else None


def resolve_role_system(db: Session | None, name: str, fallback: str) -> str:
    override = get_active_content(db, name)
    return override or fallback


def resolve_planner_system(db: Session | None = None) -> str:
    return resolve_role_system(db, DEFAULT_PROMPT_NAME, PLANNER_SYSTEM)
