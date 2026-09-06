from __future__ import annotations

from pathlib import Path

import pandas as pd

from agent.cancel import clear, is_cancelled, register, request_cancel
from data.profiler import profile_dataframe, profile_file_path
from sandbox.executor import execute_python
from sandbox.python_runner import run_python
from sandbox.security import SecurityError, validate_code
from sandbox.sql_runner import run_sql
from server.core.config import get_settings
from server.services.metrics_service import collect_metrics
from server.services.settings_service import get_public_settings, mask_secret
from tools.sql_guard import SqlSecurityError, validate_readonly_sql
from tools.sql_query import sql_query


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "samples" / "sales.csv"


def test_sample_exists():
    assert SAMPLE.exists()


def test_profiler_on_sales():
    df = pd.read_csv(SAMPLE)
    profile = profile_dataframe(df, "sales.csv")
    assert profile["row_count"] > 1000
    assert "sales" in profile["numeric_fields"]
    assert profile["time_range"] is not None


def test_profile_file_path_engine():
    profile = profile_file_path(str(SAMPLE), "sales.csv", large_file_mb=9999)
    assert profile["engine"] in {"pandas", "pandas_sample", "duckdb_sample"}


def test_sandbox_rejects_os_import():
    try:
        validate_code("import os\nresult = 1")
        assert False, "should raise"
    except SecurityError:
        pass


def test_python_runner_security_code():
    out = run_python("import os\nresult=1", str(SAMPLE))
    assert out["success"] is False
    assert out["error_code"] == "SECURITY"


def test_sandbox_executes_groupby():
    code = """
result = df.groupby(df['date'].astype(str).str[:7])['sales'].sum().round(2)
"""
    out = execute_python(code, str(SAMPLE), timeout_sec=20)
    assert out["success"] is True
    assert out["result"] is not None


def test_sql_guard_rejects_delete():
    try:
        validate_readonly_sql("DELETE FROM data")
        assert False, "should raise"
    except SqlSecurityError:
        pass


def test_sql_runner_rejects_delete():
    out = run_sql(sql="DELETE FROM data", dataset_path=str(SAMPLE))
    assert out["success"] is False
    assert out["error_code"] == "SECURITY"


def test_sql_query_on_csv():
    out = sql_query(
        sql="SELECT substr(CAST(date AS VARCHAR), 1, 7) AS month, SUM(sales) AS total FROM data GROUP BY 1 ORDER BY 1",
        dataset_path=str(SAMPLE),
        source_type="file",
    )
    assert out["success"] is True
    assert out["row_count"] >= 1


def test_cancel_registry():
    register("r1")
    assert is_cancelled("r1") is False
    request_cancel("r1")
    assert is_cancelled("r1") is True
    clear("r1")
    assert is_cancelled("r1") is False


def test_estimate_cost():
    settings = get_settings()
    assert settings.estimate_cost(1000, 1000) is None or isinstance(settings.estimate_cost(1000, 1000), float)


def test_mask_secret():
    assert "***" in mask_secret("sk-abcdefghijklmnop")
    assert get_public_settings()["llm_model"]


def test_metrics_empty_shape():
    from server.core.db import SessionLocal, init_db

    init_db()
    db = SessionLocal()
    try:
        m = collect_metrics(db)
        assert "runs_total" in m
        assert "tool_success_rate" in m
    finally:
        db.close()
