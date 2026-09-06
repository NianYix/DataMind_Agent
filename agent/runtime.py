from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Iterator
from typing import Any

from sqlalchemy.orm import Session

from agent import cancel as cancel_registry
from agent.events import AgentEvent, chart_event, error_event, final_event, observation_event, step_event
from agent.llm_ops import (
    analyze_result,
    build_insights,
    build_report,
    generate_python_code,
    plan_analysis,
    reflect_python_code,
)
from agent.state import AgentState, ChartSpec, EvidenceItem, Observation, PlanStep, ToolResult
from agent.supervisor import decide_next, pick_tool_call
from llm.gateway import get_llm_gateway
from server.core.config import get_settings
from server.models import (
    AgentRun,
    AgentStep,
    Chart,
    Evidence,
    Insight,
    Report,
    ToolCall,
)
from server.services import audit_service
from tools.registry import ToolContext, run_tool

logger = logging.getLogger("datamind.agent")


class AgentRuntime:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.gateway = get_llm_gateway()

    def run_stream(self, state: AgentState) -> Iterator[AgentEvent]:
        cancel_registry.register(state.run_id)
        try:
            yield from self._execute(state)
        except Exception as exc:  # noqa: BLE001
            state.status = "error"
            state.errors.append(str(exc))
            self._persist_run(state)
            audit_service.record(
                self.db,
                event_type="run_end",
                message=f"Run error: {exc}",
                run_id=state.run_id,
                level="error",
            )
            logger.exception("run_id=%s failed", state.run_id)
            yield error_event(str(exc))
        finally:
            cancel_registry.clear(state.run_id)

    def _execute(self, state: AgentState) -> Iterator[AgentEvent]:
        started = time.perf_counter()
        run = self.db.get(AgentRun, state.run_id)
        if not run:
            run = AgentRun(
                id=state.run_id,
                conversation_id=state.conversation_id,
                question=state.question,
                status="running",
                model=self.gateway.model,
            )
            self.db.add(run)
            self.db.commit()

        ctx = ToolContext(
            dataset_path=state.dataset_path,
            source_type=state.source_type,
            table_name=state.table_name,
            profile=state.schema_info if state.schema_info.get("fields") else None,
            run_id=state.run_id,
        )

        audit_service.record(
            self.db,
            event_type="run_start",
            message=f"Run started: {state.question[:200]}",
            run_id=state.run_id,
            payload={"dataset_id": state.dataset_id},
        )

        yield step_event("understand", "Loading dataset schema and profile")
        schema_payload = run_tool("dataset_schema", {}, ctx)
        if schema_payload.get("fields"):
            state.schema_info = schema_payload
            ctx.profile = schema_payload
        self._add_step(state, "Understand", state.question, "Schema loaded")

        yield step_event("planner", "Generating analysis plan")
        t0 = time.perf_counter()
        goal, steps, in_tok, out_tok = plan_analysis(
            self.gateway,
            question=state.question,
            profile_summary=state.profile_summary,
            schema=state.schema_info,
            memory=state.memory,
        )
        state.input_tokens += in_tok
        state.output_tokens += out_tok
        state.plan = steps
        self._add_step(
            state,
            "Planner",
            goal,
            f"{len(steps)} steps: " + "; ".join(s.description for s in steps[:6]),
            latency_ms=int((time.perf_counter() - t0) * 1000),
        )
        yield step_event("plan", "Plan ready", steps=[s.model_dump() for s in steps], goal=goal)

        while state.status == "running":
            if cancel_registry.is_cancelled(state.run_id) or self._db_cancel_requested(state.run_id):
                state.status = "cancelled"
                audit_service.record(
                    self.db,
                    event_type="cancel",
                    message="Run cancelled",
                    run_id=state.run_id,
                    level="warn",
                )
                yield step_event("cancelled", "Run cancelled by user")
                break
            if time.perf_counter() - started > self.settings.run_timeout_sec:
                state.errors.append("Reached RUN_TIMEOUT_SEC")
                yield step_event("timeout", "Run timeout reached")
                break
            if state.step_count >= self.settings.max_agent_steps:
                state.errors.append("Reached MAX_AGENT_STEPS")
                break

            decision, in_tok, out_tok = decide_next(self.gateway, state)
            state.input_tokens += in_tok
            state.output_tokens += out_tok
            yield step_event(
                "supervisor",
                decision.get("reason") or f"action={decision.get('action')}",
                action=decision.get("action"),
                preferred_tool=decision.get("preferred_tool"),
            )
            self._add_step(state, "Supervisor", state.question, str(decision))
            logger.info("run_id=%s supervisor action=%s", state.run_id, decision.get("action"))

            action = decision.get("action")
            if action in {"insight", "finish"}:
                break

            pending = next((s for s in state.plan if s.status == "pending"), None)
            if pending is None and action == "call_tool":
                break
            if pending is None:
                break

            pending.status = "running"
            state.step_count += 1
            yield step_event("execute", f"Executing: {pending.description}", step_id=pending.id)

            tool_events: list[AgentEvent] = []
            tool_name, _tool_args, code_or_query = self._resolve_and_run_tool_impl(
                state, ctx, pending.description, decision.get("preferred_tool"), tool_events
            )
            for ev in tool_events:
                yield ev
            pending.status = "done"

            # Find last tool result payload
            last = state.tool_results[-1] if state.tool_results else None
            tool_payload = {
                "success": bool(last.success) if last else False,
                "result": last.result if last else None,
                "code": code_or_query,
                "tool_call_id": last.tool_call_id if last else None,
                "tool_name": tool_name,
            }

            analysis, in_tok, out_tok = analyze_result(
                self.gateway,
                question=state.question,
                step_description=pending.description,
                tool_result=tool_payload.get("result"),
                memory=state.memory,
            )
            state.input_tokens += in_tok
            state.output_tokens += out_tok

            evidence_id = str(uuid.uuid4())
            evidence = EvidenceItem(
                id=evidence_id,
                claim=str(analysis.get("claim") or analysis.get("summary") or pending.description),
                tool_call_id=tool_payload.get("tool_call_id"),
                code_or_query=code_or_query,
                result_preview=_preview(tool_payload.get("result")),
            )
            state.evidences.append(evidence)
            self.db.add(
                Evidence(
                    id=evidence_id,
                    run_id=state.run_id,
                    claim=evidence.claim,
                    tool_call_id=evidence.tool_call_id,
                    payload_json={
                        "code_or_query": evidence.code_or_query,
                        "result_preview": evidence.result_preview,
                        "tool_name": tool_name,
                    },
                )
            )
            self.db.commit()

            obs = Observation(
                step_id=pending.id,
                summary=str(analysis.get("summary") or ""),
                data=tool_payload.get("result"),
                evidence_id=evidence_id,
                needs_drill=bool(analysis.get("needs_drill")),
                drill_hint=analysis.get("drill_hint"),
            )
            state.observations.append(obs)
            yield observation_event(obs.summary, evidence_id=evidence_id, needs_drill=obs.needs_drill)
            self._add_step(state, "Analysis", pending.description, obs.summary)

            chart_hint = analysis.get("chart_hint")
            if isinstance(chart_hint, dict) and chart_hint.get("title"):
                yield from self._add_chart(state, chart_hint)

            if analysis.get("is_complete"):
                break
            if obs.needs_drill and obs.drill_hint:
                exists = any(obs.drill_hint in s.description for s in state.plan)
                if not exists and state.step_count < self.settings.max_agent_steps - 1:
                    drill = PlanStep(id=str(uuid.uuid4()), description=str(obs.drill_hint))
                    state.plan.append(drill)
                    yield step_event("replan", f"Drill down: {drill.description}", step=drill.model_dump())
                    self._add_step(state, "RePlan", "needs_drill", drill.description)

        if state.status == "cancelled":
            self._persist_run(state, latency_ms=int((time.perf_counter() - started) * 1000))
            audit_service.record(
                self.db,
                event_type="run_end",
                message="Run cancelled end",
                run_id=state.run_id,
                level="warn",
                payload={"status": "cancelled"},
            )
            yield final_event(state.final_answer or "分析已取消", run_id=state.run_id)
            return

        yield step_event("insight", "Extracting business insights")
        insights, final_answer, in_tok, out_tok = build_insights(
            self.gateway,
            question=state.question,
            observations=[o.summary for o in state.observations],
        )
        state.input_tokens += in_tok
        state.output_tokens += out_tok
        state.insights = insights
        state.final_answer = final_answer or (state.observations[-1].summary if state.observations else "")
        for item in insights:
            self.db.add(Insight(run_id=state.run_id, payload_json=item.model_dump()))
        self.db.commit()
        self._add_step(state, "Insight", state.question, state.final_answer or "")

        yield step_event("report", "Generating markdown report")
        markdown, in_tok, out_tok = build_report(
            self.gateway,
            question=state.question,
            observations=[o.summary for o in state.observations],
            insights=insights,
            evidences=[e.model_dump() for e in state.evidences],
        )
        state.input_tokens += in_tok
        state.output_tokens += out_tok
        state.report_markdown = markdown
        report = Report(run_id=state.run_id, markdown=markdown or state.final_answer or "")
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)

        state.status = "done"
        state.estimated_cost = self.settings.estimate_cost(state.input_tokens, state.output_tokens)
        latency_ms = int((time.perf_counter() - started) * 1000)
        self._persist_run(state, latency_ms=latency_ms)
        audit_service.record(
            self.db,
            event_type="run_end",
            message="Run completed",
            run_id=state.run_id,
            payload={
                "status": "done",
                "latency_ms": latency_ms,
                "input_tokens": state.input_tokens,
                "output_tokens": state.output_tokens,
            },
        )
        yield final_event(
            state.final_answer or "",
            report_id=report.id,
            run_id=state.run_id,
        )
        yield step_event(
            "metrics",
            "Run metrics",
            input_tokens=state.input_tokens,
            output_tokens=state.output_tokens,
            latency_ms=latency_ms,
            estimated_cost=state.estimated_cost,
        )

    def _resolve_and_run_tool_impl(
        self,
        state: AgentState,
        ctx: ToolContext,
        step_description: str,
        preferred_tool: str | None,
        events: list[AgentEvent],
    ) -> tuple[str, dict[str, Any], str | None]:
        tc, in_tok, out_tok = pick_tool_call(self.gateway, state, step_description, preferred_tool)
        state.input_tokens += in_tok
        state.output_tokens += out_tok

        tool_name = (tc.name if tc else None) or preferred_tool or "python_execute"
        args = dict(tc.arguments) if tc else {}

        # Ensure python has code
        if tool_name == "python_execute" and not args.get("code"):
            code, in_tok, out_tok = generate_python_code(
                self.gateway,
                step_description=step_description,
                question=state.question,
                schema=state.schema_info,
                memory=state.memory,
                prior_observations=[o.summary for o in state.observations],
            )
            state.input_tokens += in_tok
            state.output_tokens += out_tok
            args["code"] = code

        # Ensure sql has query; fallback to python if missing
        if tool_name == "sql_query" and not args.get("sql"):
            tool_name = "python_execute"
            code, in_tok, out_tok = generate_python_code(
                self.gateway,
                step_description=step_description,
                question=state.question,
                schema=state.schema_info,
                memory=state.memory,
                prior_observations=[o.summary for o in state.observations],
            )
            state.input_tokens += in_tok
            state.output_tokens += out_tok
            args = {"code": code}

        events.append(step_event("tool", f"Calling {tool_name}", tool=tool_name, arguments=_preview(args)))
        result = self._execute_tool_with_retry(state, ctx, tool_name, args, events)
        if tool_name != "python_execute" and result.get("success"):
            state.used_non_python_tool = True

        code_or_query = args.get("code") or args.get("sql")
        return tool_name, args, code_or_query

    def _execute_tool_with_retry(
        self,
        state: AgentState,
        ctx: ToolContext,
        tool_name: str,
        args: dict[str, Any],
        events: list[AgentEvent],
    ) -> dict[str, Any]:
        attempt = 0
        current_args = dict(args)
        last_error = ""
        while attempt <= self.settings.max_tool_retries:
            attempt += 1
            t0 = time.perf_counter()
            result = run_tool(tool_name, current_args, ctx)
            # normalize success flag
            if "success" not in result and tool_name == "python_execute":
                pass
            success = bool(result.get("success", True)) and not result.get("error")
            if tool_name == "python_execute":
                success = bool(result.get("success"))
            duration = int((time.perf_counter() - t0) * 1000)
            logger.info(
                "run_id=%s tool=%s success=%s duration_ms=%s",
                state.run_id,
                tool_name,
                success,
                duration,
            )

            tool_row = ToolCall(
                run_id=state.run_id,
                tool_name=tool_name,
                arguments=current_args,
                result=_preview(result),
                success=success,
                error=result.get("error"),
                duration_ms=duration,
            )
            self.db.add(tool_row)
            self.db.commit()
            self.db.refresh(tool_row)

            payload_result = result.get("result", result)
            if tool_name in {"sql_query", "statistics", "anomaly_detection", "dataset_preview", "dataset_schema"}:
                payload_result = result

            tr = ToolResult(
                tool_name=tool_name,
                success=success,
                result=payload_result if success else None,
                error=result.get("error"),
                code=current_args.get("code") or current_args.get("sql"),
                tool_call_id=tool_row.id,
            )
            state.tool_results.append(tr)

            if success:
                if tool_name == "generate_chart" and result.get("option"):
                    chart_id = str(uuid.uuid4())
                    self.db.add(
                        Chart(
                            id=chart_id,
                            run_id=state.run_id,
                            chart_type=str(result.get("chart_type") or "bar"),
                            title=str(result.get("title") or "Chart"),
                            option_json=result["option"],
                        )
                    )
                    self.db.commit()
                    state.charts.append(
                        ChartSpec(
                            id=chart_id,
                            chart_type=str(result.get("chart_type") or "bar"),
                            title=str(result.get("title") or "Chart"),
                            option=result["option"],
                        )
                    )
                    events.append(chart_event(chart_id, str(result.get("title") or "Chart"), result["option"]))
                return result

            last_error = str(result.get("error") or "tool failed")
            state.errors.append(last_error)
            if result.get("error_code") == "SECURITY":
                audit_service.record(
                    self.db,
                    event_type="sandbox_reject",
                    message=f"{tool_name}: {last_error[:300]}",
                    run_id=state.run_id,
                    level="warn",
                    payload={"tool": tool_name, "error_code": "SECURITY"},
                )
            events.append(step_event("reflection", f"{tool_name} failed: {last_error[:200]}"))
            if tool_name != "python_execute" or attempt > self.settings.max_tool_retries:
                break
            fixed, in_tok, out_tok = reflect_python_code(
                self.gateway,
                code=str(current_args.get("code") or ""),
                error=last_error,
                schema=state.schema_info,
            )
            state.input_tokens += in_tok
            state.output_tokens += out_tok
            current_args["code"] = fixed
            self._add_step(state, "Reflection", last_error[:300], "retry with fixed code")

        return {"success": False, "error": last_error, "result": None}

    def _db_cancel_requested(self, run_id: str) -> bool:
        run = self.db.get(AgentRun, run_id)
        return bool(run and run.cancel_requested)

    def _add_chart(self, state: AgentState, hint: dict[str, Any]) -> Iterator[AgentEvent]:
        from tools.chart import build_chart_option

        chart_type = str(hint.get("chart_type") or "bar")
        title = str(hint.get("title") or "Chart")
        option = build_chart_option(
            chart_type,
            title,
            categories=hint.get("categories"),
            values=hint.get("values"),
        )
        chart_id = str(uuid.uuid4())
        spec = ChartSpec(id=chart_id, chart_type=chart_type, title=title, option=option)
        state.charts.append(spec)
        self.db.add(
            Chart(id=chart_id, run_id=state.run_id, chart_type=chart_type, title=title, option_json=option)
        )
        self.db.commit()
        yield chart_event(chart_id, title, option)

    def _add_step(
        self,
        state: AgentState,
        agent_name: str,
        input_summary: str,
        output_summary: str,
        latency_ms: int | None = None,
    ) -> None:
        seq = len(self.db.query(AgentStep).filter(AgentStep.run_id == state.run_id).all()) + 1
        step = AgentStep(
            run_id=state.run_id,
            seq=seq,
            agent_name=agent_name,
            input_summary=str(input_summary)[:2000],
            output_summary=str(output_summary)[:4000],
            status="ok",
            latency_ms=latency_ms,
        )
        self.db.add(step)
        self.db.commit()

    def _persist_run(self, state: AgentState, latency_ms: int | None = None) -> None:
        run = self.db.get(AgentRun, state.run_id)
        if not run:
            return
        run.status = state.status
        run.input_tokens = state.input_tokens
        run.output_tokens = state.output_tokens
        run.final_answer = state.final_answer
        run.estimated_cost = state.estimated_cost or self.settings.estimate_cost(
            state.input_tokens, state.output_tokens
        )
        run.error = "; ".join(state.errors) if state.errors and state.status == "error" else None
        if latency_ms is not None:
            run.latency_ms = latency_ms
        run.state_json = state.model_dump()
        self.db.commit()


def _preview(value: Any, limit: int = 40) -> Any:
    if isinstance(value, list) and len(value) > limit:
        return value[:limit]
    if isinstance(value, dict) and len(value) > limit:
        keys = list(value.keys())[:limit]
        return {k: value[k] for k in keys}
    return value
