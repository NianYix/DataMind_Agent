from __future__ import annotations

import time
import uuid
from typing import Any

from server.core.config import get_settings


def touch_agent(state: dict[str, Any], agent: str) -> dict[str, Any]:
    agents = list(state.get("agents_involved") or [])
    if agent and agent not in agents:
        agents.append(agent)
    return {"agents_involved": agents}


def patch_blackboard(state: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    board = dict(state.get("blackboard") or {})
    for key, value in updates.items():
        if value is None:
            continue
        board[key] = value
    return {"blackboard": board}


def record_handoff(
    state: dict[str, Any],
    *,
    from_agent: str,
    to_agent: str,
    reason: str = "",
    summary: str | None = None,
) -> dict[str, Any]:
    if not get_settings().multi_agent_enabled:
        return {}
    if not from_agent or not to_agent or from_agent == to_agent:
        return touch_agent(state, to_agent)
    handoffs = list(state.get("handoffs") or [])
    handoffs.append(
        {
            "id": str(uuid.uuid4()),
            "from_agent": from_agent,
            "to_agent": to_agent,
            "reason": (reason or f"{from_agent} → {to_agent}")[:500],
            "summary": (summary or "")[:500] or None,
            "at": time.time(),
        }
    )
    out = touch_agent(state, to_agent)
    out["handoffs"] = handoffs
    return out


def enter_role(
    state: dict[str, Any],
    agent: str,
    *,
    reason: str = "",
    summary: str | None = None,
) -> dict[str, Any]:
    """Mark entering an agent role; record handoff from last_agent when multi-agent is on."""
    if not get_settings().multi_agent_enabled:
        return {}
    prev = state.get("last_agent")
    out: dict[str, Any] = {"last_agent": agent}
    out.update(touch_agent(state, agent))
    if prev and prev != agent:
        # merge agents from touch into a temp state for handoff list
        tmp = {**state, "agents_involved": out["agents_involved"], "handoffs": list(state.get("handoffs") or [])}
        hop = record_handoff(tmp, from_agent=str(prev), to_agent=agent, reason=reason, summary=summary)
        if hop.get("handoffs") is not None:
            out["handoffs"] = hop["handoffs"]
        if hop.get("agents_involved") is not None:
            out["agents_involved"] = hop["agents_involved"]
    return out


def collaboration_snapshot(state: dict[str, Any] | None, settings: Any | None = None) -> dict[str, Any]:
    s = settings or get_settings()
    st = state or {}
    return {
        "enabled": bool(getattr(s, "multi_agent_enabled", True)),
        "critic_enabled": bool(getattr(s, "critic_enabled", False)),
        "agents_involved": list(st.get("agents_involved") or []),
        "handoffs": list(st.get("handoffs") or []),
        "blackboard": dict(st.get("blackboard") or {}),
        "critic_result": st.get("critic_result"),
    }


def empty_collaboration(settings: Any | None = None) -> dict[str, Any]:
    return collaboration_snapshot({}, settings)
