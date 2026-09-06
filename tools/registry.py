from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from data.parser import parse_tabular_file
from sandbox.python_runner import run_python
from sandbox.sql_runner import run_sql as sandbox_run_sql
from tools.anomaly import anomaly_detection
from tools.chart import build_chart_option
from tools.statistics import statistics


@dataclass
class ToolContext:
    dataset_path: str
    source_type: str = "file"
    table_name: str | None = None
    profile: dict[str, Any] | None = None
    run_id: str | None = None
    connection_id: str | None = None
    workspace_id: str | None = None


def dataset_schema(ctx: ToolContext, **_kwargs: Any) -> dict[str, Any]:
    profile = ctx.profile
    if profile and profile.get("fields"):
        return {
            "success": True,
            "fields": [
                {
                    "name": f["name"],
                    "type": f.get("inferred_type") or f.get("type"),
                    "null_ratio": f.get("null_ratio"),
                    "nunique": f.get("nunique"),
                }
                for f in profile["fields"]
            ],
        }
    if ctx.source_type in {"sqlite", "mysql", "postgresql", "mock"} or str(ctx.dataset_path).startswith("remote://"):
        from tools.statistics import _load_df

        df = _load_df(ctx.dataset_path, ctx.source_type, ctx.table_name)
        return {"success": True, "fields": [{"name": c, "type": str(df[c].dtype)} for c in df.columns]}
    df = parse_tabular_file(ctx.dataset_path)
    return {"success": True, "fields": [{"name": c, "type": str(df[c].dtype)} for c in df.columns]}


def dataset_preview(ctx: ToolContext, n: int = 5, **_kwargs: Any) -> dict[str, Any]:
    from tools.statistics import _load_df

    df = _load_df(ctx.dataset_path, ctx.source_type, ctx.table_name)
    records = df.head(int(n)).astype(object).where(df.notna(), None).to_dict(orient="records")
    safe = []
    for row in records:
        safe.append({k: (v if isinstance(v, (str, int, float, bool)) or v is None else str(v)) for k, v in row.items()})
    return {"success": True, "rows": safe, "row_count": int(len(df))}


def python_execute(ctx: ToolContext, code: str, **_kwargs: Any) -> dict[str, Any]:
    path = ctx.dataset_path
    if ctx.source_type in {"sqlite", "mysql", "postgresql", "mock"} or str(path).startswith("remote://"):
        import tempfile
        from pathlib import Path

        from tools.statistics import _load_df

        df = _load_df(ctx.dataset_path, ctx.source_type, ctx.table_name)
        tmp = Path(tempfile.gettempdir()) / f"datamind_remote_{ctx.run_id or 'tmp'}.csv"
        df.to_csv(tmp, index=False)
        path = str(tmp)
    return run_python(code, path, run_id=ctx.run_id)


def run_sql(ctx: ToolContext, sql: str, **_kwargs: Any) -> dict[str, Any]:
    return sandbox_run_sql(
        sql=sql,
        dataset_path=ctx.dataset_path,
        source_type=ctx.source_type,
        table_name=ctx.table_name,
        run_id=ctx.run_id,
        connection_id=ctx.connection_id,
    )


def run_statistics(ctx: ToolContext, **kwargs: Any) -> dict[str, Any]:
    return statistics(
        dataset_path=ctx.dataset_path,
        source_type=ctx.source_type,
        table_name=ctx.table_name,
        column=kwargs.get("column"),
        group_by=kwargs.get("group_by"),
    )


def run_anomaly(ctx: ToolContext, column: str, **_kwargs: Any) -> dict[str, Any]:
    return anomaly_detection(
        dataset_path=ctx.dataset_path,
        column=column,
        source_type=ctx.source_type,
        table_name=ctx.table_name,
    )


def run_chart(ctx: ToolContext, **kwargs: Any) -> dict[str, Any]:
    option = build_chart_option(
        str(kwargs.get("chart_type") or "bar"),
        str(kwargs.get("title") or "Chart"),
        categories=kwargs.get("categories"),
        values=kwargs.get("values"),
    )
    return {
        "success": True,
        "chart_type": kwargs.get("chart_type") or "bar",
        "title": kwargs.get("title") or "Chart",
        "option": option,
    }


def run_http(ctx: ToolContext, **kwargs: Any) -> dict[str, Any]:  # noqa: ARG001
    from tools.http_tools import http_request

    return http_request(
        method=str(kwargs.get("method") or "GET"),
        url=str(kwargs.get("url") or ""),
        headers=kwargs.get("headers"),
        body=kwargs.get("body"),
        timeout=kwargs.get("timeout"),
    )


def run_web_search(ctx: ToolContext, **kwargs: Any) -> dict[str, Any]:  # noqa: ARG001
    from tools.http_tools import web_search

    return web_search(query=str(kwargs.get("query") or ""))


def run_knowledge_search(ctx: ToolContext, **kwargs: Any) -> dict[str, Any]:
    from tools.knowledge_search import knowledge_search

    return knowledge_search(
        query=str(kwargs.get("query") or ""),
        knowledge_base_id=kwargs.get("knowledge_base_id"),
        top_k=kwargs.get("top_k"),
        workspace_id=kwargs.get("workspace_id") or ctx.workspace_id,
    )


TOOL_HANDLERS = {
    "dataset_schema": dataset_schema,
    "dataset_preview": dataset_preview,
    "python_execute": python_execute,
    "sql_query": run_sql,
    "statistics": run_statistics,
    "anomaly_detection": run_anomaly,
    "generate_chart": run_chart,
    "http_request": run_http,
    "web_search": run_web_search,
    "knowledge_search": run_knowledge_search,
}


def run_tool(name: str, args: dict[str, Any] | None, ctx: ToolContext) -> dict[str, Any]:
    if name not in TOOL_HANDLERS:
        return {"success": False, "error": f"Unknown tool: {name}"}
    try:
        return TOOL_HANDLERS[name](ctx, **(args or {}))
    except TypeError as exc:
        return {"success": False, "error": f"Invalid arguments for {name}: {exc}"}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": str(exc)}


def call_tool(name: str, **kwargs: Any) -> dict[str, Any]:
    ctx = ToolContext(
        dataset_path=kwargs.get("dataset_path", ""),
        source_type=kwargs.get("source_type", "file"),
        table_name=kwargs.get("table_name"),
        profile=kwargs.get("profile"),
        connection_id=kwargs.get("connection_id"),
        run_id=kwargs.get("run_id"),
        workspace_id=kwargs.get("workspace_id"),
    )
    return run_tool(name, kwargs, ctx)
