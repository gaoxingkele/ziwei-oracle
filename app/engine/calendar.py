"""calendar_resolve - 自然语言时间表达 → 多视角时间结构。

设计文档：docs/calendar-resolve-design.md (v3 §3.1)

职责：
- 把对话里的"今年下半年""农历三月""明年春节前后"等表达解析成精确公历范围
- 提供给 LLM 的输出包含：公历区间、农历描述、节气表、按视图切分的子时段
- 不做命理判定（流月十神/刑冲合害由 *_period 工具完成）
"""
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from typing import Any

from app.lunar import Solar, Lunar


# ──────────────────────── 解析层 ────────────────────────

_LUNAR_MONTH_MAP = {
    "正": 1, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
    "七": 7, "八": 8, "九": 9, "十": 10, "冬": 11, "腊": 12,
}


def _parse_iso_range(expr: str) -> dict | None:
    """形如 '{"from":"2026-04-25","to":"2026-12-31"}' 的 ISO 区间。"""
    s = expr.strip()
    if not (s.startswith("{") and s.endswith("}")):
        return None
    try:
        d = json.loads(s)
        if "from" in d and "to" in d:
            return {"from": d["from"], "to": d["to"]}
    except json.JSONDecodeError:
        return None
    return None


def _parse_single_date(expr: str) -> date | None:
    """today / YYYY-MM-DD 单点。"""
    s = expr.strip().lower()
    if s in ("today", "今天", "今日"):
        return date.today()
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", s)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def _year_offset(base: date, label: str) -> int:
    """今年 → 0、明年 → 1、后年 → 2、去年 → -1、前年 → -2。"""
    offsets = {"今年": 0, "明年": 1, "后年": 2, "大后年": 3, "去年": -1, "前年": -2}
    return offsets.get(label, 0)


def _resolve_year_anchor(expr: str, base: date) -> tuple[date, date] | None:
    """识别"今年/明年/2025 年" → 该年公历 1/1 ~ 12/31。"""
    for label in ("今年", "明年", "后年", "大后年", "去年", "前年"):
        if label in expr:
            y = base.year + _year_offset(base, label)
            return date(y, 1, 1), date(y, 12, 31)
    m = re.search(r"(\d{4})\s*年", expr)
    if m:
        y = int(m.group(1))
        return date(y, 1, 1), date(y, 12, 31)
    return None


def _resolve_lunar_month(expr: str, base: date) -> tuple[date, date] | None:
    """识别"农历三月""农历正月""农历五月初五"等。"""
    m = re.search(r"农历([正一二三四五六七八九十冬腊])月(?:初([一二三四五六七八九十]))?", expr)
    if not m:
        return None
    lm = _LUNAR_MONTH_MAP.get(m.group(1))
    if not lm:
        return None
    # 该农历月对应当前农历年（base 所在的农历年）
    base_solar = Solar.fromYmd(base.year, base.month, base.day)
    base_lunar = base_solar.getLunar()
    ly = base_lunar.getYear()
    # 找该农历月初一公历日期
    try:
        lunar_start = Lunar.fromYmd(ly, lm, 1)
    except Exception:
        # 跨年闰月之类的边界，简化处理：试明年
        try:
            lunar_start = Lunar.fromYmd(ly + 1, lm, 1)
        except Exception:
            return None
    s_start = lunar_start.getSolar()
    start = date(s_start.getYear(), s_start.getMonth(), s_start.getDay())
    # 找下个月初一前一天作为月末
    next_lm = lm + 1 if lm < 12 else 1
    next_ly = ly if lm < 12 else ly + 1
    try:
        lunar_end_next = Lunar.fromYmd(next_ly, next_lm, 1)
        s_next = lunar_end_next.getSolar()
        end = date(s_next.getYear(), s_next.getMonth(), s_next.getDay()) - timedelta(days=1)
    except Exception:
        end = start + timedelta(days=29)  # 兜底：30 天

    # 若指明"初X"日，缩到单日
    if m.group(2):
        day_map = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
                   "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
        d = day_map.get(m.group(2))
        if d:
            try:
                lunar_day = Lunar.fromYmd(ly, lm, d)
                s_day = lunar_day.getSolar()
                d_day = date(s_day.getYear(), s_day.getMonth(), s_day.getDay())
                return d_day, d_day
            except Exception:
                pass
    return start, end


def _apply_range_modifier(
    expr: str, anchor: tuple[date, date], base: date
) -> tuple[date, date]:
    """在 anchor (year_start, year_end) 上应用"上半年/下半年/接下来/未来 N 个月"等限定符。"""
    y_start, y_end = anchor

    if "上半年" in expr:
        return date(y_start.year, 1, 1), date(y_start.year, 6, 30)
    if "下半年" in expr:
        return date(y_start.year, 7, 1), date(y_start.year, 12, 31)
    if "接下来" in expr or "今后" in expr:
        # 取 max(base, y_start)
        s = base if base >= y_start else y_start
        return s, y_end
    m = re.search(r"未来\s*(\d+)\s*个?月", expr)
    if m:
        n = int(m.group(1))
        return base, base + timedelta(days=30 * n)
    m = re.search(r"前\s*(\d+)\s*个?月", expr)
    if m:
        n = int(m.group(1))
        return base - timedelta(days=30 * n), base
    m = re.search(r"过去\s*(\d+)\s*个?月", expr)
    if m:
        n = int(m.group(1))
        return base - timedelta(days=30 * n), base
    if "下个月" in expr:
        # base 的下一个公历月
        ny = base.year + (1 if base.month == 12 else 0)
        nm = 1 if base.month == 12 else base.month + 1
        from calendar import monthrange
        return date(ny, nm, 1), date(ny, nm, monthrange(ny, nm)[1])
    if "上个月" in expr:
        py = base.year - (1 if base.month == 1 else 0)
        pm = 12 if base.month == 1 else base.month - 1
        from calendar import monthrange
        return date(py, pm, 1), date(py, pm, monthrange(py, pm)[1])
    if "本月" in expr or "这个月" in expr:
        from calendar import monthrange
        return date(base.year, base.month, 1), date(base.year, base.month, monthrange(base.year, base.month)[1])
    return anchor


def _parse_solar_month_range(expr: str, base: date) -> tuple[date, date] | None:
    """识别"2026 年 5 月到 8 月""5 月到 8 月"等。"""
    m = re.search(r"(?:(\d{4})\s*年)?\s*(\d{1,2})\s*月(?:到|至|~)\s*(\d{1,2})\s*月", expr)
    if not m:
        return None
    y = int(m.group(1)) if m.group(1) else base.year
    sm = int(m.group(2))
    em = int(m.group(3))
    from calendar import monthrange
    return date(y, sm, 1), date(y, em, monthrange(y, em)[1])


def _parse_natural(expr: str, base: date) -> tuple[tuple[date, date], str]:
    """两段式自然语言解析。返回 ((start, end), ambiguity_note)。"""
    note = ""

    # 单点优先
    single = _parse_single_date(expr)
    if single:
        return (single, single), note

    # "X月到Y月" 公历区间
    rng = _parse_solar_month_range(expr, base)
    if rng:
        return rng, "公历自然月区间，按公历切分"

    # 农历月
    lm = _resolve_lunar_month(expr, base)
    if lm:
        return lm, ""

    # 年锚点
    anchor = _resolve_year_anchor(expr, base)
    if anchor is None:
        # 无年锚但可能有限定符（"下个月""未来12个月"等）
        anchor = (date(base.year, 1, 1), date(base.year, 12, 31))

    # 限定符叠加
    result = _apply_range_modifier(expr, anchor, base)

    # 歧义提示
    if "明年" in expr or "今年" in expr or re.search(r"\d{4}\s*年", expr):
        if "下半年" not in expr and "上半年" not in expr and result == anchor:
            note = "默认按公历年（1/1~12/31）解析；如需按命理年（立春到次年立春），请明确告知。"

    return result, note


# ──────────────────────── 切分层 ────────────────────────

_JIE_NAMES = ("立春", "惊蛰", "清明", "立夏", "芒种", "小暑",
              "立秋", "白露", "寒露", "立冬", "大雪", "小寒")


def _all_jie_in_years(y_start: int, y_end: int) -> list[tuple[date, str]]:
    """枚举 [y_start - 1, y_end + 1] 范围内所有"节"的日期，按时间排序。
    扩展 ±1 年是为了让 start 之前/end 之后的节气都能作为切分边界。"""
    out: list[tuple[date, str]] = []
    seen: set[str] = set()
    for y in range(y_start - 1, y_end + 2):
        s = Solar.fromYmd(y, 6, 15)  # 取年中查表，避开年初年末扰动
        lu = s.getLunar()
        jq_table = lu.getJieQiTable()
        for name, sd in jq_table.items():
            if not isinstance(name, str) or name not in _JIE_NAMES:
                continue
            d_jq = date(sd.getYear(), sd.getMonth(), sd.getDay())
            key = f"{name}_{d_jq.isoformat()}"
            if key in seen:
                continue
            seen.add(key)
            out.append((d_jq, name))
    out.sort()
    return out


def _by_period_bazi(start: date, end: date) -> list[dict]:
    """按节气月柱切分。每个流月起点是节，终点是下一个节前一天。"""
    jies = _all_jie_in_years(start.year, end.year)
    if not jies:
        return []
    periods: list[dict] = []
    # 找第一个 <= start 的节作为起始月
    n = len(jies)
    i = 0
    while i + 1 < n and jies[i + 1][0] <= start:
        i += 1
    while i < n - 1 and jies[i][0] <= end:
        jie_d, _jie_name = jies[i]
        next_jie_d = jies[i + 1][0]
        period_start_raw = jie_d
        period_end_raw = next_jie_d - timedelta(days=1)
        period_start = max(period_start_raw, start)
        period_end = min(period_end_raw, end)
        if period_start > period_end:
            i += 1
            continue
        # 流月干支：用月内任一日中午（避开节气边界）
        mid = period_start + timedelta(days=(period_end - period_start).days // 2)
        ec_solar = Solar.fromYmdHms(mid.year, mid.month, mid.day, 12, 0, 0)
        ec = ec_solar.getLunar().getEightChar()
        periods.append({
            "solar_range": [period_start.isoformat(), period_end.isoformat()],
            "lunar_range": _lunar_range_str(period_start, period_end),
            "ganzhi_month": ec.getMonth(),
            "lunar_month_idx": _lunar_month_idx(period_start),
            "is_partial": (period_start > period_start_raw) or (period_end < period_end_raw),
        })
        i += 1
    return periods


def _by_period_ziwei(start: date, end: date) -> list[dict]:
    """按农历月切分（初一→晦日为一月）。"""
    periods = []
    cur = start
    while cur <= end:
        cur_solar = Solar.fromYmd(cur.year, cur.month, cur.day)
        cur_lunar = cur_solar.getLunar()
        ly, lm = cur_lunar.getYear(), cur_lunar.getMonth()
        # 该农历月初一与下月初一
        try:
            lm_start = Lunar.fromYmd(ly, abs(lm), 1)
        except Exception:
            cur = cur + timedelta(days=30)
            continue
        s_start = lm_start.getSolar()
        period_start_raw = date(s_start.getYear(), s_start.getMonth(), s_start.getDay())
        period_start = max(period_start_raw, start)

        nlm = abs(lm) + 1 if abs(lm) < 12 else 1
        nly = ly if abs(lm) < 12 else ly + 1
        try:
            lm_next = Lunar.fromYmd(nly, nlm, 1)
            s_next = lm_next.getSolar()
            period_end_raw = date(s_next.getYear(), s_next.getMonth(), s_next.getDay()) - timedelta(days=1)
        except Exception:
            period_end_raw = period_start_raw + timedelta(days=29)
        period_end = min(period_end_raw, end)

        # 干支按月初节气取（与 bazi 对齐）
        ec_solar = Solar.fromYmdHms(period_start.year, period_start.month, period_start.day, 12, 0, 0)
        ec_lunar = ec_solar.getLunar()
        ec = ec_lunar.getEightChar()

        periods.append({
            "solar_range": [period_start.isoformat(), period_end.isoformat()],
            "lunar_range": _lunar_range_str(period_start, period_end),
            "ganzhi_month": ec.getMonth(),
            "lunar_month_idx": abs(lm),
            "is_partial": (period_start > period_start_raw) or (period_end < period_end_raw),
        })
        cur = period_end + timedelta(days=1)
        if cur > end:
            break
    return periods


def _by_period_astrology(start: date, end: date) -> list[dict]:
    """按公历自然月切分。"""
    from calendar import monthrange
    periods = []
    y, m = start.year, start.month
    while True:
        ms = date(y, m, 1)
        me = date(y, m, monthrange(y, m)[1])
        period_start = max(ms, start)
        period_end = min(me, end)
        periods.append({
            "solar_range": [period_start.isoformat(), period_end.isoformat()],
            "lunar_range": _lunar_range_str(period_start, period_end),
            "ganzhi_month": "",  # 占星不强调月柱
            "lunar_month_idx": 0,
            "is_partial": (period_start > ms) or (period_end < me),
        })
        if period_end >= end:
            break
        if m == 12:
            y += 1
            m = 1
        else:
            m += 1
    return periods


# ──────────────────────── 辅助 ────────────────────────

def _lunar_range_str(start: date, end: date) -> str:
    s_lunar = Solar.fromYmd(start.year, start.month, start.day).getLunar()
    e_lunar = Solar.fromYmd(end.year, end.month, end.day).getLunar()
    s_str = f"{s_lunar.getMonthInChinese()}月{s_lunar.getDayInChinese()}"
    e_str = f"{e_lunar.getMonthInChinese()}月{e_lunar.getDayInChinese()}"
    return f"{s_str} ~ {e_str}"


def _lunar_month_idx(d: date) -> int:
    """返回该公历日期所在的农历月（1-12，绝对值，不区分闰月）。"""
    return abs(Solar.fromYmd(d.year, d.month, d.day).getLunar().getMonth())


def _jieqi_in_range(start: date, end: date) -> list[dict]:
    """枚举区间内经过的所有节气。getJieQiTable 字典 value 直接是 Solar。"""
    out = []
    cur = start
    while cur <= end:
        lunar = Solar.fromYmd(cur.year, cur.month, cur.day).getLunar()
        jq_table = lunar.getJieQiTable()
        for name, sd in jq_table.items():
            # 跳过 DA_XUE/DONG_ZHI/XIAO_HAN/DA_HAN/LI_CHUN/YU_SHUI/JING_ZHE 等英文键
            # 这些是相邻年份的辅助节气，会导致重复
            if not name or not isinstance(name, str) or any(c.isascii() and c.isalpha() for c in name):
                continue
            d_jq = date(sd.getYear(), sd.getMonth(), sd.getDay())
            if start <= d_jq <= end:
                out.append({
                    "name": name,
                    "datetime": f"{sd.toYmdHms()}",
                })
        # 推进到下一年
        cur = date(cur.year + 1, 1, 1)
    # 去重 + 排序
    seen = set()
    out_sorted = []
    for item in sorted(out, key=lambda x: x["datetime"]):
        key = item["name"] + item["datetime"]
        if key not in seen:
            seen.add(key)
            out_sorted.append(item)
    return out_sorted


# ──────────────────────── 主入口 ────────────────────────

def resolve_calendar(
    expr: str,
    base_date: str = "",
    view: str = "raw",
    granularity: str = "auto",
) -> dict[str, Any]:
    """主函数。详见 docstring（mcp_server.py 注册时挂的 docstring 是给 LLM 看的）。"""
    # base_date 默认今天
    if base_date:
        try:
            parts = base_date.split("-")
            base = date(int(parts[0]), int(parts[1]), int(parts[2]))
        except Exception:
            base = date.today()
    else:
        base = date.today()

    # 1. ISO 直传
    iso = _parse_iso_range(expr)
    if iso:
        try:
            sp = iso["from"].split("-")
            ep = iso["to"].split("-")
            start = date(int(sp[0]), int(sp[1]), int(sp[2]))
            end = date(int(ep[0]), int(ep[1]), int(ep[2]))
            note = ""
        except Exception:
            return {"error": "invalid_iso_range", "hint": f"无法解析: {expr}"}
    else:
        # 2. 自然语言
        try:
            (start, end), note = _parse_natural(expr, base)
        except Exception as e:
            return {"error": "unparseable", "hint": f"表达式无法解析: {expr}（{e}）"}

    if start > end:
        return {"error": "invalid_range", "hint": f"起点晚于终点: {start} > {end}"}

    # 3. resolved 块
    s_lunar = Solar.fromYmd(start.year, start.month, start.day).getLunar()
    e_lunar = Solar.fromYmd(end.year, end.month, end.day).getLunar()
    # ganzhi_year_solar 用范围中点：避免 1/1 起算的范围跨立春时
    # 错把"立春前的旧年干支"当成主流年（如 2026-01-01 ~ 2026-12-31 误返"乙巳"）
    mid_date = start + (end - start) / 2
    mid_lunar = Solar.fromYmd(mid_date.year, mid_date.month, mid_date.day).getLunar()
    resolved = {
        "gregorian": [start.isoformat(), end.isoformat()],
        "lunar": f"{s_lunar.getYearInChinese()}年{s_lunar.getMonthInChinese()}月{s_lunar.getDayInChinese()} ~ {e_lunar.getYearInChinese()}年{e_lunar.getMonthInChinese()}月{e_lunar.getDayInChinese()}",
        "ganzhi_year_solar": mid_lunar.getYearInGanZhiExact(),
        "jieqi_in_range": _jieqi_in_range(start, end),
    }

    # 4. 自动 granularity
    if granularity == "auto":
        days = (end - start).days
        if days <= 1:
            granularity = "day"
        elif days <= 366:
            granularity = "month"
        else:
            granularity = "year"

    # 5. by_period 切分
    by_period: list[dict] = []
    if view == "bazi" and granularity in ("month", "day"):
        by_period = _by_period_bazi(start, end)
    elif view == "ziwei" and granularity in ("month", "day"):
        by_period = _by_period_ziwei(start, end)
    elif view == "astrology" and granularity in ("month", "day"):
        by_period = _by_period_astrology(start, end)

    return {
        "resolved": resolved,
        "view": view,
        "granularity": granularity,
        "by_period": by_period,
        "ambiguity_note": note,
    }
