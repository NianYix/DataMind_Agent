from __future__ import annotations

from typing import Any

import pandas as pd

from tools.statistics import _load_df, _jsonable


def anomaly_detection(
    *,
    dataset_path: str,
    column: str,
    source_type: str = "file",
    table_name: str | None = None,
) -> dict[str, Any]:
    df = _load_df(dataset_path, source_type, table_name)
    if column not in df.columns:
        return {"success": False, "error": f"Column not found: {column}"}
    series = pd.to_numeric(df[column], errors="coerce").dropna()
    if len(series) < 8:
        return {"success": True, "column": column, "outlier_count": 0, "method": "iqr", "samples": []}

    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return {"success": True, "column": column, "outlier_count": 0, "method": "iqr", "samples": []}

    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    mask = (pd.to_numeric(df[column], errors="coerce") < lower) | (pd.to_numeric(df[column], errors="coerce") > upper)
    outliers = df.loc[mask].head(20)
    records = outliers.astype(object).where(outliers.notna(), None).to_dict(orient="records")
    safe = [{k: (v if isinstance(v, (str, int, float, bool)) or v is None else str(v)) for k, v in row.items()} for row in records]
    return {
        "success": True,
        "column": column,
        "method": "iqr",
        "lower": _jsonable(lower),
        "upper": _jsonable(upper),
        "outlier_count": int(mask.sum()),
        "samples": safe,
    }
