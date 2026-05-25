from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.optimization_service import auto_tune_strategy, optimization_assistant, save_draft_profile


router = APIRouter(prefix="/optimization", tags=["optimization"])


class DraftProfileRequest(BaseModel):
    profile_name: str = Field(min_length=1)
    baseline_profile: str | None = None
    overrides: dict = Field(default_factory=dict)


class AutoTuneRequest(BaseModel):
    baseline_profile: str | None = None
    candidate_count: int = Field(default=3, ge=3, le=12)
    run_backtests: bool = True


@router.get("/{strategy_slug}")
def assistant(strategy_slug: str, baseline_profile: str | None = None) -> dict:
    try:
        return optimization_assistant(strategy_slug, baseline_profile)
    except RuntimeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{strategy_slug}/profiles")
def save_profile(strategy_slug: str, payload: DraftProfileRequest) -> dict:
    try:
        return save_draft_profile(
            strategy_slug,
            payload.profile_name,
            payload.baseline_profile,
            payload.overrides,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{strategy_slug}/auto-tune")
def auto_tune(strategy_slug: str, payload: AutoTuneRequest) -> dict:
    try:
        return auto_tune_strategy(
            strategy_slug,
            payload.baseline_profile,
            candidate_count=payload.candidate_count,
            run_backtests=payload.run_backtests,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
