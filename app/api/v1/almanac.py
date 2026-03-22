from __future__ import annotations
from datetime import date
from fastapi import APIRouter
from app.common.response import success
from app.engine.almanac import get_almanac_for_date

router = APIRouter(prefix="/almanac", tags=["almanac"])

@router.get("/today")
async def almanac_today():
    return success(get_almanac_for_date(date.today().isoformat()))

@router.get("/{date_str}")
async def almanac_by_date(date_str: str):
    return success(get_almanac_for_date(date_str))
