from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

_configured = False


def setup_logging(log_dir) -> None:
    global _configured
    if _configured:
        return
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "datamind.log"

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")

    fh = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
    fh.setFormatter(fmt)
    fh.setLevel(logging.INFO)

    if not any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        root.addHandler(fh)

    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler) for h in root.handlers):
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        sh.setLevel(logging.INFO)
        root.addHandler(sh)

    _configured = True
    logging.getLogger("datamind").info("Logging to %s", log_file)
