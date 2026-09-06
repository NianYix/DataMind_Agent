from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from server.core.db import get_db
from server.core.security import require_api_key
from server.schemas import (
    AgentRunOut,
    AgentStepOut,
    ChartOut,
    ConversationCreate,
    ConversationOut,
    EvidenceOut,
    MessageCreate,
    MessageOut,
    ReportOut,
)
from server.services import chat_service, export_service

router = APIRouter(prefix="/api", tags=["analysis"])


@router.post("/workspaces/{workspace_id}/conversations", response_model=ConversationOut)
def create_conversation(workspace_id: str, body: ConversationCreate, db: Session = Depends(get_db)):
    return chat_service.create_conversation(db, workspace_id, body.dataset_id, body.title)


@router.get("/workspaces/{workspace_id}/conversations", response_model=list[ConversationOut])
def list_conversations(workspace_id: str, db: Session = Depends(get_db)):
    return chat_service.list_conversations(db, workspace_id)


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
def get_messages(conversation_id: str, db: Session = Depends(get_db)):
    return chat_service.list_messages(db, conversation_id)


@router.get("/conversations/{conversation_id}/agent-runs", response_model=list[AgentRunOut])
def list_conversation_runs(conversation_id: str, db: Session = Depends(get_db)):
    return chat_service.list_runs_for_conversation(db, conversation_id)


@router.post("/conversations/{conversation_id}/messages")
def post_message(conversation_id: str, body: MessageCreate, db: Session = Depends(get_db)):
    return EventSourceResponse(chat_service.stream_analysis(db, conversation_id, body.content))


@router.get("/datasets/{dataset_id}/preview")
def preview(dataset_id: str, n: int = 20, db: Session = Depends(get_db)):
    return chat_service.preview_dataset(db, dataset_id, n)


@router.get("/agent-runs/{run_id}", response_model=AgentRunOut)
def get_run(run_id: str, db: Session = Depends(get_db)):
    return chat_service.get_run(db, run_id)


@router.post("/agent-runs/{run_id}/cancel", response_model=AgentRunOut)
def cancel_run(run_id: str, db: Session = Depends(get_db)):
    return chat_service.cancel_run(db, run_id)


@router.get("/agent-runs/{run_id}/trace", response_model=list[AgentStepOut])
def get_trace(run_id: str, db: Session = Depends(get_db)):
    return chat_service.get_trace(db, run_id)


@router.get("/agent-runs/{run_id}/report", response_model=ReportOut)
def get_report(run_id: str, db: Session = Depends(get_db)):
    return chat_service.get_report_for_run(db, run_id)


@router.get("/agent-runs/{run_id}/report.pdf")
def get_report_pdf(run_id: str, db: Session = Depends(get_db)):
    data = chat_service.get_report_pdf(db, run_id)
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="report-{run_id[:8]}.pdf"'},
    )


@router.get("/agent-runs/{run_id}/charts", response_model=list[ChartOut])
def get_charts(run_id: str, db: Session = Depends(get_db)):
    return chat_service.get_charts_for_run(db, run_id)


@router.get("/agent-runs/{run_id}/evidences", response_model=list[EvidenceOut])
def list_evidences(run_id: str, db: Session = Depends(get_db)):
    return chat_service.list_evidences(db, run_id)


@router.get("/agent-runs/{run_id}/export")
def export_run(run_id: str, db: Session = Depends(get_db), _: None = Depends(require_api_key)):
    return export_service.export_run_bundle(db, run_id)


@router.get("/evidences/{evidence_id}", response_model=EvidenceOut)
def get_evidence(evidence_id: str, db: Session = Depends(get_db)):
    return chat_service.get_evidence(db, evidence_id)
