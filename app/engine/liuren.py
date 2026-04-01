from __future__ import annotations
import uuid
from typing import Any
from app.common.utils import parse_shichen
from app.engine.registry import ChartRequest, ChartResult, register
from app.lunar import Solar

from kinliuren.kinliuren import Liuren

SHICHEN_ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]


@register("liuren")
def calculate_liuren(req: ChartRequest) -> ChartResult:
    parts = req.birth_date.split("-")
    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
    s = Solar.fromYmd(year, month, day)
    lunar = s.getLunar()

    jieqi = lunar.getPrevJie().getName()
    month_zhi = lunar.getMonthZhi()
    day_gangzhi = lunar.getDayInGanZhi()

    time_idx = parse_shichen(req.birth_time)
    if time_idx is None:
        time_idx = 6
    times = lunar.getTimes()
    hour_gangzhi = times[time_idx].getGanZhi()

    guiren_num = int(req.extra.get("guiren", 1))  # 1=昼贵, 2=夜贵

    lr = Liuren(jieqi, month_zhi, day_gangzhi, hour_gangzhi)
    data = lr.result(guiren_num)
    text = _build_text(data)
    return ChartResult(
        chart_id=f"ch_{uuid.uuid4().hex[:12]}",
        system="liuren", raw_data=data, text_summary=text,
    )


def _build_text(d: dict[str, Any]) -> str:
    lines = [
        "----------大六壬----------",
        f"节气：{d.get('節氣', '未知')}",
        f"农历月：{d.get('農曆月', '未知')}",
        f"日期：{d.get('日期', '未知')}",
        f"格局：{d.get('格局', [])}",
        f"日马：{d.get('日馬', '未知')}",
    ]
    sanchuan = d.get("三傳", {})
    if sanchuan:
        lines.append(f"三传：{sanchuan}")
    sike = d.get("四課", {})
    if sike:
        lines.append(f"四课：{sike}")
    tiandi = d.get("天地盤", {})
    if tiandi:
        lines.append(f"天地盘：{tiandi}")
    return "\n".join(lines)
