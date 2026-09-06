from __future__ import annotations

import argparse
import json
import sys

from evaluation import list_suites
from server.core.db import SessionLocal, init_db
from server.services.dataset_service import ensure_default_workspace


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DataMind Agent evaluation runner")
    parser.add_argument("--suite", default="sales_suite", help="Suite id (JSON stem under evaluation/datasets)")
    parser.add_argument("--mode", choices=("mock", "live"), default="mock")
    parser.add_argument("--list", action="store_true", help="List available suites")
    args = parser.parse_args(argv)

    if args.list:
        print(json.dumps(list_suites(), ensure_ascii=False, indent=2))
        return 0

    init_db()
    db = SessionLocal()
    try:
        ensure_default_workspace(db)
        from evaluation.runner import run_suite

        run = run_suite(db, args.suite, mode=args.mode)
        print(json.dumps(run.summary_json or {}, ensure_ascii=False, indent=2))
        print(f"eval_run_id={run.id} status={run.status} mode={run.mode}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
