from __future__ import annotations

from typing import Any

import pandas as pd

from data.parser import parse_tabular_file


def _load_df(dataset_path: str, source_type: str = "file", table_name: str | None = None) -> pd.DataFrame:
    if source_type in {"mysql", "postgresql", "mock"} or str(dataset_path).startswith("remote://"):
        from server.core.db import SessionLocal
        from server.services.datasource_service import execute_remote_sql, get_source
        from data.connectors import get_connector
        from server.services.datasource_service import _cfg

        parsed_id = None
        tbl = table_name
        if str(dataset_path).startswith("remote://"):
            rest = dataset_path[len("remote://") :]
            parsed_id, tbl = rest.split("/", 1)
        if not parsed_id:
            raise ValueError("remote dataset missing connection_id")
        db = SessionLocal()
        try:
            ds = get_source(db, parsed_id)
            connector = get_connector(ds.db_type, force_mock=ds.db_type == "mock")
            sample = connector.fetch_sample(_cfg(ds), tbl or "data", limit=5000)
            if not sample.get("success"):
                raise ValueError(sample.get("error") or "remote sample failed")
            return pd.DataFrame(sample.get("rows") or [])
        finally:
            db.close()
    if source_type == "sqlite":
        import sqlite3

        uri = f"file:{dataset_path}?mode=ro"
        with sqlite3.connect(uri, uri=True) as conn:
            tbl = table_name or "data"
            return pd.read_sql_query(f'SELECT * FROM "{tbl}"', conn)
    return parse_tabular_file(dataset_path)


def statistics(
    *,
    dataset_path: str,
    column: str | None = None,
    group_by: str | None = None,
    source_type: str = "file",
    table_name: str | None = None,
) -> dict[str, Any]:
    df = _load_df(dataset_path, source_type, table_name)
    if column and column not in df.columns:
        return {"success": False, "error": f"Column not found: {column}"}
    if group_by and group_by not in df.columns:
        return {"success": False, "error": f"group_by not found: {group_by}"}

    if group_by and column:
        grouped = df.groupby(group_by)[column].agg(["count", "sum", "mean", "min", "max"])
        payload = grouped.reset_index().to_dict(orient="records")
        return {"success": True, "kind": "grouped", "result": _jsonable(payload)}

    if column:
        series = df[column]
        if pd.api.types.is_numeric_dtype(series):
            desc = series.describe().to_dict()
        else:
            desc = {
                "count": int(series.count()),
                "nunique": int(series.nunique(dropna=True)),
                "top": str(series.mode().iloc[0]) if not series.mode().empty else None,
            }
        return {"success": True, "kind": "column", "column": column, "result": _jsonable(desc)}

    numeric = df.select_dtypes(include="number")
    return {
        "success": True,
        "kind": "overview",
        "result": _jsonable(numeric.describe().to_dict() if not numeric.empty else {}),
        "columns": list(df.columns),
        "row_count": int(len(df)),
    }


def _jsonable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_jsonable(v) for v in obj]
    if hasattr(obj, "item"):
        try:
            return obj.item()
        except Exception:  # noqa: BLE001
            return str(obj)
    if isinstance(obj, (float, int, str, bool)) or obj is None:
        return obj
    return str(obj)
