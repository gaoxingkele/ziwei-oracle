from __future__ import annotations
import uuid
from typing import Any
from app.common.utils import TIME_MAP, parse_shichen
from app.engine.registry import ChartRequest, ChartResult, register
from app.lunar import Lunar, Solar


@register("bazi")
def calculate_bazi_engine(req: ChartRequest) -> ChartResult:
    parts = req.birth_date.split("-")
    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
    time_idx = parse_shichen(req.birth_time) or 6
    hour, minute = TIME_MAP.get(time_idx, (11, 30))
    solar = Solar.fromYmdHms(year, month, day, hour, minute, 0)
    lunar = solar.getLunar()
    ba_zi = lunar.getEightChar()
    gender_flag = 0 if req.gender.strip().lower() in ("male", "m", "男") else 1
    ba_zi.setSect(1)  # 晚子时区分

    # ── 四柱 + 纳音 + 五行 ──
    pillars = {
        "year": {"gan_zhi": ba_zi.getYear(), "na_yin": ba_zi.getYearNaYin(), "wu_xing": ba_zi.getYearWuXing()},
        "month": {"gan_zhi": ba_zi.getMonth(), "na_yin": ba_zi.getMonthNaYin(), "wu_xing": ba_zi.getMonthWuXing()},
        "day": {"gan_zhi": ba_zi.getDay(), "na_yin": ba_zi.getDayNaYin(), "wu_xing": ba_zi.getDayWuXing()},
        "hour": {"gan_zhi": ba_zi.getTime(), "na_yin": ba_zi.getTimeNaYin(), "wu_xing": ba_zi.getTimeWuXing()},
    }

    # ── 十神 (天干 + 地支) ──
    shi_shen = {
        "year_gan": ba_zi.getYearShiShenGan(),
        "year_zhi": ba_zi.getYearShiShenZhi(),
        "month_gan": ba_zi.getMonthShiShenGan(),
        "month_zhi": ba_zi.getMonthShiShenZhi(),
        "day_zhi": ba_zi.getDayShiShenZhi(),
        "hour_gan": ba_zi.getTimeShiShenGan(),
        "hour_zhi": ba_zi.getTimeShiShenZhi(),
    }

    # ── 藏干 ──
    hide_gan = {
        "year": ba_zi.getYearHideGan(),
        "month": ba_zi.getMonthHideGan(),
        "day": ba_zi.getDayHideGan(),
        "hour": ba_zi.getTimeHideGan(),
    }

    # ── 长生十二宫 (地势) ──
    di_shi = {
        "year": ba_zi.getYearDiShi(),
        "month": ba_zi.getMonthDiShi(),
        "day": ba_zi.getDayDiShi(),
        "hour": ba_zi.getTimeDiShi(),
    }

    # ── 命宫 / 身宫 / 胎元 / 胎息 ──
    gong = {
        "ming_gong": ba_zi.getMingGong(),
        "ming_gong_na_yin": ba_zi.getMingGongNaYin(),
        "shen_gong": ba_zi.getShenGong(),
        "shen_gong_na_yin": ba_zi.getShenGongNaYin(),
        "tai_yuan": ba_zi.getTaiYuan(),
        "tai_yuan_na_yin": ba_zi.getTaiYuanNaYin(),
        "tai_xi": ba_zi.getTaiXi(),
        "tai_xi_na_yin": ba_zi.getTaiXiNaYin(),
    }

    # ── 旬空 ──
    xun_kong = {
        "year_xun": ba_zi.getYearXun(), "year_kong": ba_zi.getYearXunKong(),
        "month_xun": ba_zi.getMonthXun(), "month_kong": ba_zi.getMonthXunKong(),
        "day_xun": ba_zi.getDayXun(), "day_kong": ba_zi.getDayXunKong(),
        "hour_xun": ba_zi.getTimeXun(), "hour_kong": ba_zi.getTimeXunKong(),
    }

    # ── 大运 ──
    yun = ba_zi.getYun(gender_flag)
    da_yun_list = []
    for dy in yun.getDaYun():
        da_yun_list.append({
            "start_age": dy.getStartAge(),
            "end_age": dy.getEndAge(),
            "gan_zhi": dy.getGanZhi(),
            "start_year": dy.getStartYear(),
            "end_year": dy.getEndYear(),
        })

    data: dict[str, Any] = {
        "solar_date": str(solar),
        "lunar_date": str(lunar),
        "zodiac": lunar.getYearShengXiao(),
        "pillars": pillars,
        "shi_shen": shi_shen,
        "hide_gan": hide_gan,
        "di_shi": di_shi,
        "gong": gong,
        "xun_kong": xun_kong,
        "da_yun": {
            "start_desc": f"{yun.getStartYear()}年{yun.getStartMonth()}月{yun.getStartDay()}日起运",
            "steps": da_yun_list,
        },
    }

    text = _build_text(data)
    return ChartResult(
        chart_id=f"ch_{uuid.uuid4().hex[:12]}",
        system="bazi", raw_data=data, text_summary=text,
    )


def _build_text(d: dict[str, Any]) -> str:
    p = d["pillars"]
    lines = [
        "══════════ 八字排盘 ══════════",
        f"阳历: {d['solar_date']}  阴历: {d['lunar_date']}  生肖: {d['zodiac']}",
        "",
        "──── 四柱 ────",
        f"  年柱: {p['year']['gan_zhi']}  [{p['year']['na_yin']}]  {p['year']['wu_xing']}",
        f"  月柱: {p['month']['gan_zhi']}  [{p['month']['na_yin']}]  {p['month']['wu_xing']}",
        f"  日柱: {p['day']['gan_zhi']}  [{p['day']['na_yin']}]  {p['day']['wu_xing']}  ← 日主",
        f"  时柱: {p['hour']['gan_zhi']}  [{p['hour']['na_yin']}]  {p['hour']['wu_xing']}",
    ]

    ss = d["shi_shen"]
    # 日主天干 (日柱第一字) — 用于解读日主强弱
    day_gan_char = p['day']['gan_zhi'][0] if p['day'].get('gan_zhi') else ''
    lines += [
        "",
        "──── 十神 ────",
        f"  年干: {ss['year_gan']}  年支藏: {','.join(ss['year_zhi'])}",
        f"  月干: {ss['month_gan']}  月支藏: {','.join(ss['month_zhi'])}",
        f"  日主: {day_gan_char} (本气)  日支藏: {','.join(ss['day_zhi'])}",
        f"  时干: {ss['hour_gan']}  时支藏: {','.join(ss['hour_zhi'])}",
    ]

    hg = d["hide_gan"]
    lines += [
        "",
        "──── 藏干 ────",
        f"  年支: {','.join(hg['year'])}",
        f"  月支: {','.join(hg['month'])}",
        f"  日支: {','.join(hg['day'])}",
        f"  时支: {','.join(hg['hour'])}",
    ]

    ds = d["di_shi"]
    lines += [
        "",
        "──── 地势(长生十二宫) ────",
        f"  年: {ds['year']}  月: {ds['month']}  日: {ds['day']}  时: {ds['hour']}",
    ]

    g = d["gong"]
    lines += [
        "",
        "──── 命宫 / 身宫 / 胎元 / 胎息 ────",
        f"  命宫: {g['ming_gong']}({g['ming_gong_na_yin']})",
        f"  身宫: {g['shen_gong']}({g['shen_gong_na_yin']})",
        f"  胎元: {g['tai_yuan']}({g['tai_yuan_na_yin']})",
        f"  胎息: {g['tai_xi']}({g['tai_xi_na_yin']})",
    ]

    xk = d["xun_kong"]
    lines += [
        "",
        "──── 旬空 ────",
        f"  年: {xk['year_xun']}旬 空亡{xk['year_kong']}",
        f"  月: {xk['month_xun']}旬 空亡{xk['month_kong']}",
        f"  日: {xk['day_xun']}旬 空亡{xk['day_kong']}",
        f"  时: {xk['hour_xun']}旬 空亡{xk['hour_kong']}",
    ]

    dy_info = d["da_yun"]
    lines += [
        "",
        f"──── 大运 ({dy_info['start_desc']}) ────",
    ]
    for step in dy_info["steps"]:
        if step["gan_zhi"]:
            lines.append(f"  {step['start_age']:>2}岁: {step['gan_zhi']}  ({step['start_year']}-{step['end_year']})")

    return "\n".join(lines)
