from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class GraphState(TypedDict, total=False):
    run_id: str
    conversation_id: str
    question: str
    dataset_id: str
    dataset_path: str
    source_type: str
    table_name: str | None
    connection_id: str | None
    workspace_id: str | None
    schema_info: dict[str, Any]
    profile_summary: str
    memory: dict[str, Any]
    plan: list[dict[str, Any]]
    observations: list[dict[str, Any]]
    messages: Annotated[list, add_messages]
    step_count: int
    input_tokens: int
    output_tokens: int
    used_non_python_tool: bool
    final_answer: str | None
    report_markdown: str | None
    report_id: str | None
    status: str
    error: str | None
    next_action: str
    preferred_tool: str | None
    current_step_id: str | None
    last_tool_name: str | None
    last_tool_result: Any
    last_tool_code: str | None
    last_tool_call_id: str | None
    started_at: float
    handoffs: list[dict[str, Any]]
    blackboard: dict[str, Any]
    agents_involved: list[str]
    last_agent: str | None
    critic_result: dict[str, Any] | None
    datasets: list[dict[str, Any]]
