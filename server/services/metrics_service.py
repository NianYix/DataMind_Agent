from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from server.models import AgentRun, ToolCall


def collect_metrics(db: Session) -> dict:
    runs_total = db.query(func.count(AgentRun.id)).scalar() or 0
    status_rows = (
        db.query(AgentRun.status, func.count(AgentRun.id)).group_by(AgentRun.status).all()
    )
    runs_by_status = {str(s): int(c) for s, c in status_rows}

    avg_latency = db.query(func.avg(AgentRun.latency_ms)).scalar()
    avg_in = db.query(func.avg(AgentRun.input_tokens)).scalar()
    avg_out = db.query(func.avg(AgentRun.output_tokens)).scalar()

    tool_total = db.query(func.count(ToolCall.id)).scalar() or 0
    tool_ok = db.query(func.count(ToolCall.id)).filter(ToolCall.success.is_(True)).scalar() or 0

    def _rate(name: str) -> float | None:
        total = db.query(func.count(ToolCall.id)).filter(ToolCall.tool_name == name).scalar() or 0
        if not total:
            return None
        ok = (
            db.query(func.count(ToolCall.id))
            .filter(ToolCall.tool_name == name, ToolCall.success.is_(True))
            .scalar()
            or 0
        )
        return round(ok / total, 4)

    return {
        "runs_total": int(runs_total),
        "runs_by_status": runs_by_status,
        "avg_latency_ms": round(float(avg_latency), 2) if avg_latency is not None else None,
        "avg_input_tokens": round(float(avg_in), 2) if avg_in is not None else None,
        "avg_output_tokens": round(float(avg_out), 2) if avg_out is not None else None,
        "tool_success_rate": round(tool_ok / tool_total, 4) if tool_total else None,
        "python_success_rate": _rate("python_execute"),
        "sql_success_rate": _rate("sql_query"),
        "tool_calls_total": int(tool_total),
    }
