from __future__ import annotations
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from app.engine.registry import ChartRequest, ChartResult, register

@dataclass(frozen=True)
class Trigram:
    idx: int; name: str; symbol: str; element: str; lines: tuple[int, int, int]

TRIGRAMS: dict[int, Trigram] = {
    1: Trigram(1, "乾", "☰", "金", (1, 1, 1)), 2: Trigram(2, "兑", "☱", "金", (1, 1, 0)),
    3: Trigram(3, "离", "☲", "火", (1, 0, 1)), 4: Trigram(4, "震", "☳", "木", (1, 0, 0)),
    5: Trigram(5, "巽", "☴", "木", (0, 1, 1)), 6: Trigram(6, "坎", "☵", "水", (0, 1, 0)),
    7: Trigram(7, "艮", "☶", "土", (0, 0, 1)), 8: Trigram(8, "坤", "☷", "土", (0, 0, 0)),
}
_BY_LINES = {t.lines: t for t in TRIGRAMS.values()}
_MOVING_NAMES = {1: "初爻", 2: "二爻", 3: "三爻", 4: "四爻", 5: "五爻", 6: "上爻"}
_WUXING = {
    "金": {"金": "比和", "木": "体克用", "水": "体生用", "火": "用克体", "土": "用生体"},
    "木": {"木": "比和", "土": "体克用", "火": "体生用", "金": "用克体", "水": "用生体"},
    "水": {"水": "比和", "火": "体克用", "木": "体生用", "土": "用克体", "金": "用生体"},
    "火": {"火": "比和", "金": "体克用", "土": "体生用", "水": "用克体", "木": "用生体"},
    "土": {"土": "比和", "水": "体克用", "金": "体生用", "木": "用克体", "火": "用生体"},
}

def _calc(topic: str, t: datetime, numbers: list[int] | None = None) -> dict[str, Any]:
    if numbers and len(numbers) >= 3:
        up_idx = numbers[0] % 8 or 8
        lo_idx = numbers[1] % 8 or 8
        mv = numbers[2] % 6 or 6
    else:
        y, m, d, h = t.year, t.month, t.day, t.hour
        up_idx = (y + m + d) % 8 or 8
        lo_idx = (y + m + d + h) % 8 or 8
        mv = (y + m + d + h) % 6 or 6
    up, lo = TRIGRAMS[up_idx], TRIGRAMS[lo_idx]
    base = list(lo.lines + up.lines)
    hu_lo = _BY_LINES[tuple(base[1:4])]; hu_up = _BY_LINES[tuple(base[2:5])]
    chg = base.copy(); chg[mv - 1] = 1 - chg[mv - 1]
    chg_lo = _BY_LINES[tuple(chg[:3])]; chg_up = _BY_LINES[tuple(chg[3:])]
    ti = up if mv > 3 else lo; yong = lo if mv > 3 else up
    return {
        "upper_trigram": up.name, "lower_trigram": lo.name,
        "base_gua": f"上{up.name}下{lo.name}", "mutual_gua": f"上{hu_up.name}下{hu_lo.name}",
        "changed_gua": f"上{chg_up.name}下{chg_lo.name}",
        "moving_line": mv, "moving_line_name": _MOVING_NAMES[mv],
        "ti_gua": ti.name, "yong_gua": yong.name,
        "relation": _WUXING.get(ti.element, {}).get(yong.element, "比和"),
        "occurred_at": t.isoformat(),
    }

@register("meihua")
def calculate_meihua_engine(req: ChartRequest) -> ChartResult:
    now = datetime.now()
    numbers = req.extra.get("numbers") if req.extra else None
    data = _calc(topic=req.question or "综合", t=now, numbers=numbers)
    text = (
        f"本卦: {data['base_gua']}, 互卦: {data['mutual_gua']}, "
        f"变卦: {data['changed_gua']}, 动爻: {data['moving_line_name']}, "
        f"体卦: {data['ti_gua']}, 用卦: {data['yong_gua']}, 关系: {data['relation']}"
    )
    return ChartResult(
        chart_id=f"ch_{uuid.uuid4().hex[:12]}",
        system="meihua", raw_data=data, text_summary=text,
    )
