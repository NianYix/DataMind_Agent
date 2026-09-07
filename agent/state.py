from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    id: str
    description: str
    status: Literal["pending", "running", "done", "skipped"] = "pending"


class Observation(BaseModel):
    step_id: str
    summary: str
    data: Any = None
    evidence_id: str | None = None
    needs_drill: bool = False
    drill_hint: str | None = None


class ToolResult(BaseModel):
    tool_name: str
    success: bool
    result: Any = None
    error: str | None = None
    code: str | None = None
    tool_call_id: str | None = None


class ChartSpec(BaseModel):
    id: str
    chart_type: str
    title: str
    option: dict[str, Any]


class InsightItem(BaseModel):
    observation: str
    evidence: str
    reason: str
    impact: str
    recommendation: str


class EvidenceItem(BaseModel):
    id: str
    claim: str
    tool_call_id: str | None = None
    code_or_query: str | None = None
    result_preview: Any = None


class AgentState(BaseModel):
    run_id: str
    conversation_id: str
    question: str
    dataset_id: str
    dataset_path: str
    source_type: str = "file"
    table_name: str | None = None
    connection_id: str | None = None
    workspace_id: str | None = None
    schema_info: dict[str, Any] = Field(default_factory=dict)
    profile_summary: str = ""
    memory: dict[str, Any] = Field(default_factory=dict)
    plan: list[PlanStep] = Field(default_factory=list)
    current_step: int = 0
    observations: list[Observation] = Field(default_factory=list)
    tool_results: list[ToolResult] = Field(default_factory=list)
    charts: list[ChartSpec] = Field(default_factory=list)
    insights: list[InsightItem] = Field(default_factory=list)
    evidences: list[EvidenceItem] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    final_answer: str | None = None
    report_markdown: str | None = None
    status: Literal["running", "done", "error", "cancelled"] = "running"
    step_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost: float | None = None
    used_non_python_tool: bool = False
    datasets: list[dict[str, Any]] = Field(default_factory=list)
