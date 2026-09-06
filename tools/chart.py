from __future__ import annotations

from typing import Any


def build_chart_option(
    chart_type: str,
    title: str,
    categories: list[Any] | None = None,
    values: list[Any] | None = None,
    series: list[dict[str, Any]] | None = None,
    x: list[Any] | None = None,
    y: list[Any] | None = None,
) -> dict[str, Any]:
    chart_type = chart_type.lower()
    option: dict[str, Any] = {
        "title": {"text": title, "left": "center"},
        "tooltip": {"trigger": "axis" if chart_type in {"line", "bar"} else "item"},
        "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
    }

    if chart_type == "line":
        option.update(
            {
                "xAxis": {"type": "category", "data": categories or []},
                "yAxis": {"type": "value"},
                "series": series
                or [{"type": "line", "data": values or [], "smooth": True, "name": title}],
            }
        )
    elif chart_type == "bar":
        option.update(
            {
                "xAxis": {"type": "category", "data": categories or []},
                "yAxis": {"type": "value"},
                "series": series or [{"type": "bar", "data": values or [], "name": title}],
            }
        )
    elif chart_type in {"pie", "donut"}:
        data = []
        if categories and values:
            data = [{"name": str(c), "value": v} for c, v in zip(categories, values)]
        option.update(
            {
                "tooltip": {"trigger": "item"},
                "series": [
                    {
                        "type": "pie",
                        "radius": ["40%", "70%"] if chart_type == "donut" else "65%",
                        "data": data,
                    }
                ],
            }
        )
    elif chart_type == "scatter":
        points = list(zip(x or [], y or []))
        option.update(
            {
                "xAxis": {"type": "value"},
                "yAxis": {"type": "value"},
                "series": [{"type": "scatter", "data": points}],
            }
        )
    else:
        option.update(
            {
                "xAxis": {"type": "category", "data": categories or []},
                "yAxis": {"type": "value"},
                "series": [{"type": "bar", "data": values or []}],
            }
        )
    return option
