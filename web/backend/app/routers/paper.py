from __future__ import annotations

from fastapi import APIRouter

from app.services.paper_service import paper_summary


router = APIRouter(tags=["paper"])


@router.get("/paper/summary")
def summary() -> dict:
    return paper_summary()
