from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agent.lc.nodes import (
    agent_tools_node,
    critic_node,
    insight_node,
    observe_node,
    plan_node,
    report_node,
    route_after_insight,
    route_after_observe,
    route_supervisor,
    supervisor_node,
    understand_node,
)
from agent.lc.state import GraphState


def build_analysis_graph():
    g = StateGraph(GraphState)
    g.add_node("understand", understand_node)
    g.add_node("plan", plan_node)
    g.add_node("supervisor", supervisor_node)
    g.add_node("tools", agent_tools_node)
    g.add_node("observe", observe_node)
    g.add_node("insight", insight_node)
    g.add_node("critic", critic_node)
    g.add_node("report", report_node)

    g.add_edge(START, "understand")
    g.add_edge("understand", "plan")
    g.add_edge("plan", "supervisor")
    g.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {"tools": "tools", "insight": "insight", "end": END},
    )
    g.add_edge("tools", "observe")
    g.add_conditional_edges(
        "observe",
        route_after_observe,
        {"supervisor": "supervisor", "insight": "insight"},
    )
    g.add_conditional_edges(
        "insight",
        route_after_insight,
        {"critic": "critic", "report": "report"},
    )
    g.add_edge("critic", "report")
    g.add_edge("report", END)
    return g.compile()
