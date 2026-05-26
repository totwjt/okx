from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.jobs_service import create_job, start_job_process


router = APIRouter(prefix="/data", tags=["data"])


class DataEnsureRequest(BaseModel):
    strategy_slug: str = Field(min_length=1)
    profile_name: str | None = None
    pair: str | None = None
    timeframe: str | None = None
    trading_mode: str | None = None
    timerange: str | None = None
    erase: bool = False
    no_parallel_download: bool = False
    candle_types: list[str] | None = None
    timeout_seconds: int | None = None


@router.post("/ensure")
def ensure_data(payload: DataEnsureRequest) -> dict[str, Any]:
    job = create_job("data_ensure", payload.model_dump(exclude_none=True))
    if not job.get("deduped"):
        start_job_process(int(job["id"]))
    return job
