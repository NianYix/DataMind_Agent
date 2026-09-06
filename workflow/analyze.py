from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from server.core.config import get_settings


def run_analyze(db: Session, context: dict[str, Any], workspace_id: str) -> dict[str, Any]:
    """Execute analyze node. Returns {final_answer, agent_run_id?, mock?}."""
    settings = get_settings()
    question = str(context.get("question") or "").strip()
    dataset_id = context.get("dataset_id")
    if not question:
        raise ValueError("analyze requires context.question")

    if settings.workflow_mock_analyze:
        return {
            "final_answer": f"[mock] analysis complete for: {question}",
            "agent_run_id": None,
            "mock": True,
        }

    if not dataset_id:
        raise ValueError("analyze requires context.dataset_id when WORKFLOW_MOCK_ANALYZE=false")

    from agent.facade import create_runtime
    from agent.state import AgentState
    from server.models import Conversation, Message
    from server.services.dataset_service import get_dataset

    ds = get_dataset(db, str(dataset_id))
    if ds.workspace_id != workspace_id:
        raise ValueError("dataset not in workspace")

    conv = Conversation(
        workspace_id=workspace_id,
        dataset_id=ds.id,
        title=f"Workflow · {question[:40]}",
        context_json={"dataset_id": ds.id, "filters": {}, "from_workflow": True},
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    db.add(Message(conversation_id=conv.id, role="user", content=question))
    db.commit()

    profile = ds.profile_json or {}
    run_id = str(uuid.uuid4())
    state = AgentState(
        run_id=run_id,
        conversation_id=conv.id,
        question=question,
        dataset_id=ds.id,
        dataset_path=ds.file_path,
        source_type=getattr(ds, "source_type", None) or "file",
        table_name=getattr(ds, "table_name", None),
        connection_id=getattr(ds, "connection_id", None),
        workspace_id=workspace_id,
        schema_info=profile if profile.get("fields") else {},
        profile_summary=str(profile.get("summary_text") or ""),
        memory={},
    )
    runtime = create_runtime(db)
    final_answer = ""
    for event in runtime.run_stream(state):
        if event.event == "final":
            final_answer = str(event.data.get("answer") or "")
        elif event.event == "error":
            raise RuntimeError(str(event.data.get("message") or "agent error"))

    if final_answer:
        db.add(Message(conversation_id=conv.id, role="assistant", content=final_answer))
        db.commit()

    return {
        "final_answer": final_answer or "(empty)",
        "agent_run_id": run_id,
        "conversation_id": conv.id,
        "mock": False,
    }
