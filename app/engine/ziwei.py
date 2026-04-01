from __future__ import annotations
import uuid
from typing import Any
from app.common.utils import parse_shichen
from app.engine.registry import ChartRequest, ChartResult, register

from app.pureziwei import Astro

@register("ziwei")
def calculate_ziwei(req: ChartRequest) -> ChartResult:
    astro = Astro()
    time_idx = parse_shichen(req.birth_time)
    if time_idx is None:
        time_idx = 6
    gender_cn = "男" if req.gender.strip().lower() in ("male", "m", "男") else "女"
    raw = astro.by_solar(req.birth_date, time_idx, gender_cn)
    data = raw.model_dump(by_alias=True, mode="json")
    text = _build_text(data)
    return ChartResult(
        chart_id=f"ch_{uuid.uuid4().hex[:12]}",
        system="ziwei", raw_data=data, text_summary=text,
    )

def _build_text(d: dict[str, Any]) -> str:
    lines = [
        "----------基本信息----------",
        f"命主性别：{d.get('gender', '未知')}",
        f"阳历生日：{d.get('solarDate', '未知')}",
        f"阴历生日：{d.get('lunarDate', '未知')}",
        f"八字：{d.get('chineseDate', '未知')}",
        f"生辰时辰：{d.get('time', '未知')} ({d.get('timeRange', '未知')})",
        f"星座：{d.get('sign', '未知')}",
        f"生肖：{d.get('zodiac', '未知')}",
        f"命宫地支：{d.get('earthlyBranchOfSoulPalace', '未知')}",
        f"五行局：{d.get('fiveElementsClass', '未知')}",
        "----------宫位信息----------",
    ]
    for p in d.get("palaces") or []:
        name = p.get("name", "?")
        major = p.get("majorStars") or []
        stars = ", ".join(f"{s.get('name', '')}({s.get('brightness', '')})" for s in major)
        lines.append(f"[{name}] 主星: {stars or '无'}")
    return "\n".join(lines)
