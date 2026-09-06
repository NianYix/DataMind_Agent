from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from server.core.config import get_settings
from tools.registry import ToolContext, run_tool


class PreviewInput(BaseModel):
    n: int = Field(default=5, description="Number of preview rows")


class PythonInput(BaseModel):
    code: str = Field(description="Pandas code. df is preloaded. Assign output to result.")


class SqlInput(BaseModel):
    sql: str = Field(description="Readonly SQL against table `data`")


class StatsInput(BaseModel):
    column: str | None = Field(default=None, description="Column name")
    group_by: str | None = Field(default=None, description="Optional group-by column")


class AnomalyInput(BaseModel):
    column: str = Field(description="Numeric column for IQR outlier detection")


class ChartInput(BaseModel):
    chart_type: str = Field(description="line|bar|pie|donut|scatter")
    title: str = Field(description="Chart title")
    categories: list[Any] | None = Field(default=None)
    values: list[float] | None = Field(default=None)


class HttpInput(BaseModel):
    method: str = Field(default="GET", description="GET or POST")
    url: str = Field(description="URL must match configured allowlist prefix")
    headers: dict[str, str] | None = None
    body: str | None = None


class WebSearchInput(BaseModel):
    query: str = Field(description="Search query")


class KnowledgeSearchInput(BaseModel):
    query: str = Field(description="Natural language query for business docs / definitions")
    knowledge_base_id: str | None = Field(default=None, description="Optional knowledge base id")
    top_k: int | None = Field(default=None, description="Number of chunks to return")


def _dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def build_tools(ctx: ToolContext) -> list[StructuredTool]:
    def dataset_schema() -> str:
        return _dumps(run_tool("dataset_schema", {}, ctx))

    def dataset_preview(n: int = 5) -> str:
        return _dumps(run_tool("dataset_preview", {"n": n}, ctx))

    def python_execute(code: str) -> str:
        return _dumps(run_tool("python_execute", {"code": code}, ctx))

    def sql_query(sql: str) -> str:
        return _dumps(run_tool("sql_query", {"sql": sql}, ctx))

    def statistics(column: str | None = None, group_by: str | None = None) -> str:
        return _dumps(run_tool("statistics", {"column": column, "group_by": group_by}, ctx))

    def anomaly_detection(column: str) -> str:
        return _dumps(run_tool("anomaly_detection", {"column": column}, ctx))

    def generate_chart(
        chart_type: str,
        title: str,
        categories: list[Any] | None = None,
        values: list[float] | None = None,
    ) -> str:
        return _dumps(
            run_tool(
                "generate_chart",
                {
                    "chart_type": chart_type,
                    "title": title,
                    "categories": categories,
                    "values": values,
                },
                ctx,
            )
        )

    def http_request(
        method: str = "GET",
        url: str = "",
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> str:
        return _dumps(run_tool("http_request", {"method": method, "url": url, "headers": headers, "body": body}, ctx))

    def web_search(query: str) -> str:
        return _dumps(run_tool("web_search", {"query": query}, ctx))

    def knowledge_search(
        query: str,
        knowledge_base_id: str | None = None,
        top_k: int | None = None,
    ) -> str:
        return _dumps(
            run_tool(
                "knowledge_search",
                {"query": query, "knowledge_base_id": knowledge_base_id, "top_k": top_k},
                ctx,
            )
        )

    tools = [
        StructuredTool.from_function(func=dataset_schema, name="dataset_schema", description="Get dataset field names and types"),
        StructuredTool.from_function(func=dataset_preview, name="dataset_preview", description="Preview first N rows", args_schema=PreviewInput),
        StructuredTool.from_function(func=python_execute, name="python_execute", description="Execute Pandas code on dataframe df", args_schema=PythonInput),
        StructuredTool.from_function(func=sql_query, name="sql_query", description="Run readonly SQL against table data", args_schema=SqlInput),
        StructuredTool.from_function(func=statistics, name="statistics", description="Describe statistics for a column, optionally grouped", args_schema=StatsInput),
        StructuredTool.from_function(func=anomaly_detection, name="anomaly_detection", description="Detect numeric outliers with IQR", args_schema=AnomalyInput),
        StructuredTool.from_function(func=generate_chart, name="generate_chart", description="Build an ECharts option JSON", args_schema=ChartInput),
        StructuredTool.from_function(func=http_request, name="http_request", description="HTTP GET/POST to allowlisted URLs", args_schema=HttpInput),
        StructuredTool.from_function(
            func=knowledge_search,
            name="knowledge_search",
            description="Search Workspace knowledge docs for definitions, metrics口径, policies",
            args_schema=KnowledgeSearchInput,
        ),
    ]
    if get_settings().web_search_enabled:
        tools.append(
            StructuredTool.from_function(func=web_search, name="web_search", description="Web search (stub/provider)", args_schema=WebSearchInput)
        )
    return tools
