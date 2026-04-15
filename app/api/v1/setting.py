"""Per-device user setting endpoints.

Client sends already-normalized values (wheel picker / direct input); server
validates format and persists to SQLite keyed by device_id. No LLM call.
"""
from __future__ import annotations

import re
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_api_token
from app.common import audit_log
from app.common.exceptions import ValidationError
from app.common.response import success
from app.store.crud.settings import get_setting, upsert_field
from app.store.db import get_session

router = APIRouter(prefix="/setting", tags=["setting"])

_BIRTHDAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_BIRTHTIME_RE = re.compile(r"^\d{1,2}:\d{2}$")
_SEX_MAP: dict = {
    # 男 → 1
    "男": 1, "男生": 1, "男性": 1, "male": 1, "m": 1, "boy": 1, "1": 1, 1: 1,
    # 女 → 0
    "女": 0, "女生": 0, "女性": 0, "female": 0, "f": 0, "girl": 0, "0": 0, 0: 0,
}


class SettingIn(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=128, description="设备ID")
    text: str = Field(..., min_length=1, max_length=500, description="客户端提交的值")


class NameIn(SettingIn):
    lang: Literal["zh", "en"] = Field("zh", description="语言标签，默认 zh")


def _log(device_id: str, field: str, raw: str, value, error: str | None = None):
    audit_log.log_event(
        device_id, "setting_update",
        level="ERROR" if error else "INFO",
        field=field, raw=raw, value=value, error=error,
    )


def _validate_birthday(text: str) -> str:
    t = text.strip()
    if not _BIRTHDAY_RE.match(t):
        raise ValidationError(f"生日格式无效，需为 YYYY-MM-DD，收到: {t}")
    y, m, d = int(t[0:4]), int(t[5:7]), int(t[8:10])
    if not (1900 <= y <= 2100 and 1 <= m <= 12 and 1 <= d <= 31):
        raise ValidationError(f"生日取值越界: {t}")
    return t


def _validate_birthtime(text: str) -> str:
    t = text.strip().replace("：", ":")
    if not _BIRTHTIME_RE.match(t):
        raise ValidationError(f"时间格式无效，需为 HH:MM，收到: {t}")
    h, mi = t.split(":")
    h_i, m_i = int(h), int(mi)
    if not (0 <= h_i <= 23 and 0 <= m_i <= 59):
        raise ValidationError(f"时间取值越界: {t}")
    return f"{h_i:02d}:{m_i:02d}"


def _validate_sex(text) -> int:
    if isinstance(text, str):
        key = text.strip()
        if key in _SEX_MAP:
            return _SEX_MAP[key]
        if key.lower() in _SEX_MAP:
            return _SEX_MAP[key.lower()]
    elif text in _SEX_MAP:
        return _SEX_MAP[text]
    raise ValidationError(f"性别无法识别: {text}，期望 男/女/1/0/male/female")


def _validate_text(text: str, field: str) -> str:
    t = text.strip()
    if not t:
        raise ValidationError(f"{field} 不能为空")
    return t


async def _save_and_respond(
    session: AsyncSession, device_id: str, field: str,
    raw: str, value, extra: dict | None = None,
):
    row = await upsert_field(session, device_id, field, value)
    _log(device_id, field, raw, value)
    data = {
        "device_id": device_id,
        "field": field,
        "value": value,
        "raw": raw,
        **(extra or {}),
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
    return success(data)


@router.post("/birthday", dependencies=[Depends(verify_api_token)])
async def setting_birthday(body: SettingIn, session: AsyncSession = Depends(get_session)):
    """生日。客户端直接传 YYYY-MM-DD（滚轮选择器已格式化）。"""
    try:
        value = _validate_birthday(body.text)
    except ValidationError as e:
        _log(body.device_id, "birthday", body.text, None, error=e.message)
        raise
    return await _save_and_respond(session, body.device_id, "birthday", body.text, value)


@router.post("/birthtime", dependencies=[Depends(verify_api_token)])
async def setting_birthtime(body: SettingIn, session: AsyncSession = Depends(get_session)):
    """出生时间。客户端直接传 HH:MM（24h）。"""
    try:
        value = _validate_birthtime(body.text)
    except ValidationError as e:
        _log(body.device_id, "birthtime", body.text, None, error=e.message)
        raise
    return await _save_and_respond(session, body.device_id, "birthtime", body.text, value)


@router.post("/city", dependencies=[Depends(verify_api_token)])
async def setting_city(body: SettingIn, session: AsyncSession = Depends(get_session)):
    """出生地。客户端直接传字符串，服务端原样保存。"""
    try:
        value = _validate_text(body.text, "出生地")
    except ValidationError as e:
        _log(body.device_id, "city", body.text, None, error=e.message)
        raise
    return await _save_and_respond(session, body.device_id, "city", body.text, value)


@router.post("/name", dependencies=[Depends(verify_api_token)])
async def setting_name(body: NameIn, session: AsyncSession = Depends(get_session)):
    """姓名。客户端直接传字符串，服务端原样保存；lang 仅作标签透传。"""
    try:
        value = _validate_text(body.text, "姓名")
    except ValidationError as e:
        _log(body.device_id, "name", body.text, None, error=e.message)
        raise
    return await _save_and_respond(
        session, body.device_id, "name", body.text, value, extra={"lang": body.lang}
    )


@router.post("/sex", dependencies=[Depends(verify_api_token)])
async def setting_sex(body: SettingIn, session: AsyncSession = Depends(get_session)):
    """性别。客户端可传 男/女/1/0/male/female 等，服务端映射为整数 1(男)/0(女)。"""
    try:
        value = _validate_sex(body.text)
    except ValidationError as e:
        _log(body.device_id, "sex", body.text, None, error=e.message)
        raise
    return await _save_and_respond(session, body.device_id, "sex", body.text, value)


@router.get("", dependencies=[Depends(verify_api_token)])
async def get_all_settings(device_id: str, session: AsyncSession = Depends(get_session)):
    """读取某设备的全部设置。字段未设置返回 null。"""
    row = await get_setting(session, device_id)
    if row is None:
        return success({
            "device_id": device_id, "name": None, "sex": None,
            "birthday": None, "birthtime": None, "city": None,
            "updated_at": None,
        })
    return success(row.to_dict())
