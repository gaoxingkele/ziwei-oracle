from __future__ import annotations
from typing import Any

try:
    from lunar_python import Solar
except ImportError:
    Solar = None

def get_almanac_for_date(date_str: str) -> dict[str, Any]:
    if Solar is None:
        raise RuntimeError("请先安装 lunar_python: pip install lunar_python")
    parts = date_str.split("-")
    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
    solar = Solar.fromYmd(year, month, day)
    lunar = solar.getLunar()
    jie_qi = None
    try:
        jie_qi = lunar.getCurrentJieQi()
        if jie_qi is None:
            jie_qi = lunar.getPrevJieQi()
    except Exception:
        pass
    return {
        "solar_date": str(solar),
        "lunar_date": str(lunar),
        "gan_zhi": f"{lunar.getYearInGanZhi()}年 {lunar.getMonthInGanZhi()}月 {lunar.getDayInGanZhi()}日",
        "yi": lunar.getDayYi(),
        "ji": lunar.getDayJi(),
        "zodiac": lunar.getYearShengXiao(),
        "jie_qi": str(jie_qi) if jie_qi else None,
        "peng_zu": lunar.getPengZuGan() + " " + lunar.getPengZuZhi(),
        "chong": lunar.getDayChong(),
        "sha": lunar.getDaySha(),
    }
