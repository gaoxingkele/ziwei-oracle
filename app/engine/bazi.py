from __future__ import annotations
import uuid
from typing import Any
from app.common.utils import TIME_MAP, parse_shichen
from app.engine.registry import ChartRequest, ChartResult, register

try:
    from lunar_python import Lunar, Solar
except ImportError:
    Lunar = None
    Solar = None

@register("bazi")
def calculate_bazi_engine(req: ChartRequest) -> ChartResult:
    if Lunar is None:
        raise RuntimeError("请先安装 lunar_python: pip install lunar_python")
    parts = req.birth_date.split("-")
    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
    time_idx = parse_shichen(req.birth_time) or 6
    hour, minute = TIME_MAP.get(time_idx, (11, 30))
    solar = Solar.fromYmdHms(year, month, day, hour, minute, 0)
    lunar = solar.getLunar()
    ba_zi = lunar.getEightChar()
    data: dict[str, Any] = {
        "year_pillar": ba_zi.getYear(),
        "month_pillar": ba_zi.getMonth(),
        "day_pillar": ba_zi.getDay(),
        "hour_pillar": ba_zi.getTime(),
        "year_gan": ba_zi.getYearGan(),
        "year_zhi": ba_zi.getYearZhi(),
        "day_gan": ba_zi.getDayGan(),
        "day_zhi": ba_zi.getDayZhi(),
        "solar_date": str(solar),
        "lunar_date": str(lunar),
        "zodiac": lunar.getYearShengXiao(),
    }
    text = (
        f"四柱: {data['year_pillar']} {data['month_pillar']} "
        f"{data['day_pillar']} {data['hour_pillar']}\n"
        f"阳历: {data['solar_date']}, 阴历: {data['lunar_date']}\n"
        f"生肖: {data['zodiac']}"
    )
    return ChartResult(
        chart_id=f"ch_{uuid.uuid4().hex[:12]}",
        system="bazi", raw_data=data, text_summary=text,
    )
