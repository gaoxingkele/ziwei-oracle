"""ziwei_period - 紫微流年/流月运限分析。

设计文档：docs/calendar-resolve-design.md §3.3, §5 Phase 2

职责：
- 吃 device_id + expr，内部调 calendar_resolve 切分时段
- 每个时段调 pureziwei.horoscope.calc_horoscope() 拿运限数据
- 返回 LLM 可直接语言化的结构（natal_recap + by_period[流年/大限/小限/流月]）

零新命理算法 - 100% wrapper pureziwei.horoscope.calc_horoscope()。
准确性等级：A（pureziwei 标准实现）。
"""
from __future__ import annotations

from datetime import date
from typing import Any

from app.common.utils import parse_shichen
from app.engine.calendar import resolve_calendar
from app.pureziwei import Astro
from app.pureziwei.horoscope import calc_horoscope


def _item_summary(item: Any) -> dict:
    """把 HoroscopeItemModel 转成精简 dict 便于 LLM 阅读。"""
    if item is None:
        return {}
    out = {
        "palace": item.earthly_branch,
        "stem_branch": f"{item.heavenly_stem}{item.earthly_branch}",
        "palace_index": item.index,
        "mutagen": dict(zip(["禄", "权", "科", "忌"], item.mutagen)) if item.mutagen and len(item.mutagen) >= 4 else {},
    }
    return out


def _yearly_summary(item: Any) -> dict:
    """流年特有 yearly_dec_star 字段。"""
    base = _item_summary(item)
    if item is not None and getattr(item, "yearly_dec_star", None):
        base["jiangqian12_first"] = item.yearly_dec_star.jiangqian12[:1] if item.yearly_dec_star.jiangqian12 else []
        base["suiqian12_first"] = item.yearly_dec_star.suiqian12[:1] if item.yearly_dec_star.suiqian12 else []
    return base


def _age_summary(item: Any) -> dict:
    """小限特有 nominal_age 字段。"""
    base = _item_summary(item)
    if item is not None and hasattr(item, "nominal_age"):
        base["nominal_age"] = item.nominal_age
    return base


def calculate_ziwei_period(
    profile: dict,
    expr: str,
    base_date: str = "",
    granularity: str = "month",
) -> dict[str, Any]:
    """主函数。profile 是 _load_user_profile 返回的 dict（含 birthday/birthtime/sex/...）。"""
    # 1. 校验 profile
    birthday = profile.get("birthday")
    birthtime = profile.get("birthtime")
    sex = profile.get("sex")
    if not birthday or not birthtime or sex is None:
        return {
            "error": "profile_incomplete",
            "hint": f"用户档案不完整：device_id={profile.get('device_id')}，缺生日/时辰/性别。先用 setting API 补齐。",
        }

    gender_cn = "男" if str(sex) in ("1", "男", "male", "M", "m") else "女"
    time_idx = parse_shichen(birthtime)
    if time_idx is None:
        time_idx = 6

    # 2. 用 Astro 排出本命盘 + 拿 _context
    astro = Astro()
    natal_model = astro.by_solar(birthday, time_idx, gender_cn)
    ctx = getattr(natal_model, "_context", None)
    if ctx is None:
        return {"error": "natal_context_missing", "hint": "pureziwei.Astro 未保存 _context；版本不兼容"}

    # 3. natal_recap（命主信息回放）
    natal_recap = {
        "ming_gong": natal_model.earthly_branch_of_soul_palace,
        "shen_gong": natal_model.earthly_branch_of_body_palace,
        "wu_xing_ju": natal_model.five_elements_class,
        "soul_star": natal_model.soul,
        "body_star": natal_model.body,
        "main_stars_in_ming": [
            s.name for p in (natal_model.palaces or [])
            if p.is_body_palace is False and p.heavenly_stem  # 命宫
            for s in (p.major_stars or [])
        ][:4],
    }
    # 命宫主星更精确：根据 palace.name == "命宫" 找
    for p in (natal_model.palaces or []):
        if p.name == "命宫":
            natal_recap["main_stars_in_ming"] = [s.name for s in (p.major_stars or [])]
            break

    # 4. 解析时段 + 切分
    cal = resolve_calendar(expr=expr, base_date=base_date, view="ziwei", granularity=granularity)
    if "error" in cal:
        return cal
    by_period_input = cal.get("by_period", [])
    # year 粒度时 calendar_resolve 不切分，构造一个全程时段供查流年+大限
    if not by_period_input and cal.get("granularity") == "year":
        g = cal["resolved"]["gregorian"]
        by_period_input = [{
            "solar_range": g,
            "lunar_range": cal["resolved"].get("lunar", ""),
            "ganzhi_month": "",
            "lunar_month_idx": 0,
            "is_partial": False,
        }]

    # 5. 循环调 calc_horoscope
    by_period_out: list[dict] = []
    seen_year: set[int] = set()
    for p in by_period_input:
        # 用该农历月范围中点作为 horoscope_date（避开月初/月末边界）
        sr = p.get("solar_range", [])
        if len(sr) != 2:
            continue
        s_start = date.fromisoformat(sr[0])
        s_end = date.fromisoformat(sr[1])
        mid = s_start + (s_end - s_start) / 2
        h_date_str = f"{mid.year}-{mid.month}-{mid.day}"
        try:
            horo = calc_horoscope(
                birth_cal=ctx["birth_cal"],
                birth_gender=ctx["gender"],
                birth_direction=ctx["direction"],
                soul_palace_index=ctx["soul_palace_index"],
                wu_xing_value=ctx["wu_xing_value"],
                palace_stems=ctx["palace_stems"],
                decadals=ctx["decadals"],
                ages_table=ctx["ages_table"],
                horoscope_date=h_date_str,
                horoscope_time_index=0,
            )
        except Exception as e:
            by_period_out.append({
                "solar_range": sr,
                "lunar_range": p.get("lunar_range"),
                "lunar_month_idx": p.get("lunar_month_idx"),
                "ganzhi_month": p.get("ganzhi_month"),
                "error": f"calc_horoscope failed: {e}",
            })
            continue

        item = {
            "solar_range": sr,
            "lunar_range": p.get("lunar_range"),
            "lunar_month_idx": p.get("lunar_month_idx"),
            "ganzhi_month": p.get("ganzhi_month"),
            "yearly": _yearly_summary(horo.yearly),
            "decadal": _item_summary(horo.decadal),
            "yearly_age": _age_summary(horo.age),
            "monthly": _item_summary(horo.monthly),
        }
        by_period_out.append(item)

    return {
        "natal_recap": natal_recap,
        "resolved": cal["resolved"],
        "view": "ziwei",
        "granularity": cal["granularity"],
        "by_period": by_period_out,
    }
