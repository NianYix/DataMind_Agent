from __future__ import annotations

import re
from typing import Any


def _norm(text: str) -> str:
    return (text or "").lower()


def mention_hits(answer: str, must_mention: list[str]) -> tuple[float, list[str]]:
    text = _norm(answer)
    missing: list[str] = []
    hit = 0
    for m in must_mention or []:
        token = _norm(str(m))
        if token and token in text:
            hit += 1
        else:
            missing.append(str(m))
    total = len(must_mention or [])
    score = 1.0 if total == 0 else hit / total
    return score, missing


def extract_numbers(text: str) -> list[float]:
    found = re.findall(r"-?\d+(?:\.\d+)?", text or "")
    out: list[float] = []
    for x in found:
        try:
            out.append(float(x))
        except ValueError:
            continue
    return out


def number_hits(answer: str, tool_blob: str, numbers: list[dict[str, Any]]) -> float:
    if not numbers:
        return 1.0
    hay = f"{answer}\n{tool_blob}"
    vals = extract_numbers(hay)
    ok = 0
    for spec in numbers:
        target = float(spec.get("value"))
        tol = float(spec.get("tolerance") or 0)
        if any(abs(v - target) <= tol for v in vals):
            ok += 1
    return ok / len(numbers)


def hallucination_rate(answer: str, tool_blob: str) -> float:
    """Heuristic: fraction of numbers in answer not found in tool outputs."""
    ans_nums = extract_numbers(answer)
    if not ans_nums:
        return 0.0
    tool_nums = extract_numbers(tool_blob)
    missing = 0
    for n in ans_nums:
        if not any(abs(n - t) < 1e-6 or abs(n - t) / max(abs(t), 1e-9) < 0.01 for t in tool_nums):
            # also allow string presence
            if f"{n:g}" not in (tool_blob or "") and str(int(n)) not in (tool_blob or ""):
                missing += 1
    return missing / len(ans_nums)


def score_case(
    *,
    final_answer: str,
    expect: dict[str, Any],
    tool_stats: dict[str, Any],
    tool_blob: str = "",
    steps: int = 0,
) -> dict[str, Any]:
    must = list(expect.get("must_mention") or [])
    insight_score, missing = mention_hits(final_answer, must)
    calc_score = number_hits(final_answer, tool_blob, list(expect.get("numbers") or []))
    task_success = 1.0 if insight_score >= 1.0 and calc_score >= 1.0 else 0.0
    # soften: if no numbers required, only mentions
    if not expect.get("numbers"):
        task_success = 1.0 if insight_score >= 1.0 else 0.0

    max_steps = expect.get("max_steps")
    over_steps = bool(max_steps and steps > int(max_steps))
    if over_steps:
        task_success = 0.0

    total_tools = int(tool_stats.get("total") or 0)
    success_tools = int(tool_stats.get("success") or 0)
    py_total = int(tool_stats.get("python_total") or 0)
    py_ok = int(tool_stats.get("python_success") or 0)
    sql_total = int(tool_stats.get("sql_total") or 0)
    sql_ok = int(tool_stats.get("sql_success") or 0)

    return {
        "task_success": task_success,
        "insight_score": round(insight_score, 4),
        "calculation_score": round(calc_score, 4),
        "hallucination_rate": round(hallucination_rate(final_answer, tool_blob), 4),
        "tool_success_rate": (success_tools / total_tools) if total_tools else None,
        "python_success_rate": (py_ok / py_total) if py_total else None,
        "sql_success_rate": (sql_ok / sql_total) if sql_total else None,
        "missing_mentions": missing,
        "over_steps": over_steps,
        "heuristic": True,
    }


def aggregate_summary(case_scores: list[dict[str, Any]]) -> dict[str, Any]:
    if not case_scores:
        return {
            "task_success_rate": 0.0,
            "tool_success_rate": None,
            "python_success_rate": None,
            "sql_success_rate": None,
            "avg_insight_score": 0.0,
            "avg_calculation_score": 0.0,
            "avg_hallucination_rate": 0.0,
            "avg_steps": 0.0,
            "avg_latency_ms": 0.0,
            "avg_tokens": 0.0,
            "avg_cost": None,
            "cases_total": 0,
            "cases_passed": 0,
            "heuristic": True,
        }

    def avg(key: str) -> float | None:
        vals = [c[key] for c in case_scores if c.get(key) is not None]
        if not vals:
            return None
        return round(sum(vals) / len(vals), 4)

    passed = sum(1 for c in case_scores if c.get("task_success") == 1.0)
    return {
        "task_success_rate": round(passed / len(case_scores), 4),
        "tool_success_rate": avg("tool_success_rate"),
        "python_success_rate": avg("python_success_rate"),
        "sql_success_rate": avg("sql_success_rate"),
        "avg_insight_score": avg("insight_score") or 0.0,
        "avg_calculation_score": avg("calculation_score") or 0.0,
        "avg_hallucination_rate": avg("hallucination_rate") or 0.0,
        "avg_steps": avg("steps") or 0.0,
        "avg_latency_ms": avg("latency_ms") or 0.0,
        "avg_tokens": avg("tokens") or 0.0,
        "avg_cost": avg("cost"),
        "cases_total": len(case_scores),
        "cases_passed": passed,
        "heuristic": True,
    }
