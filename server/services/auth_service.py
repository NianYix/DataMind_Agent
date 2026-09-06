from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, Header, HTTPException
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from server.core.config import get_settings
from server.core.db import get_db
from server.models import User, WorkspaceMember
from server.services.dataset_service import ensure_default_workspace

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(user: User) -> str:
    settings = get_settings()
    payload = {
        "sub": user.id,
        "username": user.username,
        "role": user.global_role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_min),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc


def serialize_user(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "global_role": user.global_role,
    }


def ensure_seed_admin(db: Session) -> User | None:
    """Always ensure seed admin exists so /login works even when AUTH_ENABLED=false."""
    settings = get_settings()
    existing = db.query(User).filter(User.username == settings.seed_admin_user).first()
    if existing:
        return existing
    user = User(
        username=settings.seed_admin_user,
        email=None,
        password_hash=hash_password(settings.seed_admin_password),
        global_role="admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    ws = ensure_default_workspace(db)
    if not db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user.id, WorkspaceMember.workspace_id == ws.id).first():
        db.add(WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="admin"))
        db.commit()
    return user


def get_user_from_auth_header(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User | None:
    settings = get_settings()
    if not settings.auth_enabled:
        return None
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    payload = decode_token(token)
    user = db.get(User, str(payload.get("sub") or ""))
    return user


def require_user(user: User | None = Depends(get_user_from_auth_header)) -> User:
    settings = get_settings()
    if not settings.auth_enabled:
        raise HTTPException(status_code=400, detail="AUTH_ENABLED is false")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def require_admin(
    user: User | None = Depends(get_user_from_auth_header),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> User | None:
    """Admin JWT or APP_API_KEY. When AUTH off, falls back to require_api_key behavior."""
    settings = get_settings()
    expected = (settings.app_api_key or "").strip()
    if expected and x_api_key and x_api_key.strip() == expected:
        return user

    if not settings.auth_enabled:
        if expected and (not x_api_key or x_api_key.strip() != expected):
            raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")
        return None

    if user and user.global_role == "admin":
        return user
    if expected and x_api_key and x_api_key.strip() == expected:
        return user
    raise HTTPException(status_code=403, detail="Admin required")


def user_can_access_workspace(db: Session, user: User | None, workspace_id: str) -> bool:
    settings = get_settings()
    if not settings.auth_enabled:
        return True
    if not user:
        return False
    if user.global_role == "admin":
        return True
    return (
        db.query(WorkspaceMember)
        .filter(WorkspaceMember.user_id == user.id, WorkspaceMember.workspace_id == workspace_id)
        .first()
        is not None
    )
