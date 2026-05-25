from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.jobs_service import (
    create_job,
    get_job,
    list_backtest_results,
    list_jobs,
    list_validation_results,
    promote_profile_with_gate,
    run_job,
    start_job_process,
)


router = APIRouter(tags=["jobs"])


class JobRequest(BaseModel):
    job_type: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)


class PromotionRequest(BaseModel):
    strategy_slug: str = Field(min_length=1)
    profile_name: str = Field(min_length=1)
    to_status: str = Field(min_length=1)
    reason: str | None = None


@router.get("/jobs")
def jobs(
    limit: int = Query(default=100, ge=1, le=500),
    status: str | None = Query(default=None, pattern="^(pending|running|success|failed)$"),
) -> dict:
    return {"items": list_jobs(limit=limit, status=status)}


@router.get("/jobs/{job_id}")
def job_detail(job_id: int) -> dict:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"job not found: {job_id}")
    return job


@router.post("/jobs")
def create_and_run_job(payload: JobRequest) -> dict:
    if payload.job_type in {"materialize", "backtest", "validation", "optimization"}:
        job = create_job(payload.job_type, payload.payload)
        start_job_process(int(job["id"]))
        return job
    return run_job(payload.job_type, payload.payload)


@router.get("/backtests/results")
def backtest_results(limit: int = Query(default=100, ge=1, le=500)) -> dict:
    return {"items": list_backtest_results(limit=limit)}


@router.get("/validation/results")
def validation_results(limit: int = Query(default=100, ge=1, le=500)) -> dict:
    return {"items": list_validation_results(limit=limit)}


@router.post("/profiles/promote")
def profile_promote(payload: PromotionRequest) -> dict:
    try:
        return promote_profile_with_gate(
            payload.strategy_slug,
            payload.profile_name,
            payload.to_status,
            payload.reason,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
