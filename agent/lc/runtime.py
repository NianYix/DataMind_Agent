from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from typing import Any

from sqlalchemy.orm import Session

from agent import cancel as cancel_registry
from agent.events import AgentEvent, error_event, final_event, step_event
from agent.lc.graph import build_analysis_graph
from agent.state import AgentState
from server.core.config import get_settings
from server.models import AgentRun

logger = logging.getLogger("datamind.lc")


class LangGraphAgentRuntime:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.graph = build_analysis_graph()

    def run_stream(self, state: AgentState) -> Iterator[AgentEvent]:
        cancel_registry.register(state.run_id)
        emitter: list[AgentEvent] = []
        started = time.perf_counter()

        run = self.db.get(AgentRun, state.run_id)
        if not run:
            run = AgentRun(
                id=state.run_id,
                conversation_id=state.conversation_id,
                question=state.question,
                status="running",
                model=self.settings.llm_model,
            )
            self.db.add(run)
            self.db.commit()

        initial: dict[str, Any] = {
            "run_id": state.run_id,
            "conversation_id": state.conversation_id,
            "question": state.question,
            "dataset_id": state.dataset_id,
            "dataset_path": state.dataset_path,
            "source_type": state.source_type,
            "table_name": state.table_name,
            "connection_id": getattr(state, "connection_id", None),
            "workspace_id": getattr(state, "workspace_id", None),
            "schema_info": state.schema_info,
            "profile_summary": state.profile_summary,
            "memory": state.memory,
            "plan": [],
            "observations": [],
            "messages": [],
            "step_count": 0,
            "input_tokens": state.input_tokens,
            "output_tokens": state.output_tokens,
            "used_non_python_tool": False,
            "status": "running",
            "started_at": time.time(),
            "handoffs": [],
            "blackboard": {},
            "agents_involved": [],
            "last_agent": None,
            "critic_result": None,
            "datasets": list(getattr(state, "datasets", None) or []),
        }

        config = {
            "configurable": {
                "db": self.db,
                "emitter": emitter,
            },
            "recursion_limit": max(50, self.settings.max_agent_steps * 4),
        }

        final_state: dict[str, Any] = dict(initial)
        try:
            for update in self.graph.stream(initial, config=config, stream_mode="updates"):
                # update is {node_name: partial_state}
                for _node, partial in (update or {}).items():
                    if isinstance(partial, dict):
                        final_state.update(partial)
                while emitter:
                    yield emitter.pop(0)
                if final_state.get("status") == "cancelled":
                    break
        except Exception as exc:  # noqa: BLE001
            logger.exception("LangGraph run failed run_id=%s", state.run_id)
            self._persist(state.run_id, final_state, status="error", error=str(exc), started=started)
            yield error_event(str(exc))
            return
        finally:
            cancel_registry.clear(state.run_id)

        # flush remaining events
        while emitter:
            yield emitter.pop(0)

        status = final_state.get("status") or "done"
        if status == "cancelled":
            self._persist(state.run_id, final_state, status="cancelled", started=started)
            yield final_event(final_state.get("final_answer") or "分析已取消", run_id=state.run_id)
            return

        self._persist(state.run_id, final_state, status="done", started=started)
        answer = final_state.get("final_answer") or ""
        yield final_event(answer, report_id=final_state.get("report_id"), run_id=state.run_id)
        cost = self.settings.estimate_cost(
            int(final_state.get("input_tokens") or 0),
            int(final_state.get("output_tokens") or 0),
        )
        yield step_event(
            "metrics",
            "Run metrics",
            input_tokens=int(final_state.get("input_tokens") or 0),
            output_tokens=int(final_state.get("output_tokens") or 0),
            latency_ms=int((time.perf_counter() - started) * 1000),
            estimated_cost=cost,
            engine="langchain",
        )

    def _persist(
        self,
        run_id: str,
        final_state: dict[str, Any],
        *,
        status: str,
        started: float,
        error: str | None = None,
    ) -> None:
        run = self.db.get(AgentRun, run_id)
        if not run:
            return
        run.status = status
        run.input_tokens = int(final_state.get("input_tokens") or 0)
        run.output_tokens = int(final_state.get("output_tokens") or 0)
        run.final_answer = final_state.get("final_answer")
        run.estimated_cost = self.settings.estimate_cost(run.input_tokens, run.output_tokens)
        run.latency_ms = int((time.perf_counter() - started) * 1000)
        run.error = error
        run.model = self.settings.llm_model
        from agent.lc.collaboration import collaboration_snapshot

        run.state_json = {
            "engine": "langchain",
            "plan": final_state.get("plan"),
            "observations": final_state.get("observations"),
            "used_non_python_tool": final_state.get("used_non_python_tool"),
            "multi_agent": collaboration_snapshot(final_state, self.settings),
        }
        self.db.commit()
