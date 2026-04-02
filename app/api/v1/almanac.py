from __future__ import annotations
from datetime import date
from fastapi import APIRouter, Depends
from app.common.response import success
from app.api.deps import verify_api_token
from app.engine.registry import ChartRequest, ENGINES
import app.engine.almanac  # noqa: F401 — 触发 @register

router = APIRouter(prefix="/almanac", tags=["almanac"])


def _query(date_str: str) -> dict:
    req = ChartRequest(
        system="almanac", name="", birth_date=date_str,
        birth_time="", gender="",
    )
    result = ENGINES["almanac"](req)
    return result.raw_data


@router.get("/today")
async def almanac_today(_: str = Depends(verify_api_token)):
    return success(_query(date.today().isoformat()))


@router.get("/{date_str}")
async def almanac_by_date(date_str: str, _: str = Depends(verify_api_token)):
    return success(_query(date_str))
