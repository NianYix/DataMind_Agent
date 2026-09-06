from __future__ import annotations

import logging

from fastapi import Header, HTTPException

from server.core.config import get_settings

logger = logging.getLogger("datamind.security")


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    settings = get_settings()
    expected = (settings.app_api_key or "").strip()
    if not expected:
        return
    if not x_api_key or x_api_key.strip() != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")
