from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _infer_type(series: pd.Series, col_name: str = "") -> str:
    name = str(col_name).lower()
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if pd.api.types.is_bool_dtype(series):
        return "bool"
    if pd.api.types.is_integer_dtype(series):
        return "int"
    if pd.api.types.is_float_dtype(series):
        return "float"
    # try datetime parse for object / string columns
    if series.dtype == object or pd.api.types.is_string_dtype(series) or "date" in name or "time" in name:
        sample = series.dropna().astype(str).head(30)
        if not sample.empty:
            parsed = pd.to_datetime(sample, errors="coerce", format="%Y-%m-%d")
            if parsed.notna().mean() < 0.8:
                parsed = pd.to_datetime(sample, errors="coerce")
            if parsed.notna().mean() >= 0.8:
                return "datetime"
        if "date" in name or "time" in name:
            return "datetime"
    if series.dtype == object or pd.api.types.is_string_dtype(series):
        nunique = series.nunique(dropna=True)
        if nunique > 0 and nunique <= max(20, int(len(series) * 0.05)):
            return "category"
        return "string"
    return str(series.dtype)


def _iqr_outlier_count(series: pd.Series) -> int:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if len(numeric) < 8:
        return 0
    q1, q3 = numeric.quantile(0.25), numeric.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return 0
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return int(((numeric < lower) | (numeric > upper)).sum())


def profile_dataframe(df: pd.DataFrame, dataset_name: str) -> dict[str, Any]:
    work = df.copy()
    fields: list[dict[str, Any]] = []
    time_fields: list[str] = []
    numeric_fields: list[str] = []
    categorical_fields: list[str] = []
    time_range: dict[str, str] | None = None

    for col in work.columns:
        series = work[col]
        inferred = _infer_type(series, str(col))
        if inferred == "datetime":
            work[col] = pd.to_datetime(series, errors="coerce")
            series = work[col]
            time_fields.append(col)
            valid = series.dropna()
            if not valid.empty:
                time_range = {
                    "start": str(valid.min().date()),
                    "end": str(valid.max().date()),
                }
        elif inferred in {"int", "float"}:
            numeric_fields.append(col)
        else:
            categorical_fields.append(col)

        null_ratio = float(series.isna().mean()) if len(series) else 0.0
        nunique = int(series.nunique(dropna=True))
        sample_values = [ _jsonable(v) for v in series.dropna().head(5).tolist()]
        meta: dict[str, Any] = {"sample_values": sample_values}
        if inferred in {"int", "float"}:
            numeric = pd.to_numeric(series, errors="coerce")
            meta.update(
                {
                    "min": _jsonable(numeric.min()),
                    "max": _jsonable(numeric.max()),
                    "mean": _jsonable(numeric.mean()),
                    "outlier_count": _iqr_outlier_count(series),
                }
            )

        fields.append(
            {
                "name": str(col),
                "inferred_type": inferred,
                "null_ratio": round(null_ratio, 4),
                "nunique": nunique,
                "meta": meta,
            }
        )

    duplicate_rows = int(work.duplicated().sum())
    summary_lines = [
        f"Dataset: {dataset_name}",
        f"Shape: {len(work)} rows × {len(work.columns)} columns",
        f"Time fields: {', '.join(time_fields) or 'none'}",
        f"Numeric fields: {', '.join(numeric_fields) or 'none'}",
        f"Categorical fields: {', '.join(categorical_fields) or 'none'}",
    ]
    if time_range:
        summary_lines.append(f"Time range: {time_range['start']} ~ {time_range['end']}")

    return {
        "name": dataset_name,
        "row_count": int(len(work)),
        "col_count": int(len(work.columns)),
        "time_range": time_range,
        "time_fields": time_fields,
        "numeric_fields": numeric_fields,
        "categorical_fields": categorical_fields,
        "duplicate_rows": duplicate_rows,
        "fields": fields,
        "summary_text": "\n".join(summary_lines),
        "engine": "pandas",
    }


def profile_file_path(file_path: str, dataset_name: str, *, large_file_mb: int = 30, sample_rows: int = 200_000) -> dict[str, Any]:
    """Profile CSV/Excel; use DuckDB sample path for large CSV files."""
    from pathlib import Path

    path = Path(file_path)
    size_mb = path.stat().st_size / (1024 * 1024) if path.exists() else 0
    suffix = path.suffix.lower()

    if suffix == ".csv" and size_mb >= large_file_mb:
        try:
            import duckdb

            con = duckdb.connect(database=":memory:")
            quoted = path.as_posix().replace("'", "''")
            total = con.execute(f"SELECT COUNT(*) FROM read_csv_auto('{quoted}')").fetchone()[0]
            sample_n = min(int(sample_rows), int(total))
            df = con.execute(
                f"SELECT * FROM read_csv_auto('{quoted}') USING SAMPLE {sample_n}"
            ).fetchdf()
            con.close()
            profile = profile_dataframe(df, dataset_name)
            profile["row_count"] = int(total)
            profile["engine"] = "duckdb_sample"
            profile["sample_rows"] = int(len(df))
            profile["summary_text"] = (
                profile["summary_text"]
                + f"\nEngine: duckdb_sample ({len(df)} sampled of {total}; file={size_mb:.1f}MB)"
            )
            return profile
        except Exception:  # noqa: BLE001
            pass

    from data.parser import parse_tabular_file

    df = parse_tabular_file(path)
    if len(df) > sample_rows:
        sampled = df.sample(n=sample_rows, random_state=42) if len(df) > sample_rows else df
        profile = profile_dataframe(sampled, dataset_name)
        profile["row_count"] = int(len(df))
        profile["engine"] = "pandas_sample"
        profile["sample_rows"] = int(len(sampled))
        return profile
    profile = profile_dataframe(df, dataset_name)
    profile["engine"] = "pandas"
    return profile


def _jsonable(value: Any) -> Any:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (pd.Timestamp,)):
        return str(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value
