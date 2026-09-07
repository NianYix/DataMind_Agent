from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.sql_guard import SqlSecurityError, validate_readonly_sql


def _parse_remote(dataset_path: str) -> tuple[str, str] | None:
    if not dataset_path.startswith("remote://"):
        return None
    rest = dataset_path[len("remote://") :]
    if "/" not in rest:
        return None
    connection_id, table = rest.split("/", 1)
    return connection_id, table


def _register_one(con: Any, *, alias: str, path: Path, source_type: str, table_name: str | None) -> str | None:
    """Register one local source into DuckDB. Returns error string or None."""
    if source_type == "sqlite":
        tbl = table_name or "data"
        attach = f"src_{alias}"
        con.execute(f"ATTACH '{path.as_posix()}' AS {attach} (TYPE SQLITE)")
        con.execute(f"CREATE OR REPLACE VIEW {alias} AS SELECT * FROM {attach}.{tbl}")
        return None
    suffix = path.suffix.lower()
    if suffix == ".csv":
        con.execute(f"CREATE OR REPLACE VIEW {alias} AS SELECT * FROM read_csv_auto('{path.as_posix()}')")
        return None
    if suffix in {".xlsx", ".xls"}:
        import pandas as pd

        df = pd.read_excel(path)
        con.register(alias, df)
        return None
    return f"Unsupported file type for SQL: {suffix}"


def sql_query(
    *,
    sql: str,
    dataset_path: str,
    source_type: str = "file",
    table_name: str | None = None,
    connection_id: str | None = None,
    sources: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    try:
        safe_sql = validate_readonly_sql(sql)
    except SqlSecurityError as exc:
        return {"success": False, "error": str(exc), "rows": [], "sql": sql}

    srcs = list(sources or [])
    if len(srcs) <= 1:
        # single-source / legacy path
        if source_type in {"mysql", "postgresql", "mock"} or dataset_path.startswith("remote://"):
            parsed = _parse_remote(dataset_path)
            cid = connection_id or (parsed[0] if parsed else None)
            if not cid:
                return {
                    "success": False,
                    "error": "Missing connection_id for remote dataset",
                    "rows": [],
                    "sql": safe_sql,
                }
            from server.core.db import SessionLocal
            from server.services.datasource_service import execute_remote_sql

            db = SessionLocal()
            try:
                return execute_remote_sql(db, cid, safe_sql)
            finally:
                db.close()

        try:
            import duckdb
        except ImportError:
            return {"success": False, "error": "duckdb is not installed", "rows": [], "sql": safe_sql}

        path = Path(dataset_path)
        if not path.exists():
            return {"success": False, "error": f"Dataset file not found: {dataset_path}", "rows": [], "sql": safe_sql}

        con = duckdb.connect(database=":memory:")
        try:
            err = _register_one(con, alias="data", path=path, source_type=source_type, table_name=table_name)
            if err:
                return {"success": False, "error": err, "rows": [], "sql": safe_sql}
            result = con.execute(safe_sql).fetchdf()
            records = result.head(200).astype(object).where(result.notna(), None).to_dict(orient="records")
            safe_rows = []
            for row in records:
                safe_rows.append(
                    {k: (v if isinstance(v, (str, int, float, bool)) or v is None else str(v)) for k, v in row.items()}
                )
            return {
                "success": True,
                "sql": safe_sql,
                "row_count": int(len(result)),
                "columns": list(result.columns),
                "rows": safe_rows,
                "error": None,
                "source": {"alias": "data"},
            }
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc), "rows": [], "sql": safe_sql}
        finally:
            con.close()

    # multi-source DuckDB
    for s in srcs:
        st = s.get("source_type") or "file"
        path_s = str(s.get("path") or "")
        if st in {"mysql", "postgresql", "mock"} or path_s.startswith("remote://"):
            return {
                "success": False,
                "error": f"Multi-dataset SQL does not support remote source {s.get('alias')}",
                "rows": [],
                "sql": safe_sql,
            }

    try:
        import duckdb
    except ImportError:
        return {"success": False, "error": "duckdb is not installed", "rows": [], "sql": safe_sql}

    con = duckdb.connect(database=":memory:")
    try:
        for s in srcs:
            alias = str(s.get("alias") or "data")
            path = Path(str(s.get("path") or ""))
            if not path.exists():
                return {
                    "success": False,
                    "error": f"Dataset file not found for {alias}: {path}",
                    "rows": [],
                    "sql": safe_sql,
                }
            err = _register_one(
                con,
                alias=alias,
                path=path,
                source_type=str(s.get("source_type") or "file"),
                table_name=s.get("table_name"),
            )
            if err:
                return {"success": False, "error": f"{alias}: {err}", "rows": [], "sql": safe_sql}

        result = con.execute(safe_sql).fetchdf()
        records = result.head(200).astype(object).where(result.notna(), None).to_dict(orient="records")
        safe_rows = []
        for row in records:
            safe_rows.append(
                {k: (v if isinstance(v, (str, int, float, bool)) or v is None else str(v)) for k, v in row.items()}
            )
        return {
            "success": True,
            "sql": safe_sql,
            "row_count": int(len(result)),
            "columns": list(result.columns),
            "rows": safe_rows,
            "error": None,
            "source": {"aliases": [str(s.get("alias")) for s in srcs]},
        }
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": str(exc), "rows": [], "sql": safe_sql}
    finally:
        con.close()
