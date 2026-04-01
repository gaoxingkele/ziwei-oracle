from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any
from app.engine.registry import ChartRequest, ChartResult, register

from app.najia import Najia

def _normalize_params(raw: str) -> list[int]:
    items = (raw or "").strip().split()
    vals: list[int] = []
    for token in items[:6]:
        try:
            v = int(token)
        except ValueError:
            v = 2
        vals.append(max(1, min(4, v)))
    while len(vals) < 6:
        vals.append(2)
    return vals

@register("liuyao")
def calculate_liuyao_engine(req: ChartRequest) -> ChartResult:
    code = req.extra.get("liuyao_code", "2 2 2 2 2 2")
    params = _normalize_params(code)
    use_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    obj = Najia(verbose=2).compile(
        params=params, date=use_date,
        gender=req.gender or "", title=req.question or "", guaci=False,
    )
    rendered = obj.render()
    data: dict[str, Any] = obj.data or {}
    return ChartResult(
        chart_id=f"ch_{uuid.uuid4().hex[:12]}",
        system="liuyao",
        raw_data={"rendered_text": rendered, "params": params, "date": use_date, "data": data},
        text_summary=rendered[:500] if rendered else "",
    )
