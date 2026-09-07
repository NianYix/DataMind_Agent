from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server.api.analysis import router as analysis_router
from server.api.auth import router as auth_router
from server.api.datasources import router as datasources_router
from server.api.evaluations import router as evaluations_router
from server.api.knowledge import router as knowledge_router
from server.api.mcp import router as mcp_router
from server.api.ops import router as ops_router
from server.api.prompts import router as prompts_router
from server.api.workflows import router as workflows_router
from server.api.workspaces import router as workspaces_router
from server.core.config import get_settings
from server.core.db import SessionLocal, init_db
from server.core.logging_setup import setup_logging
from server.services.auth_service import ensure_seed_admin
from server.services.dataset_service import ensure_default_workspace
from server.services import mcp_service

settings = get_settings()
setup_logging(settings.log_path)

logger = logging.getLogger("datamind")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        ensure_default_workspace(db)
        ensure_seed_admin(db)
    finally:
        db.close()
    cfg = get_settings()
    if not cfg.app_api_key:
        logger.warning("APP_API_KEY is empty — Settings write / export / audit are open (dev mode)")
    if cfg.auth_enabled:
        logger.info("AUTH_ENABLED=true — multi-user mode active")
    try:
        mcp_service.configure_from_settings()
        if cfg.mcp_enabled:
            mcp_service.ensure_started()
            logger.info("MCP enabled — servers started from %s", cfg.mcp_config_file)
    except Exception as exc:  # noqa: BLE001
        logger.warning("MCP startup skipped: %s", exc)
    yield
    try:
        mcp_service.shutdown()
    except Exception:  # noqa: BLE001
        pass


app = FastAPI(title="DataMind Agent API", version="0.10.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(workspaces_router)
app.include_router(analysis_router)
app.include_router(ops_router)
app.include_router(evaluations_router)
app.include_router(auth_router)
app.include_router(datasources_router)
app.include_router(prompts_router)
app.include_router(knowledge_router)
app.include_router(mcp_router)
app.include_router(workflows_router)


@app.get("/api/health")
def health():
    cfg = get_settings()
    return {
        "status": "ok",
        "app": "DataMind Agent",
        "version": "0.10.0",
        "auth_enabled": cfg.auth_enabled,
        "mcp_enabled": cfg.mcp_enabled,
        "multi_agent_enabled": cfg.multi_agent_enabled,
        "critic_enabled": cfg.critic_enabled,
        "workflow_mock_analyze": cfg.workflow_mock_analyze,
    }
