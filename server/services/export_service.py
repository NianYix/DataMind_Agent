from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from server.models import AgentRun, AgentStep, Chart, Evidence, Report, ToolCall
from server.services.chat_service import get_run


def export_run_bundle(db: Session, run_id: str) -> dict[str, Any]:
    run = get_run(db, run_id)
    steps = db.query(AgentStep).filter(AgentStep.run_id == run_id).order_by(AgentStep.seq.asc()).all()
    tools = db.query(ToolCall).filter(ToolCall.run_id == run_id).order_by(ToolCall.created_at.asc()).all()
    evidences = db.query(Evidence).filter(Evidence.run_id == run_id).order_by(Evidence.created_at.asc()).all()
    charts = db.query(Chart).filter(Chart.run_id == run_id).order_by(Chart.created_at.asc()).all()
    report = db.query(Report).filter(Report.run_id == run_id).order_by(Report.created_at.desc()).first()

    return {
        "run": {
            "id": run.id,
            "conversation_id": run.conversation_id,
            "question": run.question,
            "status": run.status,
            "model": run.model,
            "input_tokens": run.input_tokens,
            "output_tokens": run.output_tokens,
            "latency_ms": run.latency_ms,
            "estimated_cost": run.estimated_cost,
            "final_answer": run.final_answer,
            "error": run.error,
        },
        "steps": [
            {
                "seq": s.seq,
                "agent_name": s.agent_name,
                "input_summary": s.input_summary,
                "output_summary": s.output_summary,
                "status": s.status,
                "latency_ms": s.latency_ms,
            }
            for s in steps
        ],
        "tool_calls": [
            {
                "id": t.id,
                "tool_name": t.tool_name,
                "arguments": t.arguments,
                "result": t.result,
                "success": t.success,
                "error": t.error,
                "duration_ms": t.duration_ms,
            }
            for t in tools
        ],
        "evidences": [
            {
                "id": e.id,
                "claim": e.claim,
                "tool_call_id": e.tool_call_id,
                "payload_json": e.payload_json,
            }
            for e in evidences
        ],
        "charts": [
            {"id": c.id, "chart_type": c.chart_type, "title": c.title, "option_json": c.option_json}
            for c in charts
        ],
        "report": report.markdown if report else None,
    }


def list_audit_events(db: Session, limit: int = 100) -> list:
    from server.models import AuditEvent

    return (
        db.query(AuditEvent)
        .order_by(AuditEvent.created_at.desc())
        .limit(limit)
        .all()
    )
