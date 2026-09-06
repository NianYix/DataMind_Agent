from __future__ import annotations

import json
import re
import time
import uuid
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from agent import cancel as cancel_registry
from agent.events import chart_event, observation_event, step_event
from agent.lc.llm import get_chat_model
from agent.lc.state import GraphState
from agent.lc.tools import build_tools
from agent.prompts import (
    ANALYST_SYSTEM,
    INSIGHT_SYSTEM,
    PLANNER_SYSTEM,
    REPORT_SYSTEM,
    SUPERVISOR_SYSTEM,
    TOOL_PICKER_SYSTEM,
    with_mcp_catalog,
)
from server.core.config import get_settings
from server.models import AgentStep, Chart, Evidence, Insight, Report, ToolCall
from tools.chart import build_chart_option
from tools.registry import ToolContext, run_tool


class PlanOut(BaseModel):
    goal: str
    steps: list[str]


class SupervisorOut(BaseModel):
    action: str = Field(description="call_tool|insight|finish")
    reason: str = ""
    preferred_tool: str | None = None


class ObserveOut(BaseModel):
    summary: str
    claim: str = ""
    needs_drill: bool = False
    drill_hint: str | None = None
    is_complete: bool = False
    chart_hint: dict[str, Any] | None = None


class InsightOut(BaseModel):
    insights: list[dict[str, str]] = Field(default_factory=list)
    final_answer: str = ""


class ReportOut(BaseModel):
    markdown: str


def _cfg(config: RunnableConfig) -> dict[str, Any]:
    return (config or {}).get("configurable") or {}


def _emit(config: RunnableConfig, event) -> None:
    emitter = _cfg(config).get("emitter")
    if emitter is not None:
        emitter.append(event)


def _db(config: RunnableConfig) -> Session:
    return _cfg(config)["db"]


def _ctx(state: GraphState) -> ToolContext:
    return ToolContext(
        dataset_path=state["dataset_path"],
        source_type=state.get("source_type") or "file",
        table_name=state.get("table_name"),
        profile=state.get("schema_info") if (state.get("schema_info") or {}).get("fields") else None,
        run_id=state.get("run_id"),
        connection_id=state.get("connection_id"),
        workspace_id=state.get("workspace_id"),
    )


def _usage(msg) -> tuple[int, int]:
    meta = getattr(msg, "usage_metadata", None) or {}
    if meta:
        return int(meta.get("input_tokens") or 0), int(meta.get("output_tokens") or 0)
    resp = getattr(msg, "response_metadata", None) or {}
    usage = resp.get("token_usage") or resp.get("usage") or {}
    return int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0), int(
        usage.get("completion_tokens") or usage.get("output_tokens") or 0
    )


def _add_step(db: Session, run_id: str, agent_name: str, inp: str, out: str) -> None:
    seq = len(db.query(AgentStep).filter(AgentStep.run_id == run_id).all()) + 1
    db.add(
        AgentStep(
            run_id=run_id,
            seq=seq,
            agent_name=agent_name,
            input_summary=str(inp)[:2000],
            output_summary=str(out)[:4000],
            status="ok",
        )
    )
    db.commit()


def _extract_json(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise
        return json.loads(match.group(0))


def understand_node(state: GraphState, config: RunnableConfig) -> dict[str, Any]:
    _emit(config, step_event("understand", "Loading dataset schema and profile"))
    result = run_tool("dataset_schema", {}, _ctx(state))
    schema = result if result.get("fields") else state.get("schema_info") or {}
    _add_step(_db(config), state["run_id"], "Understand", state["question"], "Schema loaded")
    return {"schema_info": schema, "status": "running"}


def plan_node(state: GraphState, config: RunnableConfig) -> dict[str, Any]:
    from server.services.prompt_service import resolve_planner_system

    _emit(config, step_event("planner", "Generating analysis plan"))
    model = get_chat_model()
    planner_sys = resolve_planner_system(_db(config))
    payload = {
        "question": state["question"],
        "profile_summary": state.get("profile_summary"),
        "schema": state.get("schema_info"),
        "memory": state.get("memory") or {},
    }
    try:
        structured = model.with_structured_output(PlanOut)
        plan_out: PlanOut = structured.invoke(
            [SystemMessage(content=planner_sys), HumanMessage(content=json.dumps(payload, ensure_ascii=False))]
        )
        in_tok = out_tok = 0
        goal, steps_raw = plan_out.goal, plan_out.steps
    except Exception:  # noqa: BLE001
        msg = model.invoke(
            [
                SystemMessage(content=planner_sys + "\nReturn STRICT JSON only."),
                HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
            ]
        )
        in_tok, out_tok = _usage(msg)
        data = _extract_json(str(msg.content))
        goal = str(data.get("goal") or state["question"])
        steps_raw = list(data.get("steps") or [])

    steps = [
        {"id": str(uuid.uuid4()), "description": str(s), "status": "pending"}
        for s in steps_raw
    ]
    _add_step(
        _db(config),
        state["run_id"],
        "Planner",
        goal,
        f"{len(steps)} steps: " + "; ".join(s["description"] for s in steps[:6]),
    )
    _emit(config, step_event("plan", "Plan ready", steps=steps, goal=goal))
    return {
        "plan": steps,
        "input_tokens": int(state.get("input_tokens") or 0) + in_tok,
        "output_tokens": int(state.get("output_tokens") or 0) + out_tok,
        "messages": [],
    }


def supervisor_node(state: GraphState, config: RunnableConfig) -> dict[str, Any]:
    settings = get_settings()
    run_id = state["run_id"]
    if cancel_registry.is_cancelled(run_id):
        _emit(config, step_event("cancelled", "Run cancelled by user"))
        return {"status": "cancelled", "next_action": "end"}

    started = float(state.get("started_at") or time.time())
    if time.time() - started > settings.run_timeout_sec:
        _emit(config, step_event("timeout", "Run timeout reached"))
        return {"status": "error", "error": "RUN_TIMEOUT", "next_action": "insight"}

    if int(state.get("step_count") or 0) >= settings.max_agent_steps:
        return {"next_action": "insight", "error": "MAX_STEPS"}

    pending = [s for s in (state.get("plan") or []) if s.get("status") == "pending"]
    if not pending and (state.get("observations") or []):
        return {"next_action": "insight", "preferred_tool": None}

    model = get_chat_model()
    payload = {
        "question": state["question"],
        "memory": state.get("memory") or {},
        "pending_steps": [s["description"] for s in pending[:5]],
        "observations": [o.get("summary") for o in (state.get("observations") or [])[-5:]],
        "step_count": state.get("step_count") or 0,
        "used_non_python_tool": state.get("used_non_python_tool"),
    }
    try:
        out: SupervisorOut = model.with_structured_output(SupervisorOut).invoke(
            [SystemMessage(content=with_mcp_catalog(SUPERVISOR_SYSTEM)), HumanMessage(content=json.dumps(payload, ensure_ascii=False))]
        )
        in_tok = out_tok = 0
        action, reason, preferred = out.action, out.reason, out.preferred_tool
    except Exception:  # noqa: BLE001
        msg = model.invoke(
            [
                SystemMessage(content=with_mcp_catalog(SUPERVISOR_SYSTEM) + "\nReturn STRICT JSON."),
                HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
            ]
        )
        in_tok, out_tok = _usage(msg)
        data = _extract_json(str(msg.content))
        action = str(data.get("action") or "call_tool")
        reason = str(data.get("reason") or "")
        preferred = data.get("preferred_tool")

    if action not in {"call_tool", "insight", "finish"}:
        action = "call_tool"
    if not state.get("used_non_python_tool") and not preferred and pending:
        preferred = "sql_query"
    if action == "finish":
        action = "insight"

    _emit(config, step_event("supervisor", reason or f"action={action}", action=action, preferred_tool=preferred))
    _add_step(_db(config), run_id, "Supervisor", state["question"], f"{action}: {reason}")
    return {
        "next_action": action,
        "preferred_tool": preferred,
        "input_tokens": int(state.get("input_tokens") or 0) + in_tok,
        "output_tokens": int(state.get("output_tokens") or 0) + out_tok,
    }


def agent_tools_node(state: GraphState, config: RunnableConfig) -> dict[str, Any]:
    """Select one tool via LangChain bind_tools and execute it."""
    plan = list(state.get("plan") or [])
    pending = next((s for s in plan if s.get("status") == "pending"), None)
    if not pending:
        return {"next_action": "insight"}

    pending["status"] = "running"
    step_id = pending["id"]
    step_desc = pending["description"]
    _emit(config, step_event("execute", f"Executing: {step_desc}", step_id=step_id))

    ctx = _ctx(state)
    tools = build_tools(ctx)
    model = get_chat_model().bind_tools(tools)
    user_payload = {
        "question": state["question"],
        "step": step_desc,
        "preferred_tool": state.get("preferred_tool"),
        "schema": state.get("schema_info"),
        "memory": state.get("memory") or {},
        "prior_observations": [o.get("summary") for o in (state.get("observations") or [])[-3:]],
        "hint": "Call exactly one tool. SQL table name is data.",
    }
    ai = model.invoke(
        [
            SystemMessage(content=with_mcp_catalog(TOOL_PICKER_SYSTEM)),
            HumanMessage(content=json.dumps(user_payload, ensure_ascii=False)),
        ]
    )
    in_tok, out_tok = _usage(ai)

    tool_name = state.get("preferred_tool") or "python_execute"
    tool_args: dict[str, Any] = {}
    tool_call_id = "manual"

    if getattr(ai, "tool_calls", None):
        tc = ai.tool_calls[0]
        tool_name = tc.get("name") or tool_name
        tool_args = dict(tc.get("args") or {})
        tool_call_id = str(tc.get("id") or "tc")
    else:
        # fallback: ask JSON
        try:
            data = _extract_json(str(ai.content))
            tool_name = str(data.get("tool_name") or tool_name)
            tool_args = data.get("arguments") if isinstance(data.get("arguments"), dict) else {}
        except Exception:  # noqa: BLE001
            tool_args = {}

    if tool_name == "python_execute" and not tool_args.get("code"):
        from agent.llm_ops import generate_python_code
        from llm.gateway import get_llm_gateway

        code, pin, pout = generate_python_code(
            get_llm_gateway(),
            step_description=step_desc,
            question=state["question"],
            schema=state.get("schema_info") or {},
            memory=state.get("memory") or {},
            prior_observations=[o.get("summary") for o in (state.get("observations") or [])],
        )
        in_tok += pin
        out_tok += pout
        tool_args = {"code": code}

    if tool_name == "sql_query" and not tool_args.get("sql"):
        tool_name = "python_execute"
        from agent.llm_ops import generate_python_code
        from llm.gateway import get_llm_gateway

        code, pin, pout = generate_python_code(
            get_llm_gateway(),
            step_description=step_desc,
            question=state["question"],
            schema=state.get("schema_info") or {},
            memory=state.get("memory") or {},
            prior_observations=[o.get("summary") for o in (state.get("observations") or [])],
        )
        in_tok += pin
        out_tok += pout
        tool_args = {"code": code}

    _emit(config, step_event("tool", f"Calling {tool_name}", tool=tool_name, arguments=tool_args))
    t0 = time.perf_counter()
    result = run_tool(tool_name, tool_args, ctx)
    duration = int((time.perf_counter() - t0) * 1000)
    success = bool(result.get("success", True)) and not result.get("error")
    if tool_name == "python_execute":
        success = bool(result.get("success"))

    db = _db(config)
    row = ToolCall(
        run_id=state["run_id"],
        tool_name=tool_name,
        arguments=tool_args,
        result=_preview(result),
        success=success,
        error=result.get("error"),
        duration_ms=duration,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    pending["status"] = "done"
    # update plan list
    for s in plan:
        if s["id"] == step_id:
            s["status"] = "done"

    used_non_python = bool(state.get("used_non_python_tool")) or (success and tool_name != "python_execute")
    payload_result = result.get("result", result)
    if tool_name in {"sql_query", "statistics", "anomaly_detection", "dataset_preview", "dataset_schema"}:
        payload_result = result

    if tool_name == "generate_chart" and result.get("option"):
        chart_id = str(uuid.uuid4())
        db.add(
            Chart(
                id=chart_id,
                run_id=state["run_id"],
                chart_type=str(result.get("chart_type") or "bar"),
                title=str(result.get("title") or "Chart"),
                option_json=result["option"],
            )
        )
        db.commit()
        _emit(config, chart_event(chart_id, str(result.get("title") or "Chart"), result["option"]))

    messages = list(state.get("messages") or [])
    messages.append(ai)
    messages.append(ToolMessage(content=json.dumps(result, ensure_ascii=False, default=str), tool_call_id=tool_call_id))

    return {
        "plan": plan,
        "step_count": int(state.get("step_count") or 0) + 1,
        "current_step_id": step_id,
        "last_tool_name": tool_name,
        "last_tool_result": payload_result if success else None,
        "last_tool_code": tool_args.get("code") or tool_args.get("sql"),
        "last_tool_call_id": row.id,
        "used_non_python_tool": used_non_python,
        "input_tokens": int(state.get("input_tokens") or 0) + in_tok,
        "output_tokens": int(state.get("output_tokens") or 0) + out_tok,
        "messages": messages,
    }


def observe_node(state: GraphState, config: RunnableConfig) -> dict[str, Any]:
    model = get_chat_model()
    pending_desc = ""
    for s in state.get("plan") or []:
        if s.get("id") == state.get("current_step_id"):
            pending_desc = s.get("description") or ""
            break
    payload = {
        "question": state["question"],
        "step": pending_desc,
        "tool_result": state.get("last_tool_result"),
        "memory": state.get("memory") or {},
    }
    try:
        out: ObserveOut = model.with_structured_output(ObserveOut).invoke(
            [SystemMessage(content=ANALYST_SYSTEM), HumanMessage(content=json.dumps(payload, ensure_ascii=False, default=str))]
        )
        in_tok = out_tok = 0
        summary, claim = out.summary, out.claim or out.summary
        needs_drill, drill_hint = out.needs_drill, out.drill_hint
        is_complete, chart_hint = out.is_complete, out.chart_hint
    except Exception:  # noqa: BLE001
        msg = model.invoke(
            [
                SystemMessage(content=ANALYST_SYSTEM + "\nReturn STRICT JSON."),
                HumanMessage(content=json.dumps(payload, ensure_ascii=False, default=str)),
            ]
        )
        in_tok, out_tok = _usage(msg)
        data = _extract_json(str(msg.content))
        summary = str(data.get("summary") or "")
        claim = str(data.get("claim") or summary)
        needs_drill = bool(data.get("needs_drill"))
        drill_hint = data.get("drill_hint")
        is_complete = bool(data.get("is_complete"))
        chart_hint = data.get("chart_hint")

    evidence_id = str(uuid.uuid4())
    db = _db(config)
    db.add(
        Evidence(
            id=evidence_id,
            run_id=state["run_id"],
            claim=claim,
            tool_call_id=state.get("last_tool_call_id"),
            payload_json={
                "code_or_query": state.get("last_tool_code"),
                "result_preview": _preview(state.get("last_tool_result")),
                "tool_name": state.get("last_tool_name"),
            },
        )
    )
    db.commit()

    obs = {
        "step_id": state.get("current_step_id"),
        "summary": summary,
        "evidence_id": evidence_id,
        "needs_drill": needs_drill,
        "drill_hint": drill_hint,
    }
    observations = list(state.get("observations") or [])
    observations.append(obs)
    _emit(config, observation_event(summary, evidence_id=evidence_id, needs_drill=needs_drill))
    _add_step(db, state["run_id"], "Analysis", pending_desc, summary)

    plan = list(state.get("plan") or [])
    if needs_drill and drill_hint and not is_complete:
        exists = any(drill_hint in (s.get("description") or "") for s in plan)
        if not exists:
            plan.append({"id": str(uuid.uuid4()), "description": str(drill_hint), "status": "pending"})
            _emit(config, step_event("replan", f"Drill down: {drill_hint}"))
            _add_step(db, state["run_id"], "RePlan", "needs_drill", str(drill_hint))

    if isinstance(chart_hint, dict) and chart_hint.get("title"):
        option = build_chart_option(
            str(chart_hint.get("chart_type") or "bar"),
            str(chart_hint["title"]),
            categories=chart_hint.get("categories"),
            values=chart_hint.get("values"),
        )
        chart_id = str(uuid.uuid4())
        db.add(
            Chart(
                id=chart_id,
                run_id=state["run_id"],
                chart_type=str(chart_hint.get("chart_type") or "bar"),
                title=str(chart_hint["title"]),
                option_json=option,
            )
        )
        db.commit()
        _emit(config, chart_event(chart_id, str(chart_hint["title"]), option))

    next_action = "insight" if is_complete else "supervisor"
    return {
        "observations": observations,
        "plan": plan,
        "next_action": next_action,
        "input_tokens": int(state.get("input_tokens") or 0) + in_tok,
        "output_tokens": int(state.get("output_tokens") or 0) + out_tok,
    }


def insight_node(state: GraphState, config: RunnableConfig) -> dict[str, Any]:
    _emit(config, step_event("insight", "Extracting business insights"))
    model = get_chat_model()
    payload = {
        "question": state["question"],
        "observations": [o.get("summary") for o in (state.get("observations") or [])],
    }
    try:
        out: InsightOut = model.with_structured_output(InsightOut).invoke(
            [SystemMessage(content=INSIGHT_SYSTEM), HumanMessage(content=json.dumps(payload, ensure_ascii=False))]
        )
        in_tok = out_tok = 0
        insights, final_answer = out.insights, out.final_answer
    except Exception:  # noqa: BLE001
        msg = model.invoke(
            [
                SystemMessage(content=INSIGHT_SYSTEM + "\nReturn STRICT JSON."),
                HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
            ]
        )
        in_tok, out_tok = _usage(msg)
        data = _extract_json(str(msg.content))
        insights = list(data.get("insights") or [])
        final_answer = str(data.get("final_answer") or "")

    if not final_answer and state.get("observations"):
        final_answer = str(state["observations"][-1].get("summary") or "")

    db = _db(config)
    for item in insights:
        db.add(Insight(run_id=state["run_id"], payload_json=item if isinstance(item, dict) else {"text": str(item)}))
    db.commit()
    _add_step(db, state["run_id"], "Insight", state["question"], final_answer)
    return {
        "final_answer": final_answer,
        "input_tokens": int(state.get("input_tokens") or 0) + in_tok,
        "output_tokens": int(state.get("output_tokens") or 0) + out_tok,
    }


def report_node(state: GraphState, config: RunnableConfig) -> dict[str, Any]:
    _emit(config, step_event("report", "Generating markdown report"))
    model = get_chat_model()
    payload = {
        "question": state["question"],
        "observations": [o.get("summary") for o in (state.get("observations") or [])],
        "final_answer": state.get("final_answer"),
    }
    try:
        out: ReportOut = model.with_structured_output(ReportOut).invoke(
            [SystemMessage(content=REPORT_SYSTEM), HumanMessage(content=json.dumps(payload, ensure_ascii=False))]
        )
        in_tok = out_tok = 0
        markdown = out.markdown
    except Exception:  # noqa: BLE001
        msg = model.invoke(
            [
                SystemMessage(content=REPORT_SYSTEM + "\nReturn STRICT JSON."),
                HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
            ]
        )
        in_tok, out_tok = _usage(msg)
        data = _extract_json(str(msg.content))
        markdown = str(data.get("markdown") or state.get("final_answer") or "")

    db = _db(config)
    report = Report(run_id=state["run_id"], markdown=markdown or state.get("final_answer") or "")
    db.add(report)
    db.commit()
    db.refresh(report)
    return {
        "report_markdown": markdown,
        "report_id": report.id,
        "status": "done" if state.get("status") != "cancelled" else "cancelled",
        "input_tokens": int(state.get("input_tokens") or 0) + in_tok,
        "output_tokens": int(state.get("output_tokens") or 0) + out_tok,
    }


def route_supervisor(state: GraphState) -> str:
    action = state.get("next_action") or "call_tool"
    if state.get("status") == "cancelled":
        return "end"
    if action == "call_tool":
        return "tools"
    if action in {"insight", "finish"}:
        return "insight"
    return "insight"


def route_after_observe(state: GraphState) -> str:
    if state.get("next_action") == "insight":
        return "insight"
    return "supervisor"


def _preview(value: Any, limit: int = 40) -> Any:
    if isinstance(value, list) and len(value) > limit:
        return value[:limit]
    if isinstance(value, dict) and len(value) > limit:
        keys = list(value.keys())[:limit]
        return {k: value[k] for k in keys}
    return value
