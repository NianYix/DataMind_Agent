from __future__ import annotations

import logging
import sys
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
from server.api.ops import router as ops_router
from server.api.prompts import router as prompts_router
from server.api.workspaces import router as workspaces_router
from server.core.config import get_settings
from server.core.db import SessionLocal, init_db
from server.core.logging_setup import setup_logging
from server.services.auth_service import ensure_seed_admin
from server.services.dataset_service import ensure_default_workspace

settings = get_settings()
setup_logging(settings.log_path)

logger = logging.getLogger("datamind")

app = FastAPI(title="DataMind Agent API", version="0.6.0")
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


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    db = SessionLocal()
    try:
        ensure_default_workspace(db)
        ensure_seed_admin(db)
    finally:
        db.close()
    if not settings.app_api_key:
        logger.warning("APP_API_KEY is empty — Settings write / export / audit are open (dev mode)")
    if settings.auth_enabled:
        logger.info("AUTH_ENABLED=true — multi-user mode active")


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "app": "DataMind Agent",
        "version": "0.6.0",
        "auth_enabled": settings.auth_enabled,
    }
