from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from server.core.db import get_db
from server.services import auth_service, knowledge_service
from server.services.dataset_service import ensure_default_workspace

router = APIRouter(prefix="/api", tags=["knowledge"])


class KnowledgeBaseCreate(BaseModel):
    workspace_id: str | None = None
    name: str
    description: str | None = None


class KnowledgeSearchBody(BaseModel):
    query: str
    top_k: int | None = Field(default=None, ge=1, le=20)


@router.get("/knowledge-bases")
def list_kbs(workspace_id: str | None = None, db: Session = Depends(get_db)):
    ws = workspace_id or ensure_default_workspace(db).id
    return [knowledge_service.serialize_kb(kb) for kb in knowledge_service.list_knowledge_bases(db, ws)]


@router.post("/knowledge-bases")
def create_kb(
    body: KnowledgeBaseCreate,
    db: Session = Depends(get_db),
    _=Depends(auth_service.require_admin),
):
    ws = body.workspace_id or ensure_default_workspace(db).id
    kb = knowledge_service.create_knowledge_base(db, workspace_id=ws, name=body.name, description=body.description)
    return knowledge_service.serialize_kb(kb)


@router.delete("/knowledge-bases/{kb_id}")
def delete_kb(kb_id: str, db: Session = Depends(get_db), _=Depends(auth_service.require_admin)):
    knowledge_service.delete_knowledge_base(db, kb_id)
    return {"ok": True}


@router.get("/knowledge-bases/{kb_id}/documents")
def list_docs(kb_id: str, db: Session = Depends(get_db)):
    return [knowledge_service.serialize_doc(d) for d in knowledge_service.list_documents(db, kb_id)]


@router.post("/knowledge-bases/{kb_id}/documents")
def upload_doc(
    kb_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _=Depends(auth_service.require_admin),
):
    doc = knowledge_service.upload_document(db, kb_id=kb_id, file=file)
    return knowledge_service.serialize_doc(doc)


@router.delete("/knowledge-documents/{doc_id}")
def delete_doc(doc_id: str, db: Session = Depends(get_db), _=Depends(auth_service.require_admin)):
    knowledge_service.delete_document(db, doc_id)
    return {"ok": True}


@router.post("/knowledge-bases/{kb_id}/search")
def search_kb(kb_id: str, body: KnowledgeSearchBody, db: Session = Depends(get_db)):
    return knowledge_service.search(db, knowledge_base_id=kb_id, query=body.query, top_k=body.top_k)
