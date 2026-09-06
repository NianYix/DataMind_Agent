from __future__ import annotations

from typing import Any

from data.connectors import ConnectionConfig


class MysqlConnector:
    def _connect(self, cfg: ConnectionConfig):
        import pymysql

        return pymysql.connect(
            host=cfg.host,
            port=cfg.port,
            user=cfg.username,
            password=cfg.password,
            database=cfg.database,
            connect_timeout=cfg.timeout_sec,
            ssl={"ssl": {}} if cfg.ssl else None,
            cursorclass=pymysql.cursors.DictCursor,
        )

    def test_connection(self, cfg: ConnectionConfig) -> dict[str, Any]:
        try:
            conn = self._connect(cfg)
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT VERSION() AS v")
                    row = cur.fetchone()
                return {"ok": True, "server_version": str((row or {}).get("v")), "db_type": "mysql"}
            finally:
                conn.close()
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc).replace(cfg.password, "***")}

    def list_tables(self, cfg: ConnectionConfig) -> list[str]:
        conn = self._connect(cfg)
        try:
            with conn.cursor() as cur:
                cur.execute("SHOW TABLES")
                rows = cur.fetchall()
            if not rows:
                return []
            key = next(iter(rows[0].keys()))
            return [str(r[key]) for r in rows]
        finally:
            conn.close()

    def execute_readonly(self, cfg: ConnectionConfig, sql: str, max_rows: int = 500) -> dict[str, Any]:
        try:
            conn = self._connect(cfg)
            try:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    rows = cur.fetchmany(max_rows)
                cols = list(rows[0].keys()) if rows else []
                safe = [
                    {k: (v if isinstance(v, (str, int, float, bool)) or v is None else str(v)) for k, v in r.items()}
                    for r in rows
                ]
                return {"success": True, "sql": sql, "row_count": len(safe), "columns": cols, "rows": safe, "error": None}
            finally:
                conn.close()
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc).replace(cfg.password, "***"), "rows": [], "sql": sql}

    def fetch_sample(self, cfg: ConnectionConfig, table: str, limit: int = 500) -> dict[str, Any]:
        return self.execute_readonly(cfg, f"SELECT * FROM `{table}` LIMIT {int(limit)}", max_rows=limit)
