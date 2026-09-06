from __future__ import annotations

from typing import Any

STANDARD_ANALYSIS_GRAPH: dict[str, Any] = {
    "nodes": [
        {
            "id": "s1",
            "type": "start",
            "config": {"question": "为什么 8 月销售下降？", "dataset_id": None},
        },
        {"id": "a1", "type": "analyze", "config": {}},
        {"id": "e1", "type": "end", "config": {"label": "done"}},
    ],
    "edges": [
        {"from": "s1", "to": "a1"},
        {"from": "a1", "to": "e1"},
    ],
}

CONDITION_BRANCH_GRAPH: dict[str, Any] = {
    "nodes": [
        {
            "id": "s1",
            "type": "start",
            "config": {"question": "为什么 8 月销售下降？", "dataset_id": None},
        },
        {"id": "a1", "type": "analyze", "config": {}},
        {
            "id": "c1",
            "type": "condition",
            "config": {"path": "final_answer", "op": "contains", "value": "下降"},
        },
        {"id": "e1", "type": "end", "config": {"label": "matched"}},
        {"id": "e2", "type": "end", "config": {"label": "other"}},
    ],
    "edges": [
        {"from": "s1", "to": "a1"},
        {"from": "a1", "to": "c1"},
        {"from": "c1", "to": "e1", "when": "true"},
        {"from": "c1", "to": "e2", "when": "false"},
    ],
}

BUILTIN_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "standard_analysis",
        "name": "标准销售归因分析",
        "description": "start → analyze → end",
        "graph": STANDARD_ANALYSIS_GRAPH,
    },
    {
        "id": "condition_branch",
        "name": "分析后条件分支",
        "description": "start → analyze → condition → end×2",
        "graph": CONDITION_BRANCH_GRAPH,
    },
]


def get_template(template_id: str) -> dict[str, Any] | None:
    for t in BUILTIN_TEMPLATES:
        if t["id"] == template_id:
            return t
    return None
