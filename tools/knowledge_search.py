from __future__ import annotations

from typing import Any

from server.core.db import SessionLocal
from server.services import knowledge_service


def knowledge_search(
    *,
    query: str,
    knowledge_base_id: str | None = None,
    top_k: int | None = None,
    workspace_id: str | None = None,
) -> dict[str, Any]:
    if not (query or "").strip():
        return {"success": False, "error": "query is required", "results": []}
    db = SessionLocal()
    try:
        return knowledge_service.search(
            db,
            workspace_id=workspace_id,
            knowledge_base_id=knowledge_base_id,
            query=query.strip(),
            top_k=top_k,
        )
    finally:
        db.close()
