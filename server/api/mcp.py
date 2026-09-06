from __future__ import annotations

from fastapi import APIRouter, Depends

from server.services import auth_service, mcp_service

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


@router.get("/status")
def mcp_status():
    return mcp_service.status()


@router.get("/tools")
def mcp_tools():
    return {"tools": mcp_service.list_tools()}


@router.post("/reload")
def mcp_reload(_=Depends(auth_service.require_admin)):
    return mcp_service.reload()
