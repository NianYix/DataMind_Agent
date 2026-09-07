from __future__ import annotations

import logging
from typing import Any

from sandbox.errors import SandboxErrorCode
from server.core.config import get_settings
from tools.sql_guard import SqlSecurityError, validate_readonly_sql
from tools.sql_query import sql_query

logger = logging.getLogger("datamind.sandbox.sql")


def run_sql(
    *,
    sql: str,
    dataset_path: str,
    source_type: str = "file",
    table_name: str | None = None,
    run_id: str | None = None,
    max_rows: int | None = None,
    connection_id: str | None = None,
    sources: list | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    limit = max_rows or settings.sql_max_rows
    try:
        safe_sql = validate_readonly_sql(sql, max_limit=limit)
    except SqlSecurityError as exc:
        logger.warning("run_id=%s sql rejected: %s", run_id, exc)
        return {
            "success": False,
            "error": str(exc),
            "error_code": SandboxErrorCode.SECURITY.value,
            "rows": [],
            "sql": sql,
            "truncated": False,
        }

    out = sql_query(
        sql=safe_sql,
        dataset_path=dataset_path,
        source_type=source_type,
        table_name=table_name,
        connection_id=connection_id,
        sources=sources,
    )
    if not out.get("success"):
        err = str(out.get("error") or "sql failed")
        code = SandboxErrorCode.TIMEOUT.value if "timeout" in err.lower() else SandboxErrorCode.RUNTIME.value
        out["error_code"] = code
        out["truncated"] = False
        return out

    rows = out.get("rows") or []
    truncated = bool(out.get("row_count", len(rows)) > len(rows)) or len(rows) >= limit
    out["truncated"] = truncated
    out["error_code"] = None
    return out
