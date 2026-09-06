from __future__ import annotations

import json
import uuid
from collections.abc import Iterator

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sse_starlette.sse import ServerSentEvent

from agent import cancel as cancel_registry
from agent.facade import create_runtime
from agent.memory import refresh_conversation_memory
from agent.state import AgentState
from llm.gateway import get_llm_gateway
from server.models import (
    AgentRun,
    AgentStep,
    Chart,
    Conversation,
    Evidence,
    Message,
    Report,
)
from server.services.dataset_service import get_dataset
from server.services.report_export import markdown_to_pdf
from tools.statistics import _load_df


def create_conversation(db: Session, workspace_id: str, dataset_id: str, title: str | None = None) -> Conversation:
    ds = get_dataset(db, dataset_id)
    if ds.workspace_id != workspace_id:
        raise HTTPException(status_code=400, detail="Dataset not in workspace")
    conv = Conversation(
        workspace_id=workspace_id,
        dataset_id=dataset_id,
        title=title or f"分析 · {ds.name}",
        context_json={"dataset_id": dataset_id, "filters": {}},
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def list_conversations(db: Session, workspace_id: str) -> list[Conversation]:
    return (
        db.query(Conversation)
        .filter(Conversation.workspace_id == workspace_id)
        .order_by(Conversation.created_at.desc())
        .all()
    )


def list_messages(db: Session, conversation_id: str) -> list[Message]:
    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )


def stream_analysis(db: Session, conversation_id: str, content: str) -> Iterator[ServerSentEvent]:
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if not conv.dataset_id:
        raise HTTPException(status_code=400, detail="Conversation has no dataset. Bind a dataset first.")

    user_msg = Message(conversation_id=conversation_id, role="user", content=content)
    db.add(user_msg)
    db.commit()

    context = dict(conv.context_json or {"dataset_id": conv.dataset_id, "filters": {}})
    gateway = get_llm_gateway()
    context, mem_in, mem_out = refresh_conversation_memory(gateway, context, content)
    conv.context_json = context
    db.commit()

    ds = get_dataset(db, conv.dataset_id)
    profile = ds.profile_json or {}
    run_id = str(uuid.uuid4())

    state = AgentState(
        run_id=run_id,
        conversation_id=conversation_id,
        question=content,
        dataset_id=ds.id,
        dataset_path=ds.file_path,
        source_type=getattr(ds, "source_type", None) or "file",
        table_name=getattr(ds, "table_name", None),
        connection_id=getattr(ds, "connection_id", None),
        workspace_id=conv.workspace_id,
        schema_info=profile if profile.get("fields") else {},
        profile_summary=str(profile.get("summary_text") or ""),
        memory=context.get("filters") or {},
        input_tokens=mem_in,
        output_tokens=mem_out,
    )

    runtime = create_runtime(db)
    final_answer = ""
    try:
        for event in runtime.run_stream(state):
            if event.event == "final":
                final_answer = event.data.get("answer") or ""
            yield ServerSentEvent(event=event.event, data=json.dumps(event.data, ensure_ascii=False, default=str))
    except Exception as exc:  # noqa: BLE001
        yield ServerSentEvent(event="error", data=json.dumps({"message": str(exc)}, ensure_ascii=False))
        return

    if final_answer:
        db.add(Message(conversation_id=conversation_id, role="assistant", content=final_answer))
        db.commit()


def preview_dataset(db: Session, dataset_id: str, n: int = 20) -> dict:
    ds = get_dataset(db, dataset_id)
    source_type = getattr(ds, "source_type", None) or "file"
    df = _load_df(ds.file_path, source_type, getattr(ds, "table_name", None))
    rows = df.head(n).astype(object).where(df.notna(), None).to_dict(orient="records")
    safe = []
    for row in rows:
        safe.append({k: (v if isinstance(v, (str, int, float, bool)) or v is None else str(v)) for k, v in row.items()})
    return {"rows": safe, "row_count": int(len(df)), "columns": list(df.columns)}


def get_run(db: Session, run_id: str) -> AgentRun:
    run = db.get(AgentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


def cancel_run(db: Session, run_id: str) -> AgentRun:
    run = get_run(db, run_id)
    run.cancel_requested = True
    if run.status == "running":
        # cooperative cancel; runtime will flip status
        pass
    db.commit()
    cancel_registry.request_cancel(run_id)
    db.refresh(run)
    return run


def list_runs_for_workspace(db: Session, workspace_id: str) -> list[AgentRun]:
    conv_ids = [c.id for c in db.query(Conversation).filter(Conversation.workspace_id == workspace_id).all()]
    if not conv_ids:
        return []
    return (
        db.query(AgentRun)
        .filter(AgentRun.conversation_id.in_(conv_ids))
        .order_by(AgentRun.created_at.desc())
        .limit(50)
        .all()
    )


def list_runs_for_conversation(db: Session, conversation_id: str) -> list[AgentRun]:
    return (
        db.query(AgentRun)
        .filter(AgentRun.conversation_id == conversation_id)
        .order_by(AgentRun.created_at.desc())
        .all()
    )


def get_trace(db: Session, run_id: str) -> list[AgentStep]:
    get_run(db, run_id)
    return db.query(AgentStep).filter(AgentStep.run_id == run_id).order_by(AgentStep.seq.asc()).all()


def get_evidence(db: Session, evidence_id: str) -> Evidence:
    ev = db.get(Evidence, evidence_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return ev


def list_evidences(db: Session, run_id: str) -> list[Evidence]:
    get_run(db, run_id)
    return db.query(Evidence).filter(Evidence.run_id == run_id).order_by(Evidence.created_at.asc()).all()


def get_report_for_run(db: Session, run_id: str) -> Report:
    report = db.query(Report).filter(Report.run_id == run_id).order_by(Report.created_at.desc()).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


def get_report_pdf(db: Session, run_id: str) -> bytes:
    report = get_report_for_run(db, run_id)
    return markdown_to_pdf(report.markdown)


def get_charts_for_run(db: Session, run_id: str) -> list[Chart]:
    return db.query(Chart).filter(Chart.run_id == run_id).order_by(Chart.created_at.asc()).all()
