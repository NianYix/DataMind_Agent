from __future__ import annotations

import json
import re
import uuid
from typing import Any

from agent.prompts import (
    ANALYST_SYSTEM,
    INSIGHT_SYSTEM,
    PLANNER_SYSTEM,
    PYTHON_CODE_SYSTEM,
    REFLECT_SYSTEM,
    REPORT_SYSTEM,
)
from agent.state import InsightItem, PlanStep
from llm.gateway import LLMGateway
from llm.types import ChatMessage


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise
        return json.loads(match.group(0))


def plan_analysis(
    gateway: LLMGateway,
    *,
    question: str,
    profile_summary: str,
    schema: dict[str, Any],
    memory: dict[str, Any],
) -> tuple[str, list[PlanStep], int, int]:
    user = json.dumps(
        {
            "question": question,
            "profile_summary": profile_summary,
            "schema": schema,
            "memory": memory,
        },
        ensure_ascii=False,
    )
    result = gateway.chat(
        [ChatMessage("system", PLANNER_SYSTEM), ChatMessage("user", user)],
        response_format={"type": "json_object"},
    )
    data = _extract_json(result.content)
    steps = [
        PlanStep(id=str(uuid.uuid4()), description=str(s))
        for s in data.get("steps", [])
    ]
    goal = str(data.get("goal") or question)
    return goal, steps, result.usage.input_tokens, result.usage.output_tokens


def generate_python_code(
    gateway: LLMGateway,
    *,
    step_description: str,
    question: str,
    schema: dict[str, Any],
    memory: dict[str, Any],
    prior_observations: list[str],
) -> tuple[str, int, int]:
    user = json.dumps(
        {
            "step": step_description,
            "question": question,
            "schema": schema,
            "memory": memory,
            "prior_observations": prior_observations[-5:],
        },
        ensure_ascii=False,
    )
    result = gateway.chat(
        [ChatMessage("system", PYTHON_CODE_SYSTEM), ChatMessage("user", user)],
        response_format={"type": "json_object"},
    )
    data = _extract_json(result.content)
    code = str(data.get("code") or "").strip()
    if code.startswith("```"):
        code = re.sub(r"^```(?:python)?\n?", "", code)
        code = re.sub(r"\n?```$", "", code)
    return code, result.usage.input_tokens, result.usage.output_tokens


def reflect_python_code(
    gateway: LLMGateway,
    *,
    code: str,
    error: str,
    schema: dict[str, Any],
) -> tuple[str, int, int]:
    user = json.dumps({"code": code, "error": error, "schema": schema}, ensure_ascii=False)
    result = gateway.chat(
        [ChatMessage("system", REFLECT_SYSTEM), ChatMessage("user", user)],
        response_format={"type": "json_object"},
    )
    data = _extract_json(result.content)
    return str(data.get("code") or "").strip(), result.usage.input_tokens, result.usage.output_tokens


def analyze_result(
    gateway: LLMGateway,
    *,
    question: str,
    step_description: str,
    tool_result: Any,
    memory: dict[str, Any],
) -> tuple[dict[str, Any], int, int]:
    user = json.dumps(
        {
            "question": question,
            "step": step_description,
            "tool_result": tool_result,
            "memory": memory,
        },
        ensure_ascii=False,
        default=str,
    )
    result = gateway.chat(
        [ChatMessage("system", ANALYST_SYSTEM), ChatMessage("user", user)],
        response_format={"type": "json_object"},
    )
    return _extract_json(result.content), result.usage.input_tokens, result.usage.output_tokens


def build_insights(
    gateway: LLMGateway,
    *,
    question: str,
    observations: list[str],
) -> tuple[list[InsightItem], str, int, int]:
    user = json.dumps({"question": question, "observations": observations}, ensure_ascii=False)
    result = gateway.chat(
        [ChatMessage("system", INSIGHT_SYSTEM), ChatMessage("user", user)],
        response_format={"type": "json_object"},
    )
    data = _extract_json(result.content)
    insights = [InsightItem(**item) for item in data.get("insights", [])]
    final_answer = str(data.get("final_answer") or "")
    return insights, final_answer, result.usage.input_tokens, result.usage.output_tokens


def build_report(
    gateway: LLMGateway,
    *,
    question: str,
    observations: list[str],
    insights: list[InsightItem],
    evidences: list[dict[str, Any]],
) -> tuple[str, int, int]:
    user = json.dumps(
        {
            "question": question,
            "observations": observations,
            "insights": [i.model_dump() for i in insights],
            "evidences": evidences,
        },
        ensure_ascii=False,
    )
    result = gateway.chat(
        [ChatMessage("system", REPORT_SYSTEM), ChatMessage("user", user)],
        response_format={"type": "json_object"},
    )
    data = _extract_json(result.content)
    return str(data.get("markdown") or ""), result.usage.input_tokens, result.usage.output_tokens
