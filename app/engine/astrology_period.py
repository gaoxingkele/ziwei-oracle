"""astrology_period - 占星时段（基础版）。

设计文档：docs/calendar-resolve-design.md §3.4, §5 Phase 4

本期仅返回：
- natal_recap：本命主要行星位置（kerykeion 现成）
- by_period：公历自然月切分（calendar_resolve 现成）

不做（留待后续升级）：
- transit aspects（运势行星 vs 本命行星相位）
- ingress（行星进入新星座）
- retrograde（逆行扫描）

scope_note 字段会自我提示 LLM 不要编造具体 transit 日期。
"""
from __future__ import annotations

from typing import Any

from app.common.utils import parse_shichen, TIME_MAP
from app.config import ASTRO_CITY, ASTRO_NATION, ASTRO_LNG, ASTRO_LAT, ASTRO_TZ_STR
from app.engine.calendar import resolve_calendar

try:
    from kerykeion import AstrologicalSubjectFactory
except ImportError:
    AstrologicalSubjectFactory = None


_PLANET_LABELS = [
    ("sun", "太阳"),
    ("moon", "月亮"),
    ("ascendant", "上升"),
    ("mercury", "水星"),
    ("venus", "金星"),
    ("mars", "火星"),
    ("jupiter", "木星"),
    ("saturn", "土星"),
]


def _planet_dict(subject, attr: str, label: str) -> dict | None:
    p = getattr(subject, attr, None)
    if p is None:
        return None
    out = {"label": label, "sign": getattr(p, "sign", "") or ""}
    pos = getattr(p, "position", None)
    if isinstance(pos, (int, float)):
        out["degree"] = round(float(pos), 2)
    house = getattr(p, "house", "")
    if house:
        out["house"] = house
    return out


def calculate_astrology_period(
    profile: dict,
    expr: str,
    base_date: str = "",
    granularity: str = "month",
) -> dict[str, Any]:
    """主函数。基础版：natal_recap + 公历月切分。"""
    if AstrologicalSubjectFactory is None:
        return {"error": "kerykeion_missing", "hint": "请安装 kerykeion: pip install kerykeion"}

    birthday = profile.get("birthday")
    birthtime = profile.get("birthtime")
    if not birthday or not birthtime:
        return {
            "error": "profile_incomplete",
            "hint": f"用户档案不完整：device_id={profile.get('device_id')}，缺生日/时辰。",
        }

    parts = birthday.split("-")
    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
    time_idx = parse_shichen(birthtime) or 6
    hour, minute = TIME_MAP.get(time_idx, (11, 30))

    city = profile.get("city") or ASTRO_CITY
    name = profile.get("name") or "user"

    # 本命盘
    try:
        subject = AstrologicalSubjectFactory.from_birth_data(
            name=name, year=year, month=month, day=day,
            hour=hour, minute=minute,
            city=city, nation=ASTRO_NATION,
            lng=ASTRO_LNG, lat=ASTRO_LAT, tz_str=ASTRO_TZ_STR, online=False,
        )
    except Exception as e:
        return {"error": "natal_chart_failed", "hint": f"本命盘生成失败: {e}"}

    natal_recap = {}
    for attr, label in _PLANET_LABELS:
        d = _planet_dict(subject, attr, label)
        if d:
            natal_recap[attr] = d

    # 公历切分
    cal = resolve_calendar(expr=expr, base_date=base_date, view="astrology", granularity=granularity)
    if "error" in cal:
        return cal
    by_period_input = cal.get("by_period", [])
    if not by_period_input and cal.get("granularity") == "year":
        g = cal["resolved"]["gregorian"]
        by_period_input = [{
            "solar_range": g,
            "lunar_range": cal["resolved"].get("lunar", ""),
            "is_partial": False,
        }]

    by_period_out = []
    for p in by_period_input:
        sr = p.get("solar_range", [])
        if len(sr) != 2:
            continue
        s_start, s_end = sr
        # 月份标签：取 solar_range[0] 的年月
        y_str, m_str = s_start.split("-")[:2]
        by_period_out.append({
            "solar_range": sr,
            "month_label": f"{int(y_str)} 年 {int(m_str)} 月",
            "is_partial": p.get("is_partial", False),
        })

    return {
        "natal_recap": natal_recap,
        "resolved": cal["resolved"],
        "view": "astrology",
        "granularity": cal["granularity"],
        "by_period": by_period_out,
        "scope_note": (
            "本期占星 period 仅返回时段切分与本命盘；行星行运（transit aspects）/ "
            "进入新星座（ingress）/ 逆行扫描（retrograde）在后续版本提供。"
            "LLM 解读流年时请基于本命盘做轻量通性判断，"
            "**禁止编造具体的 transit 日期、行星相位精确度数、逆行起止时刻**。"
        ),
    }
