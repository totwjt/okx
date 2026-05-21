from __future__ import annotations

from fastapi import APIRouter

from app.services.system_check import run_system_check


router = APIRouter(tags=["system"])


@router.get("/system/check")
def system_check() -> dict:
    return run_system_check()

