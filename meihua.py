# 梅花易数起卦（内置公式，与文档一致）
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Trigram:
    idx: int
    name: str
    symbol: str
    element: str
    lines: tuple[int, int, int]  # 下->上


TRIGRAMS: dict[int, Trigram] = {
    1: Trigram(1, "乾", "☰", "金", (1, 1, 1)),
    2: Trigram(2, "兑", "☱", "金", (1, 1, 0)),
    3: Trigram(3, "离", "☲", "火", (1, 0, 1)),
    4: Trigram(4, "震", "☳", "木", (1, 0, 0)),
    5: Trigram(5, "巽", "☴", "木", (0, 1, 1)),
    6: Trigram(6, "坎", "☵", "水", (0, 1, 0)),
    7: Trigram(7, "艮", "☶", "土", (0, 0, 1)),
    8: Trigram(8, "坤", "☷", "土", (0, 0, 0)),
}
TRIGRAM_BY_LINES = {t.lines: t for t in TRIGRAMS.values()}
MOVING_LINE_NAMES = {1: "初爻", 2: "二爻", 3: "三爻", 4: "四爻", 5: "五爻", 6: "上爻"}


def _wuxing_relation(ti_element: str, yong_element: str) -> str:
    relations = {
        "金": {"金": "比和", "木": "体克用", "水": "体生用", "火": "用克体", "土": "用生体"},
        "木": {"木": "比和", "土": "体克用", "火": "体生用", "金": "用克体", "水": "用生体"},
        "水": {"水": "比和", "火": "体克用", "木": "体生用", "土": "用克体", "金": "用生体"},
        "火": {"火": "比和", "金": "体克用", "土": "体生用", "水": "用克体", "木": "用生体"},
        "土": {"土": "比和", "水": "体克用", "金": "体生用", "木": "用克体", "火": "用生体"},
    }
    return relations.get(ti_element, {}).get(yong_element, "比和")


def calculate_meihua(topic: str, occurred_at: datetime) -> dict[str, Any]:
    """时间起卦：上卦=(年+月+日)%8，下卦=(年+月+日+时)%8，动爻=(年+月+日+时)%6。"""
    year = occurred_at.year
    month = occurred_at.month
    day = occurred_at.day
    hour = occurred_at.hour
    upper_idx = (year + month + day) % 8 or 8
    lower_idx = (year + month + day + hour) % 8 or 8
    moving_line = (year + month + day + hour) % 6 or 6
    upper = TRIGRAMS[upper_idx]
    lower = TRIGRAMS[lower_idx]
    base_lines = list(lower.lines + upper.lines)
    hu_lower = TRIGRAM_BY_LINES[tuple(base_lines[1:4])]
    hu_upper = TRIGRAM_BY_LINES[tuple(base_lines[2:5])]
    changed_lines = base_lines.copy()
    changed_lines[moving_line - 1] = 1 - changed_lines[moving_line - 1]
    changed_lower = TRIGRAM_BY_LINES[tuple(changed_lines[:3])]
    changed_upper = TRIGRAM_BY_LINES[tuple(changed_lines[3:])]
    is_upper_moving = moving_line > 3
    ti = upper if is_upper_moving else lower
    yong = lower if is_upper_moving else upper
    line_text = lambda lines: "".join("阳" if x == 1 else "阴" for x in lines)
    return {
        "upper_trigram": upper.name,
        "lower_trigram": lower.name,
        "base_gua": f"上{upper.name}下{lower.name}",
        "mutual_gua": f"上{hu_upper.name}下{hu_lower.name}",
        "changed_gua": f"上{changed_upper.name}下{changed_lower.name}",
        "moving_line": moving_line,
        "moving_line_name": MOVING_LINE_NAMES[moving_line],
        "base_line_pattern": line_text(base_lines),
        "changed_line_pattern": line_text(changed_lines),
        "ti_gua": ti.name,
        "yong_gua": yong.name,
        "relation": _wuxing_relation(ti.element, yong.element),
        "occurred_at": occurred_at.isoformat(),
    }
