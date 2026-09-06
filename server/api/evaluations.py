from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from server.core.db import get_db
from server.core.security import require_api_key
from server.services import eval_service

router = APIRouter(prefix="/api", tags=["evaluations"])


class EvaluationCreate(BaseModel):
    suite_id: str = Field(default="sales_suite")
    mode: str = Field(default="mock", pattern="^(mock|live)$")


@router.get("/evaluation-suites")
def get_suites():
    return eval_service.available_suites()


@router.post("/evaluations")
def create_evaluation(
    body: EvaluationCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_api_key),
):
    try:
        run = eval_service.start_evaluation(db, body.suite_id, mode=body.mode)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {exc}") from exc
    cases = eval_service.list_case_results(db, run.id)
    return eval_service.serialize_run(run, cases=cases)


@router.get("/evaluations")
def list_evaluations(limit: int = 50, db: Session = Depends(get_db)):
    runs = eval_service.list_evaluations(db, limit=limit)
    return [eval_service.serialize_run(r) for r in runs]


@router.get("/evaluations/{eval_id}")
def get_evaluation(eval_id: str, db: Session = Depends(get_db)):
    run = eval_service.get_evaluation(db, eval_id)
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    cases = eval_service.list_case_results(db, eval_id)
    return eval_service.serialize_run(run, cases=cases)


@router.get("/evaluations/{eval_id}/summary")
def get_evaluation_summary(eval_id: str, db: Session = Depends(get_db)):
    run = eval_service.get_evaluation(db, eval_id)
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return {
        "id": run.id,
        "suite_id": run.suite_id,
        "mode": run.mode,
        "status": run.status,
        "summary_json": run.summary_json or {},
    }
