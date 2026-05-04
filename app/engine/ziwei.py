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
        "══════════ 紫微斗数 ══════════",
        f"性别: {d.get('gender', '?')}  星座: {d.get('sign', '?')}  生肖: {d.get('zodiac', '?')}",
        f"阳历: {d.get('solarDate', '?')}  阴历: {d.get('lunarDate', '?')}",
        f"八字: {d.get('chineseDate', '?')}  时辰: {d.get('time', '?')} ({d.get('timeRange', '?')})",
        f"命宫地支: {d.get('earthlyBranchOfSoulPalace', '?')}  五行局: {d.get('fiveElementsClass', '?')}",
        "",
        "──── 十二宫详盘 ────",
    ]
    for p in d.get("palaces") or []:
        name = p.get("name", "?")
        zhi = p.get("earthlyBranch") or p.get("heavenlyStem") or ""
        major = p.get("majorStars") or []
        minor = p.get("minorStars") or []
        adj = p.get("adjectiveStars") or []
        chg = p.get("changeStars") or []  # 四化
        major_str = "、".join(
            f"{s.get('name', '')}{('('+s.get('brightness', '')+')') if s.get('brightness') else ''}"
            for s in major
        ) or "—"
        minor_str = "、".join(s.get("name", "") for s in minor) or "—"
        adj_str = "、".join(s.get("name", "") for s in adj) or "—"
        chg_str = "、".join(
            f"{s.get('name', '')}化{s.get('mutagen', '?')}" for s in chg
        ) if chg else "—"
        lines.append(
            f"[{name}{('-'+zhi) if zhi else ''}]"
        )
        lines.append(f"    主星: {major_str}")
        lines.append(f"    辅星: {minor_str}")
        lines.append(f"    杂耀: {adj_str}")
        lines.append(f"    四化: {chg_str}")
    return "\n".join(lines)
