from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from knowledge.embeddings import embed_query
from knowledge.extract import SUPPORTED_EXTENSIONS
from knowledge.ingest import ingest_file
from knowledge.store import delete_document_vectors, delete_knowledge_base_vectors, query_knowledge
from server.core.config import get_settings
from server.models import KnowledgeBase, KnowledgeDocument, Workspace
from server.services import audit_service


def serialize_kb(kb: KnowledgeBase) -> dict[str, Any]:
    return {
        "id": kb.id,
        "workspace_id": kb.workspace_id,
        "name": kb.name,
        "description": kb.description,
        "created_at": kb.created_at.isoformat() if kb.created_at else None,
    }


def serialize_doc(doc: KnowledgeDocument) -> dict[str, Any]:
    return {
        "id": doc.id,
        "knowledge_base_id": doc.knowledge_base_id,
        "filename": doc.filename,
        "content_type": doc.content_type,
        "status": doc.status,
        "chunk_count": doc.chunk_count,
        "error": doc.error,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }


def list_knowledge_bases(db: Session, workspace_id: str) -> list[KnowledgeBase]:
    return (
        db.query(KnowledgeBase)
        .filter(KnowledgeBase.workspace_id == workspace_id)
        .order_by(KnowledgeBase.created_at.desc())
        .all()
    )


def create_knowledge_base(
    db: Session,
    *,
    workspace_id: str,
    name: str,
    description: str | None = None,
) -> KnowledgeBase:
    if not db.get(Workspace, workspace_id):
        raise HTTPException(status_code=404, detail="Workspace not found")
    kb = KnowledgeBase(workspace_id=workspace_id, name=name, description=description)
    db.add(kb)
    db.commit()
    db.refresh(kb)
    audit_service.record(db, event_type="knowledge_base_create", message=f"Created KB {name}", payload={"id": kb.id})
    return kb


def get_knowledge_base(db: Session, kb_id: str) -> KnowledgeBase:
    kb = db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return kb


def delete_knowledge_base(db: Session, kb_id: str) -> None:
    kb = get_knowledge_base(db, kb_id)
    delete_knowledge_base_vectors(knowledge_base_id=kb.id)
    db.delete(kb)
    db.commit()
    audit_service.record(db, event_type="knowledge_base_delete", message=f"Deleted KB {kb_id}")


def list_documents(db: Session, kb_id: str) -> list[KnowledgeDocument]:
    get_knowledge_base(db, kb_id)
    return (
        db.query(KnowledgeDocument)
        .filter(KnowledgeDocument.knowledge_base_id == kb_id)
        .order_by(KnowledgeDocument.created_at.desc())
        .all()
    )


def upload_document(db: Session, *, kb_id: str, file: UploadFile) -> KnowledgeDocument:
    kb = get_knowledge_base(db, kb_id)
    filename = file.filename or "doc.txt"
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")

    settings = get_settings()
    content = file.file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=400, detail=f"File exceeds {settings.max_upload_mb}MB limit")

    doc_id = str(uuid.uuid4())
    dest_dir = settings.knowledge_path / kb.id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{doc_id}{suffix}"
    dest.write_bytes(content)

    doc = KnowledgeDocument(
        id=doc_id,
        knowledge_base_id=kb.id,
        filename=filename,
        file_path=str(dest),
        content_type=suffix.lstrip("."),
        status="indexing",
        chunk_count=0,
    )
    db.add(doc)
    db.commit()

    try:
        count = ingest_file(
            knowledge_base_id=kb.id,
            workspace_id=kb.workspace_id,
            doc_id=doc_id,
            filename=filename,
            file_path=dest,
        )
        doc.status = "ready"
        doc.chunk_count = count
        doc.error = None
        db.commit()
        audit_service.record(
            db,
            event_type="knowledge_ingest",
            message=f"Ingested {filename}",
            payload={"doc_id": doc_id, "chunks": count},
        )
    except Exception as exc:  # noqa: BLE001
        doc.status = "error"
        doc.error = str(exc)[:2000]
        db.commit()
        audit_service.record(
            db,
            event_type="knowledge_ingest",
            message=f"Ingest failed {filename}",
            level="error",
            payload={"doc_id": doc_id, "error": doc.error},
        )
        raise HTTPException(status_code=400, detail=doc.error) from exc

    db.refresh(doc)
    return doc


def delete_document(db: Session, doc_id: str) -> None:
    doc = db.get(KnowledgeDocument, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    delete_document_vectors(knowledge_base_id=doc.knowledge_base_id, doc_id=doc.id)
    path = Path(doc.file_path)
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass
    db.delete(doc)
    db.commit()
    audit_service.record(db, event_type="knowledge_doc_delete", message=f"Deleted doc {doc_id}")


def search(
    db: Session,
    *,
    workspace_id: str | None = None,
    knowledge_base_id: str | None = None,
    query: str,
    top_k: int | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    k = top_k or settings.rag_top_k
    kb_ids: list[str] = []
    if knowledge_base_id:
        kb = get_knowledge_base(db, knowledge_base_id)
        kb_ids = [kb.id]
        workspace_id = kb.workspace_id
    elif workspace_id:
        kb_ids = [kb.id for kb in list_knowledge_bases(db, workspace_id)]
    else:
        return {"success": True, "results": [], "message": "no knowledge base specified"}

    ready = (
        db.query(KnowledgeDocument)
        .filter(KnowledgeDocument.knowledge_base_id.in_(kb_ids), KnowledgeDocument.status == "ready")
        .count()
    )
    if not ready:
        return {"success": True, "results": [], "message": "no documents"}

    try:
        qvec = embed_query(query)
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": str(exc), "results": []}

    hits = query_knowledge(knowledge_base_ids=kb_ids, query_embedding=qvec, top_k=k)
    return {"success": True, "results": hits, "query": query}
