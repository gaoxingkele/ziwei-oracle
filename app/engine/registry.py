from __future__ import annotations
import asyncio
from typing import Any, Callable
from pydantic import BaseModel
from app.common.exceptions import UnsupportedSystemError

class ChartRequest(BaseModel):
    system: str
    name: str
    birth_date: str
    birth_time: str
    gender: str
    question: str = ""
    extra: dict[str, Any] = {}

class ChartResult(BaseModel):
    chart_id: str
    system: str
    raw_data: dict[str, Any]
    text_summary: str
    image_path: str | None = None

ENGINES: dict[str, Callable] = {}

def register(system: str):
    def wrapper(func: Callable) -> Callable:
        ENGINES[system] = func
        return func
    return wrapper

async def calculate(request: ChartRequest) -> ChartResult:
    engine = ENGINES.get(request.system)
    if not engine:
        raise UnsupportedSystemError(request.system)
    if asyncio.iscoroutinefunction(engine):
        return await engine(request)
    return await asyncio.to_thread(engine, request)

def list_systems() -> list[str]:
    return list(ENGINES.keys())
