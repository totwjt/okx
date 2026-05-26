from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.registry_service import (
    create_profile_draft,
    create_strategy_draft,
    get_strategy,
    list_runtime_artifacts,
    list_strategies,
    list_strategy_profiles,
    materialize_strategy,
    scaffold_profile_defaults,
    scaffold_strategy_definition,
    update_profile_overrides,
)


router = APIRouter(tags=["registry"])


class MaterializeRequest(BaseModel):
    strategy_slug: str = Field(min_length=1)
    profile_name: str | None = None


class StrategyDraftRequest(BaseModel):
    slug: str = Field(min_length=3)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    profile_name: str = "draft"
    thesis: dict = Field(default_factory=dict)


class ProfileDraftRequest(BaseModel):
    profile_name: str = Field(min_length=1)
    source_profile: str | None = None
    overrides: dict = Field(default_factory=dict)
    thesis: dict = Field(default_factory=dict)


class ProfileOverridesRequest(BaseModel):
    overrides: dict = Field(default_factory=dict)


@router.get("/strategies")
def strategies() -> dict:
    return {"items": list_strategies()}


@router.post("/strategies")
def create_strategy(payload: StrategyDraftRequest) -> dict:
    try:
        return create_strategy_draft(
            slug=payload.slug,
            name=payload.name,
            description=payload.description,
            profile_name=payload.profile_name,
            thesis=payload.thesis,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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


@router.post("/strategies/{slug}/profiles")
def create_profile(slug: str, payload: ProfileDraftRequest) -> dict:
    try:
        return create_profile_draft(
            strategy_slug=slug,
            profile_name=payload.profile_name,
            source_profile=payload.source_profile,
            overrides=payload.overrides,
            thesis=payload.thesis,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/strategies/{slug}/definition/scaffold")
def scaffold_definition(slug: str, profile_name: str | None = None) -> dict:
    try:
        return scaffold_strategy_definition(slug, profile_name)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/strategies/{slug}/profiles/{profile_name}/defaults")
def scaffold_profile(slug: str, profile_name: str) -> dict:
    try:
        return scaffold_profile_defaults(slug, profile_name)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/strategies/{slug}/profiles/{profile_name}/overrides")
def update_profile(slug: str, profile_name: str, payload: ProfileOverridesRequest) -> dict:
    try:
        return update_profile_overrides(slug, profile_name, payload.overrides)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/runtime/artifacts")
def runtime_artifacts(limit: int = Query(default=100, ge=1, le=500)) -> dict:
    return {"items": list_runtime_artifacts(limit)}


@router.post("/runtime/materialize")
def runtime_materialize(payload: MaterializeRequest) -> dict:
    try:
        return materialize_strategy(payload.strategy_slug, payload.profile_name)
    except RuntimeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
