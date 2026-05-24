from __future__ import annotations

from fastapi import APIRouter

from app.services.factors_service import factors_health


router = APIRouter(prefix="/factors", tags=["factors"])


@router.get("/health")
def get_factors_health() -> dict:
    return factors_health()
