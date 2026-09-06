from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from server.core.db import get_db
from server.services import auth_service, prompt_service

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


class PromptCreate(BaseModel):
    name: str = Field(default=prompt_service.DEFAULT_PROMPT_NAME)
    content: str
    role: str = "system"
    activate: bool = False


class PromptActivate(BaseModel):
    version: int


@router.get("")
def list_prompts(name: str | None = None, db: Session = Depends(get_db)):
    return [prompt_service.serialize_prompt(p) for p in prompt_service.list_prompts(db, name=name)]


@router.post("")
def create_prompt(
    body: PromptCreate,
    db: Session = Depends(get_db),
    user=Depends(auth_service.require_admin),
):
    row = prompt_service.create_prompt_version(
        db,
        name=body.name,
        content=body.content,
        role=body.role,
        activate=body.activate,
        created_by=getattr(user, "id", None) if user else None,
    )
    return prompt_service.serialize_prompt(row)


@router.post("/{name}/activate")
def activate(
    name: str,
    body: PromptActivate,
    db: Session = Depends(get_db),
    user=Depends(auth_service.require_admin),
):
    row = prompt_service.activate_prompt(
        db, name=name, version=body.version, actor=getattr(user, "id", None) if user else None
    )
    return prompt_service.serialize_prompt(row)
