from __future__ import annotations

from typing import Any

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "dataset_schema",
            "description": "Get dataset field names and types",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "dataset_preview",
            "description": "Preview first N rows of the dataset",
            "parameters": {
                "type": "object",
                "properties": {"n": {"type": "integer", "description": "Number of rows", "default": 5}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "python_execute",
            "description": "Execute Pandas Python code on dataframe df. Assign main output to variable result.",
            "parameters": {
                "type": "object",
                "properties": {"code": {"type": "string"}},
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sql_query",
            "description": "Run readonly SQL against table `data` (DuckDB). Prefer aggregations with LIMIT.",
            "parameters": {
                "type": "object",
                "properties": {"sql": {"type": "string"}},
                "required": ["sql"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "statistics",
            "description": "Describe statistics for a column, optionally grouped",
            "parameters": {
                "type": "object",
                "properties": {
                    "column": {"type": "string"},
                    "group_by": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "anomaly_detection",
            "description": "Detect numeric outliers with IQR method",
            "parameters": {
                "type": "object",
                "properties": {"column": {"type": "string"}},
                "required": ["column"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_chart",
            "description": "Build an ECharts option for visualization",
            "parameters": {
                "type": "object",
                "properties": {
                    "chart_type": {"type": "string", "enum": ["line", "bar", "pie", "donut", "scatter"]},
                    "title": {"type": "string"},
                    "categories": {"type": "array", "items": {"type": ["string", "number"]}},
                    "values": {"type": "array", "items": {"type": "number"}},
                },
                "required": ["chart_type", "title"],
            },
        },
    },
]
