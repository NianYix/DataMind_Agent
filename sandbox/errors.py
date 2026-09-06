from __future__ import annotations

from enum import Enum


class SandboxErrorCode(str, Enum):
    SECURITY = "SECURITY"
    TIMEOUT = "TIMEOUT"
    RUNTIME = "RUNTIME"
    OUTPUT = "OUTPUT"


class SandboxError(Exception):
    def __init__(self, message: str, code: SandboxErrorCode) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
