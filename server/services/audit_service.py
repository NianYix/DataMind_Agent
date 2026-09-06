from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from server.models import AuditEvent

logger = logging.getLogger("datamind.audit")


def record(
    db: Session | None,
    *,
    event_type: str,
    message: str,
    run_id: str | None = None,
    level: str = "info",
    payload: dict[str, Any] | None = None,
) -> None:
    logger.log(
        logging.WARNING if level in {"warn", "warning", "error"} else logging.INFO,
        "audit event_type=%s run_id=%s %s",
        event_type,
        run_id,
        message,
    )
    if db is None:
        return
    try:
        db.add(
            AuditEvent(
                event_type=event_type,
                run_id=run_id,
                level=level,
                message=message[:2000],
                payload_json=payload,
            )
        )
        db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("failed to persist audit: %s", exc)
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            pass
