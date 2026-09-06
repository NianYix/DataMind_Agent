from __future__ import annotations

import re

FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|ATTACH|DETACH|COPY|EXPORT|IMPORT|PRAGMA|REPLACE|TRUNCATE|GRANT|REVOKE|VACUUM|CALL)\b",
    re.IGNORECASE,
)


class SqlSecurityError(ValueError):
    pass


def validate_readonly_sql(sql: str, *, max_limit: int = 5000) -> str:
    text = (sql or "").strip().rstrip(";")
    if not text:
        raise SqlSecurityError("SQL is empty")
    if ";" in text:
        raise SqlSecurityError("Multiple statements are not allowed")
    upper = text.lstrip().upper()
    if not (upper.startswith("SELECT") or upper.startswith("WITH")):
        raise SqlSecurityError("Only SELECT/WITH queries are allowed")
    if FORBIDDEN.search(text):
        raise SqlSecurityError("Write or dangerous SQL keywords are not allowed")
    # ensure limit cap if LIMIT present and too large
    limit_match = re.search(r"\bLIMIT\s+(\d+)\b", text, re.IGNORECASE)
    if limit_match and int(limit_match.group(1)) > max_limit:
        text = re.sub(r"\bLIMIT\s+\d+\b", f"LIMIT {max_limit}", text, flags=re.IGNORECASE)
    elif not limit_match and upper.startswith("SELECT"):
        text = f"{text} LIMIT {max_limit}"
    return text
