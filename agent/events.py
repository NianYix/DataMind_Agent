from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class AgentEvent:
    event: str
    data: dict[str, Any]

    def sse(self) -> dict[str, str]:
        return {
            "event": self.event,
            "data": json.dumps(self.data, ensure_ascii=False, default=str),
        }


def step_event(agent_name: str, summary: str, **extra: Any) -> AgentEvent:
    return AgentEvent("step", {"type": agent_name, "summary": summary, **extra})


def observation_event(summary: str, evidence_id: str | None = None, **extra: Any) -> AgentEvent:
    return AgentEvent("observation", {"summary": summary, "evidence_id": evidence_id, **extra})


def chart_event(chart_id: str, title: str, option: dict[str, Any]) -> AgentEvent:
    return AgentEvent("chart", {"chart_id": chart_id, "title": title, "option": option})


def final_event(answer: str, report_id: str | None = None, run_id: str | None = None) -> AgentEvent:
    return AgentEvent("final", {"answer": answer, "report_id": report_id, "run_id": run_id})


def error_event(message: str) -> AgentEvent:
    return AgentEvent("error", {"message": message})
