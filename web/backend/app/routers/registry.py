from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.registry_service import (
    get_strategy,
    list_runtime_artifacts,
    list_strategies,
    list_strategy_profiles,
    materialize_strategy,
)


router = APIRouter(tags=["registry"])


class MaterializeRequest(BaseModel):
    strategy_slug: str = Field(min_length=1)
    profile_name: str | None = None


@router.get("/strategies")
def strategies() -> dict:
    return {"items": list_strategies()}


@router.get("/strategies/{slug}")
def strategy_detail(slug: str) -> dict:
    strategy = get_strategy(slug)
    if not strategy:
        raise HTTPException(status_code=404, detail=f"strategy not found: {slug}")
    return strategy


@router.get("/strategies/{slug}/profiles")
def strategy_profiles(slug: str) -> dict:
    profiles = list_strategy_profiles(slug)
    if profiles is None:
        raise HTTPException(status_code=404, detail=f"strategy not found: {slug}")
    return {"strategy_slug": slug, "items": profiles}


@router.get("/runtime/artifacts")
def runtime_artifacts(limit: int = Query(default=100, ge=1, le=500)) -> dict:
    return {"items": list_runtime_artifacts(limit)}


@router.post("/runtime/materialize")
def runtime_materialize(payload: MaterializeRequest) -> dict:
    try:
        return materialize_strategy(payload.strategy_slug, payload.profile_name)
    except RuntimeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
