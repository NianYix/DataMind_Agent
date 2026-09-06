from __future__ import annotations

from typing import Any

from data.connectors import ConnectionConfig


class PostgresConnector:
    def _connect(self, cfg: ConnectionConfig):
        import psycopg

        return psycopg.connect(
            host=cfg.host,
            port=cfg.port,
            dbname=cfg.database,
            user=cfg.username,
            password=cfg.password,
            connect_timeout=cfg.timeout_sec,
            sslmode="require" if cfg.ssl else "prefer",
        )

    def test_connection(self, cfg: ConnectionConfig) -> dict[str, Any]:
        try:
            with self._connect(cfg) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT version()")
                    ver = cur.fetchone()[0]
            return {"ok": True, "server_version": str(ver), "db_type": "postgresql"}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc).replace(cfg.password, "***")}

    def list_tables(self, cfg: ConnectionConfig) -> list[str]:
        with self._connect(cfg) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_type IN ('BASE TABLE','VIEW')
                    ORDER BY table_name
                    """
                )
                return [r[0] for r in cur.fetchall()]

    def execute_readonly(self, cfg: ConnectionConfig, sql: str, max_rows: int = 500) -> dict[str, Any]:
        try:
            with self._connect(cfg) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    cols = [d.name for d in cur.description] if cur.description else []
                    raw = cur.fetchmany(max_rows)
            rows = [dict(zip(cols, row, strict=False)) for row in raw]
            safe = [{k: (v if isinstance(v, (str, int, float, bool)) or v is None else str(v)) for k, v in r.items()} for r in rows]
            return {"success": True, "sql": sql, "row_count": len(safe), "columns": cols, "rows": safe, "error": None}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc).replace(cfg.password, "***"), "rows": [], "sql": sql}

    def fetch_sample(self, cfg: ConnectionConfig, table: str, limit: int = 500) -> dict[str, Any]:
        return self.execute_readonly(cfg, f'SELECT * FROM "{table}" LIMIT {int(limit)}', max_rows=limit)
