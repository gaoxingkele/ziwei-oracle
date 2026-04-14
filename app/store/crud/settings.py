from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.store.models.settings import UserSetting


async def get_setting(session: AsyncSession, device_id: str) -> UserSetting | None:
    result = await session.execute(select(UserSetting).where(UserSetting.device_id == device_id))
    return result.scalar_one_or_none()


async def upsert_field(session: AsyncSession, device_id: str, field: str, value: Any) -> UserSetting:
    allowed = {"name", "sex", "birthday", "birthtime", "city"}
    if field not in allowed:
        raise ValueError(f"invalid field: {field}")
    row = await get_setting(session, device_id)
    if row is None:
        row = UserSetting(device_id=device_id)
        session.add(row)
    setattr(row, field, value)
    row.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(row)
    return row
