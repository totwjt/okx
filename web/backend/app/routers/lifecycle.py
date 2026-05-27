from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.evidence_gate_service import run_evidence_check
from app.services.lifecycle_service import (
    advance_profile,
    demote_profile,
    lifecycle_strategies,
    profile_lifecycle,
    promote_profile,
    strategy_lifecycle,
    update_profile_thesis,
)
from app.services.lifecycle_reset_service import reset_all_strategies
from app.services.paper_run_service import create_paper_run, current_paper_run, review_paper_run
from app.services.runtime_alignment_service import runtime_alignment


router = APIRouter(prefix="/lifecycle", tags=["lifecycle"])


class EvidenceCheckRequest(BaseModel):
    target_status: str = Field(default="validated", min_length=1)
    thresholds: dict | None = None


class PromotionActionRequest(BaseModel):
    to_status: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class PaperRunCreateRequest(BaseModel):
    strategy_slug: str = Field(min_length=1)
    profile_name: str = Field(min_length=1)
    run_name: str | None = None
    start_balance: float | None = None


class PaperRunReviewRequest(BaseModel):
    passed: bool
    conclusion: str = Field(min_length=1)


class ThesisUpdateRequest(BaseModel):
    thesis: dict = Field(default_factory=dict)


class AdvanceRequest(BaseModel):
    candidate_count: int = Field(default=3, ge=3, le=6)


@router.get("/strategies")
def strategies() -> dict:
    return {"items": lifecycle_strategies()}


@router.delete("/strategies")
def reset_strategies() -> dict:
    try:
        return reset_all_strategies()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{strategy_slug}")
def lifecycle_detail(strategy_slug: str) -> dict:
    lifecycle = strategy_lifecycle(strategy_slug)
    if not lifecycle:
        raise HTTPException(status_code=404, detail=f"strategy not found: {strategy_slug}")
    return lifecycle


@router.get("/{strategy_slug}/profiles/{profile_name}")
def profile_detail(strategy_slug: str, profile_name: str) -> dict:
    lifecycle = profile_lifecycle(strategy_slug, profile_name)
    if not lifecycle:
        raise HTTPException(
            status_code=404,
            detail=f"profile lifecycle not found: {strategy_slug}/{profile_name}",
        )
    return lifecycle


@router.post("/{strategy_slug}/profiles/{profile_name}/evidence-check")
def evidence_check(strategy_slug: str, profile_name: str, payload: EvidenceCheckRequest) -> dict:
    try:
        return run_evidence_check(
            strategy_slug,
            profile_name,
            target_status=payload.target_status,
            thresholds=payload.thresholds,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{strategy_slug}/profiles/{profile_name}/advance")
def advance(strategy_slug: str, profile_name: str, payload: AdvanceRequest) -> dict:
    try:
        return advance_profile(strategy_slug, profile_name, candidate_count=payload.candidate_count)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/paper-runs")
def create_run(payload: PaperRunCreateRequest) -> dict:
    try:
        return create_paper_run(
            payload.strategy_slug,
            payload.profile_name,
            run_name=payload.run_name,
            start_balance=payload.start_balance,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/paper-runs/current")
def current_run(strategy_slug: str | None = None, profile_name: str | None = None) -> dict:
    run = current_paper_run(strategy_slug, profile_name)
    return {"item": run}


@router.post("/paper-runs/{run_id}/review")
def review_run(run_id: int, payload: PaperRunReviewRequest) -> dict:
    try:
        return review_paper_run(run_id, payload.passed, payload.conclusion)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{strategy_slug}/profiles/{profile_name}/alignment")
def alignment_detail(strategy_slug: str, profile_name: str) -> dict:
    return runtime_alignment(strategy_slug, profile_name)


@router.post("/{strategy_slug}/profiles/{profile_name}/promote")
def promote(strategy_slug: str, profile_name: str, payload: PromotionActionRequest) -> dict:
    try:
        return promote_profile(strategy_slug, profile_name, payload.to_status, payload.reason)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/{strategy_slug}/profiles/{profile_name}/thesis")
def update_thesis(strategy_slug: str, profile_name: str, payload: ThesisUpdateRequest) -> dict:
    try:
        return update_profile_thesis(strategy_slug, profile_name, payload.thesis)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{strategy_slug}/profiles/{profile_name}/demote")
def demote(strategy_slug: str, profile_name: str, payload: PromotionActionRequest) -> dict:
    try:
        return demote_profile(strategy_slug, profile_name, payload.to_status, payload.reason)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
