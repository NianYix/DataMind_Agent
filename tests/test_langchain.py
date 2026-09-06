from __future__ import annotations

from agent.facade import create_runtime
from agent.lc.graph import build_analysis_graph
from agent.lc.tools import build_tools
from server.core.config import get_settings
from tools.registry import ToolContext


def test_agent_engine_default():
    assert get_settings().agent_engine in {"langchain", "legacy"}


def test_build_graph_compiles():
    graph = build_analysis_graph()
    assert graph is not None


def test_build_tools_schema(tmp_path):
    # minimal csv
    p = tmp_path / "t.csv"
    p.write_text("date,sales\n2026-01-01,10\n2026-02-01,12\n", encoding="utf-8")
    ctx = ToolContext(dataset_path=str(p), source_type="file")
    tools = build_tools(ctx)
    names = {t.name for t in tools}
    assert "sql_query" in names
    assert "python_execute" in names
    out = tools[0].invoke({}) if tools[0].name == "dataset_schema" else None
    schema_tool = next(t for t in tools if t.name == "dataset_schema")
    result = schema_tool.invoke({})
    assert "fields" in result or "sales" in result


def test_facade_legacy_import():
    # ensure legacy path importable
    from agent.runtime import AgentRuntime  # noqa: F401

    assert create_runtime  # callable
