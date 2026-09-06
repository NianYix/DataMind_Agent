from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class WorkspaceOut(BaseModel):
    id: str
    name: str
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class DatasetFieldOut(BaseModel):
    id: str
    name: str
    inferred_type: str
    null_ratio: float
    nunique: int
    meta_json: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class DatasetOut(BaseModel):
    id: str
    workspace_id: str
    name: str
    row_count: int
    col_count: int
    profile_json: dict[str, Any] | None = None
    status: str
    source_type: str = "file"
    table_name: str | None = None
    created_at: datetime | None = None
    fields: list[DatasetFieldOut] = []

    model_config = {"from_attributes": True}


class ConversationCreate(BaseModel):
    dataset_id: str
    title: str | None = None


class ConversationOut(BaseModel):
    id: str
    workspace_id: str
    dataset_id: str | None
    title: str
    context_json: dict[str, Any] | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    content: str = Field(min_length=1)


class MessageOut(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class AgentRunOut(BaseModel):
    id: str
    conversation_id: str
    question: str
    status: str
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int | None = None
    error: str | None = None
    final_answer: str | None = None
    estimated_cost: float | None = None
    cancel_requested: bool = False
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class AgentStepOut(BaseModel):
    id: str
    run_id: str
    seq: int
    agent_name: str
    input_summary: str | None = None
    output_summary: str | None = None
    status: str
    latency_ms: int | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class EvidenceOut(BaseModel):
    id: str
    run_id: str
    claim: str
    tool_call_id: str | None = None
    payload_json: dict[str, Any] | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class ChartOut(BaseModel):
    id: str
    run_id: str
    chart_type: str
    title: str
    option_json: dict[str, Any]
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class ReportOut(BaseModel):
    id: str
    run_id: str
    markdown: str
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
