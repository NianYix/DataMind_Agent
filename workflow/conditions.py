from __future__ import annotations

from typing import Any


def _get_path(context: dict[str, Any], path: str) -> Any:
    cur: Any = context
    for part in (path or "").split("."):
        if not part:
            continue
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def eval_condition(context: dict[str, Any], config: dict[str, Any] | None) -> bool:
    cfg = config or {}
    path = str(cfg.get("path") or "final_answer")
    op = str(cfg.get("op") or "truthy").lower()
    value = cfg.get("value")
    left = _get_path(context, path)

    if op == "truthy":
        return bool(left)
    if op == "eq":
        return str(left) == str(value)
    if op == "contains":
        return str(value) in str(left if left is not None else "")
    raise ValueError(f"unsupported condition op: {op}")
