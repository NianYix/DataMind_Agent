from __future__ import annotations

import threading

_lock = threading.Lock()
_flags: dict[str, bool] = {}


def register(run_id: str) -> None:
    with _lock:
        _flags[run_id] = False


def request_cancel(run_id: str) -> None:
    with _lock:
        _flags[run_id] = True


def is_cancelled(run_id: str) -> bool:
    with _lock:
        return bool(_flags.get(run_id, False))


def clear(run_id: str) -> None:
    with _lock:
        _flags.pop(run_id, None)
