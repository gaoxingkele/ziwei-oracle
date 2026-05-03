from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any
from app.engine.registry import ChartRequest, ChartResult, register

from app.najia import Najia
from app.najia.analysis import analyze as najia_analyze

def _normalize_params(raw: Any) -> list[int]:
    if isinstance(raw, (list, tuple)):
        items = list(raw)
    else:
        items = (str(raw) if raw is not None else "").strip().split()
    vals: list[int] = []
    for token in items[:6]:
        try:
            v = int(token)
        except (ValueError, TypeError):
            v = 2
        vals.append(max(1, min(4, v)))
    while len(vals) < 6:
        vals.append(2)
    return vals

@register("liuyao")
def calculate_liuyao_engine(req: ChartRequest) -> ChartResult:
    code = req.extra.get("yao_codes")
    if code is None:
        code = req.extra.get("liuyao_code", "2 2 2 2 2 2")
    params = _normalize_params(code)
    use_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    obj = Najia(verbose=2).compile(
        params=params, date=use_date,
        gender=req.gender or "", title=req.question or "", guaci=False,
    )
    # 必须在 render() 之前 analyze: render() 会原地改写 obj.data['shiy'] 等字段
    try:
        analysis = najia_analyze(obj.data or {}, question=req.question or "", gender=req.gender or "")
    except Exception as exc:
        analysis = {"error": f"{type(exc).__name__}: {exc}"}
    rendered = obj.render()
    data: dict[str, Any] = obj.data or {}
    summary = analysis.get("summary", "") if isinstance(analysis, dict) else ""
    text_summary = (
        f"{rendered[:500]}\n\n【算法断卦】\n{summary}" if summary else (rendered[:500] if rendered else "")
    )
    return ChartResult(
        chart_id=f"ch_{uuid.uuid4().hex[:12]}",
        system="liuyao",
        raw_data={
            "rendered_text": rendered, "params": params, "date": use_date,
            "data": data, "analysis": analysis,
        },
        text_summary=text_summary,
    )
