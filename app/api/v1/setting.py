"""Per-device user setting endpoints.

Each endpoint accepts fuzzy voice-transcribed text, routes it through an
LLM-backed parser for normalization, persists the result to SQLite keyed
by device_id, and returns the normalized value so the client can mirror
it locally.
"""
from __future__ import annotations

import asyncio
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_api_token
from app.common import audit_log
from app.common.exceptions import OracleError
from app.common.response import success
from app.llm.setting_parser import (
    ParseError,
    parse_birthday,
    parse_birthtime,
    parse_city,
    parse_name,
    parse_sex,
)
from app.store.crud.settings import get_setting, upsert_field
from app.store.db import get_session

router = APIRouter(prefix="/setting", tags=["setting"])


class SettingIn(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=128, description="设备ID，作为用户主键")
    text: str = Field(..., min_length=1, max_length=500, description="用户原始输入（可能是语音识别后的文本）")


class NameIn(SettingIn):
    lang: Literal["zh", "en"] = Field("zh", description="偏好语言，默认中文")


async def _run_parse(fn, *args):
    """Parsers call the sync OpenAI SDK — run in a thread to keep the loop free."""
    return await asyncio.to_thread(fn, *args)


def _log_setting(device_id: str, field: str, raw: str, value, error: str | None = None):
    audit_log.log_event(
        device_id, "setting_update",
        level="ERROR" if error else "INFO",
        field=field, raw=raw, value=value, error=error,
    )


async def _handle(field: str, body, parser, session: AsyncSession, *extra_args):
    # scope LLM calls (inside the parser) under this device_id for audit logs
    audit_log.set_context(user_id=body.device_id)
    try:
        parsed = await _run_parse(parser, body.text, *extra_args)
    except ParseError as e:
        _log_setting(body.device_id, field, body.text, None, error=str(e))
        raise OracleError(f"解析失败: {e}", code=40001)
    except Exception as e:
        _log_setting(body.device_id, field, body.text, None, error=f"{type(e).__name__}: {e}")
        raise OracleError("LLM 解析异常，请稍后重试", code=50001)

    if isinstance(parsed, tuple):
        value = parsed[0]
        extra = {"lang": parsed[1]} if len(parsed) > 1 else {}
    else:
        value = parsed
        extra = {}

    row = await upsert_field(session, body.device_id, field, value)
    _log_setting(body.device_id, field, body.text, value)
    data = {
        "device_id": body.device_id,
        "field": field,
        "value": value,
        "raw": body.text,
        **extra,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
    return success(data)


@router.post("/birthday", dependencies=[Depends(verify_api_token)])
async def setting_birthday(body: SettingIn, session: AsyncSession = Depends(get_session)):
    """生日设置。输入："一九七零年四月十号" / "1970-4-10"，输出 "1970-04-10"。"""
    return await _handle("birthday", body, parse_birthday, session)


@router.post("/birthtime", dependencies=[Depends(verify_api_token)])
async def setting_birthtime(body: SettingIn, session: AsyncSession = Depends(get_session)):
    """出生时间设置。输入："早上七点四十" / "辰时" / "07:40"，输出 "07:40"。"""
    return await _handle("birthtime", body, parse_birthtime, session)


@router.post("/city", dependencies=[Depends(verify_api_token)])
async def setting_city(body: SettingIn, session: AsyncSession = Depends(get_session)):
    """出生地点设置。输入："福建永安" / "永安市"，输出 "福建省永安市"。"""
    return await _handle("city", body, parse_city, session)


@router.post("/name", dependencies=[Depends(verify_api_token)])
async def setting_name(body: NameIn, session: AsyncSession = Depends(get_session)):
    """姓名设置。支持拆字描述（"姓双木林、名字叫平凡的凡" → "林凡"）。默认中文，lang='en' 输出英文。"""
    return await _handle("name", body, parse_name, session, body.lang)


@router.post("/sex", dependencies=[Depends(verify_api_token)])
async def setting_sex(body: SettingIn, session: AsyncSession = Depends(get_session)):
    """性别设置。输入："男" / "男生" / "1"，输出 1；女=0。"""
    return await _handle("sex", body, parse_sex, session)


@router.get("", dependencies=[Depends(verify_api_token)])
async def get_all_settings(device_id: str, session: AsyncSession = Depends(get_session)):
    """读取某设备的全部设置。"""
    row = await get_setting(session, device_id)
    if row is None:
        return success({
            "device_id": device_id, "name": None, "sex": None,
            "birthday": None, "birthtime": None, "city": None,
            "updated_at": None,
        })
    return success(row.to_dict())
