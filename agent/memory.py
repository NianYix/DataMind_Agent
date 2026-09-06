from __future__ import annotations

from typing import Any

from agent.supervisor import update_memory
from llm.gateway import LLMGateway


def refresh_conversation_memory(
    gateway: LLMGateway,
    context: dict[str, Any],
    message: str,
) -> tuple[dict[str, Any], int, int]:
    previous_filters = dict((context or {}).get("filters") or {})
    try:
        filters, in_tok, out_tok = update_memory(gateway, previous=previous_filters, message=message)
        new_ctx = dict(context or {})
        new_ctx["filters"] = filters
        return new_ctx, in_tok, out_tok
    except Exception:  # noqa: BLE001
        # heuristic fallback
        filters = dict(previous_filters)
        for r in ["华东", "华北", "华南", "华中", "西南", "西北", "东北"]:
            if r in message:
                filters["region"] = r
        if "全部" in message or "重置" in message:
            if "地区" in message or "region" in message.lower():
                filters.pop("region", None)
        if "商品" in message or "SKU" in message:
            filters["focus"] = "product"
        if "客户" in message:
            filters["focus"] = "customer"
        new_ctx = dict(context or {})
        new_ctx["filters"] = filters
        return new_ctx, 0, 0
