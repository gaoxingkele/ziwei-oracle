"""Async SQLAlchemy engine + session for user settings.

Default: SQLite via aiosqlite (zero-config). Override with SETTINGS_DB_URL
for PostgreSQL (postgresql+asyncpg://...).
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import SETTINGS_DB_URL


class Base(DeclarativeBase):
    pass


engine = create_async_engine(SETTINGS_DB_URL, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    """Create tables if they don't exist. Safe to call on every startup."""
    # import models so they register with Base.metadata
    from app.store.models import settings  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
