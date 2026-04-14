from __future__ import annotations

from datetime import datetime

from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.store.db import Base


class UserSetting(Base):
    """Per-device user profile. device_id acts as the primary user key."""
    __tablename__ = "user_settings"

    device_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(64), default=None)
    sex: Mapped[int | None] = mapped_column(Integer, default=None)  # 1=男, 0=女
    birthday: Mapped[str | None] = mapped_column(String(10), default=None)  # YYYY-MM-DD
    birthtime: Mapped[str | None] = mapped_column(String(5), default=None)  # HH:MM
    city: Mapped[str | None] = mapped_column(String(128), default=None)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "device_id": self.device_id,
            "name": self.name,
            "sex": self.sex,
            "birthday": self.birthday,
            "birthtime": self.birthtime,
            "city": self.city,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
