"""八字合婚引擎 — 双人八字对比分析"""
from __future__ import annotations
import uuid
from typing import Any
from app.common.utils import TIME_MAP, parse_shichen
from app.engine.registry import ChartRequest, ChartResult, register
from app.lunar import Lunar, Solar

# 天干五行
GAN_WUXING = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土", "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"}
# 地支五行
ZHI_WUXING = {"子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火", "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水"}
# 五行相生
SHENG = {("木", "火"), ("火", "土"), ("土", "金"), ("金", "水"), ("水", "木")}
# 五行相克
KE = {("木", "土"), ("土", "水"), ("水", "火"), ("火", "金"), ("金", "木")}
# 天干五合
GAN_HE = {frozenset({"甲", "己"}), frozenset({"乙", "庚"}), frozenset({"丙", "辛"}), frozenset({"丁", "壬"}), frozenset({"戊", "癸"})}
# 地支六合
ZHI_LIUHE = {frozenset({"子", "丑"}), frozenset({"寅", "亥"}), frozenset({"卯", "戌"}), frozenset({"辰", "酉"}), frozenset({"巳", "申"}), frozenset({"午", "未"})}
# 地支三合局
ZHI_SANHE = [{"寅", "午", "戌"}, {"申", "子", "辰"}, {"巳", "酉", "丑"}, {"亥", "卯", "未"}]
# 地支六冲
ZHI_CHONG = {frozenset({"子", "午"}), frozenset({"丑", "未"}), frozenset({"寅", "申"}), frozenset({"卯", "酉"}), frozenset({"辰", "戌"}), frozenset({"巳", "亥"})}
# 地支相害
ZHI_HAI = {frozenset({"子", "未"}), frozenset({"丑", "午"}), frozenset({"寅", "巳"}), frozenset({"卯", "辰"}), frozenset({"申", "亥"}), frozenset({"酉", "戌"})}
# 地支相刑
ZHI_XING = {frozenset({"寅", "巳"}), frozenset({"巳", "申"}), frozenset({"丑", "戌"}), frozenset({"戌", "未"}), frozenset({"子", "卯"})}

# 纳音婚配表（年柱纳音五行）
NAYIN_COMPAT = {
    ("金", "金"): ("中", "比和，金金相交宜谨慎"),
    ("金", "木"): ("凶", "金克木，有克制之虑"),
    ("金", "水"): ("吉", "金生水，相生相旺"),
    ("金", "火"): ("凶", "火克金，相克不利"),
    ("金", "土"): ("吉", "土生金，财运亨通"),
    ("木", "木"): ("中", "比和，需互相包容"),
    ("木", "水"): ("吉", "水生木，相生有情"),
    ("木", "火"): ("吉", "木生火，热情和睦"),
    ("木", "土"): ("凶", "木克土，主导欲强"),
    ("火", "火"): ("中", "比和，烈火相逢需克制"),
    ("火", "水"): ("凶", "水克火，矛盾较多"),
    ("火", "土"): ("吉", "火生土，温馨和谐"),
    ("水", "水"): ("中", "比和，流动不安"),
    ("水", "土"): ("凶", "土克水，压抑束缚"),
    ("土", "土"): ("中", "比和，稳重但固执"),
}


def _get_bazi(birth_date: str, birth_time: str, gender: str):
    parts = birth_date.split("-")
    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
    time_idx = parse_shichen(birth_time) or 6
    hour, minute = TIME_MAP.get(time_idx, (11, 30))
    solar = Solar.fromYmdHms(year, month, day, hour, minute, 0)
    lunar = solar.getLunar()
    ba_zi = lunar.getEightChar()
    ba_zi.setSect(1)
    return ba_zi, lunar


def _extract_info(ba_zi, lunar) -> dict:
    gz = {"year": ba_zi.getYear(), "month": ba_zi.getMonth(), "day": ba_zi.getDay(), "hour": ba_zi.getTime()}
    gans = {k: v[0] for k, v in gz.items()}
    zhis = {k: v[1] for k, v in gz.items()}
    return {
        "gan_zhi": gz,
        "gans": gans,
        "zhis": zhis,
        "year_nayin": ba_zi.getYearNaYin(),
        "day_gan": gz["day"][0],
        "day_zhi": gz["day"][1],
        "zodiac": lunar.getYearShengXiao(),
    }


def _analyze(a: dict, b: dict) -> dict[str, Any]:
    score = 60  # 基础分
    details = []

    # 1) 日干五合
    day_pair = frozenset({a["day_gan"], b["day_gan"]})
    if day_pair in GAN_HE:
        score += 15
        details.append(("大吉", f"日干天合：{a['day_gan']}与{b['day_gan']}天干五合，夫妻缘分深厚"))
    else:
        wx_a = GAN_WUXING[a["day_gan"]]
        wx_b = GAN_WUXING[b["day_gan"]]
        if (wx_a, wx_b) in SHENG or (wx_b, wx_a) in SHENG:
            score += 8
            details.append(("吉", f"日干相生：{a['day_gan']}({wx_a})与{b['day_gan']}({wx_b})五行相生"))
        elif (wx_a, wx_b) in KE or (wx_b, wx_a) in KE:
            score -= 5
            details.append(("注意", f"日干相克：{a['day_gan']}({wx_a})与{b['day_gan']}({wx_b})五行相克"))

    # 2) 日支六合
    zhi_pair = frozenset({a["day_zhi"], b["day_zhi"]})
    if zhi_pair in ZHI_LIUHE:
        score += 12
        details.append(("大吉", f"日支六合：{a['day_zhi']}与{b['day_zhi']}六合，感情默契"))
    elif zhi_pair in ZHI_CHONG:
        score -= 10
        details.append(("凶", f"日支六冲：{a['day_zhi']}与{b['day_zhi']}相冲，易起争端"))
    elif zhi_pair in ZHI_HAI:
        score -= 5
        details.append(("注意", f"日支相害：{a['day_zhi']}与{b['day_zhi']}相害，需多包容"))
    elif zhi_pair in ZHI_XING:
        score -= 3
        details.append(("注意", f"日支相刑：{a['day_zhi']}与{b['day_zhi']}相刑，小有摩擦"))

    # 3) 年柱纳音配对
    ny_a = a["year_nayin"][:1] if a["year_nayin"] else ""
    ny_b = b["year_nayin"][:1] if b["year_nayin"] else ""
    # 取纳音五行（纳音的最后一个字即五行）
    wx_ny_a = a["year_nayin"][-1] if a["year_nayin"] else ""
    wx_ny_b = b["year_nayin"][-1] if b["year_nayin"] else ""
    compat = NAYIN_COMPAT.get((wx_ny_a, wx_ny_b)) or NAYIN_COMPAT.get((wx_ny_b, wx_ny_a))
    if compat:
        level, desc = compat
        if level == "吉":
            score += 8
        elif level == "凶":
            score -= 5
        details.append((level, f"年柱纳音：{a['year_nayin']}与{b['year_nayin']}，{desc}"))

    # 4) 四柱地支合冲统计
    all_zhis_a = list(a["zhis"].values())
    all_zhis_b = list(b["zhis"].values())
    he_count = 0
    chong_count = 0
    for za in all_zhis_a:
        for zb in all_zhis_b:
            if frozenset({za, zb}) in ZHI_LIUHE:
                he_count += 1
            if frozenset({za, zb}) in ZHI_CHONG:
                chong_count += 1
    if he_count > 1:
        score += he_count * 3
        details.append(("吉", f"四柱地支六合{he_count}组，感情基础好"))
    if chong_count > 1:
        score -= chong_count * 3
        details.append(("注意", f"四柱地支六冲{chong_count}组，需注意化解"))

    # 5) 生肖配对
    details.append(("参考", f"生肖：{a['zodiac']}配{b['zodiac']}"))

    score = max(0, min(100, score))
    return {"score": score, "details": details}


@register("hehun")
def calculate_hehun(req: ChartRequest) -> ChartResult:
    # 主方（req 本身），配偶信息在 extra 中
    extra = req.extra
    spouse_date = extra.get("spouse_birth_date", "")
    spouse_time = extra.get("spouse_birth_time", "6")
    spouse_gender = extra.get("spouse_gender", "女")
    if not spouse_date:
        from app.common.exceptions import BusinessError
        raise BusinessError("请在 extra 中提供配偶信息：spouse_birth_date, spouse_birth_time, spouse_gender")

    bazi_a, lunar_a = _get_bazi(req.birth_date, req.birth_time, req.gender)
    bazi_b, lunar_b = _get_bazi(spouse_date, spouse_time, spouse_gender)

    info_a = _extract_info(bazi_a, lunar_a)
    info_b = _extract_info(bazi_b, lunar_b)
    analysis = _analyze(info_a, info_b)

    data = {
        "person_a": {**info_a, "birth_date": req.birth_date, "gender": req.gender},
        "person_b": {**info_b, "birth_date": spouse_date, "gender": spouse_gender},
        "score": analysis["score"],
        "details": analysis["details"],
    }
    text = _build_text(data)
    return ChartResult(
        chart_id=f"ch_{uuid.uuid4().hex[:12]}",
        system="hehun", raw_data=data, text_summary=text,
    )


def _build_text(d: dict[str, Any]) -> str:
    a, b = d["person_a"], d["person_b"]
    lines = [
        "══════════ 八字合婚 ══════════",
        f"甲方：{a['birth_date']} {a['gender']}  四柱：{' '.join(a['gan_zhi'].values())}  属{a['zodiac']}",
        f"乙方：{b['birth_date']} {b['gender']}  四柱：{' '.join(b['gan_zhi'].values())}  属{b['zodiac']}",
        "",
        f"合婚评分：{d['score']} 分",
        "",
        "──── 详细分析 ────",
    ]
    for level, desc in d["details"]:
        lines.append(f"  [{level}] {desc}")
    return "\n".join(lines)
