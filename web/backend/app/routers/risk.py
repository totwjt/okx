from __future__ import annotations

from fastapi import APIRouter

from app.services.risk_service import risk_summary


router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/summary")
def get_risk_summary() -> dict:
    return risk_summary()
