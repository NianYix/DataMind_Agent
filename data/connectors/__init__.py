from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class ConnectionConfig:
    db_type: str
    host: str
    port: int
    database: str
    username: str
    password: str
    ssl: bool = False
    timeout_sec: int = 8


class DbConnector(Protocol):
    def test_connection(self, cfg: ConnectionConfig) -> dict[str, Any]: ...

    def list_tables(self, cfg: ConnectionConfig) -> list[str]: ...

    def execute_readonly(self, cfg: ConnectionConfig, sql: str, max_rows: int = 500) -> dict[str, Any]: ...

    def fetch_sample(self, cfg: ConnectionConfig, table: str, limit: int = 500) -> dict[str, Any]: ...


class MockConnector:
    """CI / offline connector with a tiny in-memory sales-like table."""

    TABLES = {
        "sales": [
            {"month": "2024-07", "region": "华东", "sales": 120.0},
            {"month": "2024-08", "region": "华东", "sales": 99.0},
            {"month": "2024-08", "region": "华北", "sales": 110.0},
        ]
    }

    def test_connection(self, cfg: ConnectionConfig) -> dict[str, Any]:
        if cfg.host == "fail.example":
            return {"ok": False, "error": "connection refused"}
        return {"ok": True, "server_version": "mock-1.0", "db_type": cfg.db_type}

    def list_tables(self, cfg: ConnectionConfig) -> list[str]:  # noqa: ARG002
        return sorted(self.TABLES.keys())

    def execute_readonly(self, cfg: ConnectionConfig, sql: str, max_rows: int = 500) -> dict[str, Any]:  # noqa: ARG002
        # Very small mock: return sales rows for any SELECT
        rows = list(self.TABLES.get("sales", []))[:max_rows]
        cols = list(rows[0].keys()) if rows else []
        return {"success": True, "sql": sql, "row_count": len(rows), "columns": cols, "rows": rows, "error": None}

    def fetch_sample(self, cfg: ConnectionConfig, table: str, limit: int = 500) -> dict[str, Any]:
        rows = list(self.TABLES.get(table, []))[:limit]
        if not rows and table not in self.TABLES:
            return {"success": False, "error": f"unknown table: {table}", "rows": [], "columns": []}
        cols = list(rows[0].keys()) if rows else []
        return {"success": True, "rows": rows, "columns": cols, "row_count": len(rows)}


def get_connector(db_type: str, *, force_mock: bool = False) -> DbConnector:
    if force_mock or db_type == "mock":
        return MockConnector()
    if db_type == "postgresql":
        from data.connectors.postgres import PostgresConnector

        return PostgresConnector()
    if db_type == "mysql":
        from data.connectors.mysql import MysqlConnector

        return MysqlConnector()
    raise ValueError(f"Unsupported db_type: {db_type}")
