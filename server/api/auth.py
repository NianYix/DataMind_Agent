from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from server.core.db import get_db
from server.models import User
from server.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginBody(BaseModel):
    username: str
    password: str


class RegisterBody(BaseModel):
    username: str
    password: str = Field(min_length=4)
    email: str | None = None


@router.post("/login")
def login(body: LoginBody, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not auth_service.verify_password(body.password, user.password_hash):
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = auth_service.create_access_token(user)
    return {"access_token": token, "token_type": "bearer", "user": auth_service.serialize_user(user)}


@router.post("/register")
def register(body: RegisterBody, db: Session = Depends(get_db)):
    from fastapi import HTTPException

    from server.core.config import get_settings

    if not get_settings().auth_enabled:
        raise HTTPException(status_code=400, detail="AUTH_ENABLED is false")
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=400, detail="Username taken")
    user = User(
        username=body.username,
        email=body.email,
        password_hash=auth_service.hash_password(body.password),
        global_role="analyst",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"user": auth_service.serialize_user(user)}


@router.get("/me")
def me(user: User = Depends(auth_service.require_user)):
    return auth_service.serialize_user(user)
