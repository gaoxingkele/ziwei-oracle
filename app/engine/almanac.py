from __future__ import annotations
import uuid
from typing import Any
from app.engine.registry import ChartRequest, ChartResult, register
from app.lunar import Solar


@register("almanac")
def calculate_almanac_engine(req: ChartRequest) -> ChartResult:
    date_str = req.birth_date  # 复用 birth_date 字段作查询日期
    parts = date_str.split("-")
    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
    solar = Solar.fromYmd(year, month, day)
    lunar = solar.getLunar()

    # ── 基本日历 ──
    base = {
        "solar_date": str(solar),
        "lunar_date": str(lunar),
        "gan_zhi_year": lunar.getYearInGanZhi(),
        "gan_zhi_month": lunar.getMonthInGanZhi(),
        "gan_zhi_day": lunar.getDayInGanZhi(),
        "na_yin_year": lunar.getYearNaYin(),
        "na_yin_month": lunar.getMonthNaYin(),
        "na_yin_day": lunar.getDayNaYin(),
        "zodiac": lunar.getYearShengXiao(),
    }

    # ── 宜忌 ──
    yi_ji = {
        "yi": lunar.getDayYi(),
        "ji": lunar.getDayJi(),
        "peng_zu_gan": lunar.getPengZuGan(),
        "peng_zu_zhi": lunar.getPengZuZhi(),
    }

    # ── 冲煞 ──
    chong_sha = {
        "chong": lunar.getDayChong(),
        "chong_desc": lunar.getDayChongDesc(),
        "chong_sheng_xiao": lunar.getDayChongShengXiao(),
        "sha": lunar.getDaySha(),
    }

    # ── 吉神凶煞 ──
    shen_sha = {
        "ji_shen": lunar.getDayJiShen(),
        "xiong_sha": lunar.getDayXiongSha(),
        "tian_shen": lunar.getDayTianShen(),
        "tian_shen_type": lunar.getDayTianShenType(),
        "tian_shen_luck": lunar.getDayTianShenLuck(),
    }

    # ── 星宿 ──
    xiu_info = {
        "xiu": lunar.getXiu(),
        "xiu_luck": lunar.getXiuLuck(),
        "xiu_song": lunar.getXiuSong(),
        "zheng": lunar.getZheng(),
        "gong": lunar.getGong(),
        "shou": lunar.getShou(),
    }

    # ── 九星 ──
    nine_star = {
        "day": str(lunar.getDayNineStar()),
        "month": str(lunar.getMonthNineStar()),
        "year": str(lunar.getYearNineStar()),
    }

    # ── 建除十二值星 ──
    zhi_xing = lunar.getZhiXing()

    # ── 方位 ──
    positions = {
        "xi": lunar.getDayPositionXiDesc(),
        "cai": lunar.getDayPositionCaiDesc(),
        "fu": lunar.getDayPositionFuDesc(),
        "yang_gui": lunar.getDayPositionYangGuiDesc(),
        "yin_gui": lunar.getDayPositionYinGuiDesc(),
        "tai_sui": lunar.getDayPositionTaiSuiDesc(),
    }

    # ── 物候 / 六曜 / 月相 / 日禄 / 节气 ──
    misc = {
        "wu_hou": lunar.getWuHou(),
        "hou": lunar.getHou(),
        "liu_yao": lunar.getLiuYao(),
        "yue_xiang": lunar.getYueXiang(),
        "day_lu": lunar.getDayLu(),
    }
    jie_qi = None
    try:
        jq = lunar.getCurrentJieQi()
        if jq is None:
            jq = lunar.getPrevJieQi()
        jie_qi = str(jq) if jq else None
    except Exception:
        pass
    misc["jie_qi"] = jie_qi

    # ── 时辰宜忌 ──
    times = []
    for t in lunar.getTimes():
        times.append({
            "name": str(t),
            "gan_zhi": t.getGanZhi(),
            "yi": t.getYi(),
            "ji": t.getJi(),
            "chong": t.getChong(),
            "chong_desc": t.getChongDesc(),
            "sha": t.getSha(),
            "tian_shen": t.getTianShen(),
            "tian_shen_type": t.getTianShenType(),
            "tian_shen_luck": t.getTianShenLuck(),
            "nine_star": str(t.getNineStar()),
        })

    data: dict[str, Any] = {
        "base": base,
        "yi_ji": yi_ji,
        "chong_sha": chong_sha,
        "shen_sha": shen_sha,
        "xiu": xiu_info,
        "nine_star": nine_star,
        "zhi_xing": zhi_xing,
        "positions": positions,
        "misc": misc,
        "times": times,
    }

    text = _build_text(data)
    return ChartResult(
        chart_id=f"ch_{uuid.uuid4().hex[:12]}",
        system="almanac", raw_data=data, text_summary=text,
    )


def _build_text(d: dict[str, Any]) -> str:
    b = d["base"]
    yj = d["yi_ji"]
    cs = d["chong_sha"]
    ss = d["shen_sha"]
    xi = d["xiu"]
    pos = d["positions"]
    misc = d["misc"]

    lines = [
        "══════════ 黄历 ══════════",
        f"阳历: {b['solar_date']}  阴历: {b['lunar_date']}  生肖: {b['zodiac']}",
        f"干支: {b['gan_zhi_year']}年 {b['gan_zhi_month']}月 {b['gan_zhi_day']}日",
        f"纳音: {b['na_yin_year']} {b['na_yin_month']} {b['na_yin_day']}",
        "",
        f"【宜】{' '.join(yj['yi'])}",
        f"【忌】{' '.join(yj['ji'])}",
        "",
        f"彭祖百忌: {yj['peng_zu_gan']} {yj['peng_zu_zhi']}",
        f"冲: {cs['chong_desc']}({cs['chong_sheng_xiao']})  煞: {cs['sha']}",
        "",
        f"──── 吉神凶煞 ────",
        f"  天神: {ss['tian_shen']}({ss['tian_shen_type']}) {ss['tian_shen_luck']}",
        f"  吉神宜趋: {' '.join(ss['ji_shen'])}",
        f"  凶煞宜忌: {' '.join(ss['xiong_sha'])}",
        "",
        f"──── 星宿 ────",
        f"  {xi['xiu']}宿({xi['xiu_luck']}) {xi['zheng']} {xi['gong']}宫 {xi['shou']}",
        f"  {xi['xiu_song']}",
        "",
        f"值星: {d['zhi_xing']}",
        f"九星: 日{d['nine_star']['day']} 月{d['nine_star']['month']} 年{d['nine_star']['year']}",
        "",
        f"──── 方位 ────",
        f"  喜神: {pos['xi']}  财神: {pos['cai']}  福神: {pos['fu']}",
        f"  阳贵: {pos['yang_gui']}  阴贵: {pos['yin_gui']}",
        f"  太岁: {pos['tai_sui']}",
        "",
        f"──── 其他 ────",
        f"  物候: {misc['wu_hou']}  候: {misc['hou']}",
        f"  六曜: {misc['liu_yao']}  月相: {misc['yue_xiang']}",
        f"  日禄: {misc['day_lu']}",
    ]
    if misc.get("jie_qi"):
        lines.append(f"  节气: {misc['jie_qi']}")

    lines += ["", "──── 时辰宜忌 ────"]
    for t in d["times"]:
        yi_str = ",".join(t["yi"][:3])
        ji_str = ",".join(t["ji"][:3])
        lines.append(f"  {t['gan_zhi']} {t['tian_shen']}({t['tian_shen_luck']}) 宜:{yi_str}… 忌:{ji_str}…")

    return "\n".join(lines)
