from __future__ import annotations

import logging
import sys
from typing import Any

from sandbox.errors import SandboxErrorCode
from sandbox.executor import execute_python
from sandbox.security import SecurityError

logger = logging.getLogger("datamind.sandbox.python")


def _try_set_memory_limit_mb(mb: int) -> str:
    if sys.platform.startswith("win"):
        return "unsupported"
    try:
        import resource

        limit = mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
        return "applied"
    except Exception as exc:  # noqa: BLE001
        logger.info("memory_limit unsupported: %s", exc)
        return "unsupported"


def run_python(
    code: str,
    dataset_path: str,
    *,
    timeout_sec: int | None = None,
    run_id: str | None = None,
    memory_mb: int | None = None,
) -> dict[str, Any]:
    mem_status = "skipped"
    if memory_mb:
        mem_status = _try_set_memory_limit_mb(memory_mb)
        if mem_status == "unsupported":
            logger.info("run_id=%s memory_limit=unsupported", run_id)

    raw = execute_python(code, dataset_path, timeout_sec=timeout_sec)
    error = raw.get("error")
    success = bool(raw.get("success"))
    error_code: str | None = None
    if not success:
        err_l = str(error or "").lower()
        if "not allowed" in err_l or "import not allowed" in err_l or isinstance(error, SecurityError):
            error_code = SandboxErrorCode.SECURITY.value
        elif "timed out" in err_l or "timeout" in err_l:
            error_code = SandboxErrorCode.TIMEOUT.value
        elif "parse" in err_l or "json" in err_l:
            error_code = SandboxErrorCode.OUTPUT.value
        else:
            error_code = SandboxErrorCode.RUNTIME.value

    return {
        "success": success,
        "result": raw.get("result"),
        "stdout": raw.get("stdout"),
        "error": error,
        "error_code": error_code,
        "duration_ms": raw.get("duration_ms"),
        "memory_limit": mem_status,
    }
