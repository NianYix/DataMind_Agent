from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol

from sqlalchemy.orm import Session

from agent.events import AgentEvent
from agent.state import AgentState
from server.core.config import get_settings


class AgentRuntimeProtocol(Protocol):
    def run_stream(self, state: AgentState) -> Iterator[AgentEvent]: ...


def create_runtime(db: Session) -> AgentRuntimeProtocol:
    engine = (get_settings().agent_engine or "langchain").strip().lower()
    if engine == "legacy":
        from agent.runtime import AgentRuntime

        return AgentRuntime(db)
    from agent.lc.runtime import LangGraphAgentRuntime

    return LangGraphAgentRuntime(db)
