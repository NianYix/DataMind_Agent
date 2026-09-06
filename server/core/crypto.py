from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

from server.core.config import get_settings


def _fernet() -> Fernet:
    raw = get_settings().credential_secret.encode("utf-8")
    key = base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
    return Fernet(key)


def encrypt_secret(plain: str) -> str:
    return _fernet().encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str:
    return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")


def mask_password(_: str | None = None) -> str:
    return "********"
