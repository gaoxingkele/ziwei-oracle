from __future__ import annotations
from fastapi import APIRouter, Query
from pydantic import BaseModel
from app.common.response import success
from app.engine.registry import ChartRequest, calculate as engine_calculate

router = APIRouter(prefix="/chart", tags=["chart"])

class ChartBody(BaseModel):
    name: str
    birth_date: str
    birth_time: str
    gender: str
    question: str = ""
    extra: dict = {}

@router.post("/{system}")
async def create_chart(system: str, body: ChartBody, format: str = Query(default="")):
    req = ChartRequest(system=system, **body.model_dump())
    result = await engine_calculate(req)
    data = {
        "chart_id": result.chart_id,
        "system": result.system,
        "raw_data": result.raw_data,
        "text_summary": result.text_summary,
        "image_url": f"/files/charts/{result.chart_id}.png" if result.image_path else None,
    }
    if format == "tts":
        data = {"chart_id": result.chart_id, "tts_text": result.text_summary}
    return success(data)
