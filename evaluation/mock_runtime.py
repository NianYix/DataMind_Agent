from __future__ import annotations

import time
import uuid
from collections.abc import Iterator
from typing import Any

from agent.events import AgentEvent, final_event, observation_event, step_event
from agent.state import AgentState


class MockRuntime:
    """CI-friendly runtime that fabricates a plausible answer from expect.must_mention."""

    def __init__(self, db=None, expect: dict[str, Any] | None = None) -> None:  # noqa: ANN001
        self.db = db
        self.expect = expect or {}

    def run_stream(self, state: AgentState) -> Iterator[AgentEvent]:
        yield step_event("understand", "mock schema")
        yield step_event("plan", "mock plan", steps=[{"id": "1", "description": "mock"}])
        prefer = list((self.expect.get("prefer_tools") or ["statistics"]))
        tool = prefer[0] if prefer else "statistics"
        yield step_event("tool", f"Calling {tool}", tool=tool)
        mentions = list(self.expect.get("must_mention") or [])
        nums = list(self.expect.get("numbers") or [])
        pieces = ["基于工具结果："] + mentions
        for n in nums:
            pieces.append(str(n.get("value")))
        answer = " ".join(str(p) for p in pieces) + "。销售下降分析完成。"
        yield observation_event(answer, evidence_id=str(uuid.uuid4()))
        time.sleep(0.01)
        yield final_event(answer, run_id=state.run_id)
        yield step_event(
            "metrics",
            "Run metrics",
            input_tokens=100,
            output_tokens=50,
            latency_ms=12,
            estimated_cost=0.0,
            engine="mock",
        )
