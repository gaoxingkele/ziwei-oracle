"""bazi_period - 八字流月分析。

设计文档：docs/calendar-resolve-design.md §3.2, §5 Phase 3

职责：
- 吃 device_id + expr，内部完成"时间解析 → 节气切月 → 流月对命主关系"
- LLM 不参与任何命理判定，所有十神/刑冲合害/五行 delta/用神状态由本工具算

字段来源：
- 流月干支：app/lunar/EightChar/LiuYue（A 级）
- 流月十神：LunarUtil.SHI_SHEN 查表（A 级）
- 刑冲合害：LunarUtil.CHONG/HE_ZHI_6 + 本文件三合/三会/三刑/六害规则表（A 级标准）
- 五行 delta：WU_XING_GAN/ZHI 计数（A 级）
- yong_shen_status：用神五行 vs 流月五行强弱（B 级，参考性）
"""
from __future__ import annotations

from datetime import date
from typing import Any

from app.common.utils import parse_shichen, TIME_MAP
from app.engine.calendar import resolve_calendar
from app.lunar import Solar
from app.lunar.util import LunarUtil


# ──────────────────────── 命理规则表 ────────────────────────

# 三合：每组 3 个地支（半合 = 任两个）
SAN_HE = {
    ("申", "子", "辰"): "水局",
    ("巳", "酉", "丑"): "金局",
    ("寅", "午", "戌"): "火局",
    ("亥", "卯", "未"): "木局",
}

# 三会：东方木/南方火/西方金/北方水
SAN_HUI = {
    ("寅", "卯", "辰"): "东方木",
    ("巳", "午", "未"): "南方火",
    ("申", "酉", "戌"): "西方金",
    ("亥", "子", "丑"): "北方水",
}

# 三刑：恃势/无恩/无礼/自刑
SAN_XING_GROUPS = [
    (("寅", "巳", "申"), "恃势之刑"),
    (("丑", "戌", "未"), "无恩之刑"),
]
LIANG_XING = [
    (("子", "卯"), "无礼之刑"),
]
ZI_XING = ["辰", "午", "酉", "亥"]

# 六害
LIU_HAI = {
    frozenset(["子", "未"]): "子未相害",
    frozenset(["丑", "午"]): "丑午相害",
    frozenset(["寅", "巳"]): "寅巳相害",
    frozenset(["卯", "辰"]): "卯辰相害",
    frozenset(["申", "亥"]): "申亥相害",
    frozenset(["酉", "戌"]): "酉戌相害",
}

# 五行相生/相克（用于 yong_shen_status 判定）
SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}


# ──────────────────────── 命理算法 ────────────────────────

def _chong_target(zhi: str) -> str:
    """获取与 zhi 相冲的地支。"""
    idx = LunarUtil.ZHI.index(zhi)
    return LunarUtil.CHONG[idx - 1]


def _he_zhi_target(zhi: str) -> str:
    """获取与 zhi 六合的地支。"""
    idx = LunarUtil.ZHI.index(zhi)
    return LunarUtil.HE_ZHI_6[idx - 1]


def _shi_shen(day_gan: str, target_gan: str) -> str:
    """日干为参照，target_gan 对日干的十神。"""
    return LunarUtil.SHI_SHEN.get(day_gan + target_gan, "")


def _hide_gan_shi_shen(day_gan: str, zhi: str) -> list[str]:
    """藏干十神（藏干主气+余气+杂气）。"""
    hide = LunarUtil.ZHI_HIDE_GAN.get(zhi, [])
    return [LunarUtil.SHI_SHEN.get(day_gan + g, "") for g in hide if g]


def _interactions(liu_zhi: str, natal_zhi_list: list[tuple[str, str]]) -> list[dict]:
    """流月地支 vs 原局四地支的关系。
    natal_zhi_list: [(target_label, zhi), ...] 如 [("year_zhi", "亥"), ("month_zhi", "卯"), ...]
    返回每条关系的 dict：{"target": label(zhi), "relation": "..."}.
    """
    out: list[dict] = []
    for label, nz in natal_zhi_list:
        if not nz:
            continue
        rel = []
        # 冲
        if _chong_target(liu_zhi) == nz:
            rel.append(f"{liu_zhi}{nz}相冲")
        # 六合
        if _he_zhi_target(liu_zhi) == nz:
            rel.append(f"{liu_zhi}{nz}六合")
        # 半合（三合中任两个）
        for trio, name in SAN_HE.items():
            if liu_zhi in trio and nz in trio and liu_zhi != nz:
                rel.append(f"{liu_zhi}{nz}半合{name}")
        # 三会半会
        for trio, name in SAN_HUI.items():
            if liu_zhi in trio and nz in trio and liu_zhi != nz:
                rel.append(f"{liu_zhi}{nz}会{name}")
        # 三刑（成对出现，命局含其中两个时与流月构成三刑）
        for trio, name in SAN_XING_GROUPS:
            if liu_zhi in trio and nz in trio and liu_zhi != nz:
                rel.append(f"{liu_zhi}{nz}{name}")
        # 子卯刑
        for pair, name in LIANG_XING:
            if liu_zhi in pair and nz in pair and liu_zhi != nz:
                rel.append(f"{liu_zhi}{nz}{name}")
        # 自刑
        if liu_zhi in ZI_XING and nz == liu_zhi:
            rel.append(f"{liu_zhi}{liu_zhi}自刑")
        # 六害
        if frozenset([liu_zhi, nz]) in LIU_HAI:
            rel.append(LIU_HAI[frozenset([liu_zhi, nz])])
        if rel:
            out.append({"target": f"{label}({nz})", "relation": "+".join(rel)})
    return out


def _wuxing_count(eight_chars: list[str]) -> dict[str, int]:
    """统计干支组合的五行个数。eight_chars: [年干, 月干, 日干, 时干, 年支, 月支, 日支, 时支]."""
    cnt = {"金": 0, "木": 0, "水": 0, "火": 0, "土": 0}
    for c in eight_chars:
        if not c:
            continue
        if c in LunarUtil.WU_XING_GAN:
            cnt[LunarUtil.WU_XING_GAN[c]] += 1
        elif c in LunarUtil.WU_XING_ZHI:
            cnt[LunarUtil.WU_XING_ZHI[c]] += 1
    return cnt


def _wuxing_delta(natal_count: dict[str, int], liu_gan: str, liu_zhi: str) -> dict[str, int]:
    """流月加入后五行计数变化（正数 = 流月带来增量）。"""
    delta = {k: 0 for k in natal_count}
    if liu_gan in LunarUtil.WU_XING_GAN:
        delta[LunarUtil.WU_XING_GAN[liu_gan]] += 1
    if liu_zhi in LunarUtil.WU_XING_ZHI:
        delta[LunarUtil.WU_XING_ZHI[liu_zhi]] += 1
    return delta


def _yong_shen_status(yong_shen: list[str], delta: dict[str, int]) -> str:
    """用神得失地的简化判定（B 级，参考性）。
    用神五行在流月有正 delta → 得地；有相生五行 → 平；相克 → 弱化；用神被冲 → 严重失地。
    """
    if not yong_shen:
        return "未知"
    score = 0
    for ys in yong_shen:
        if ys not in delta:
            continue
        if delta[ys] > 0:
            score += 2  # 用神同类增量
        # 相生五行增量也算正
        producer = next((k for k, v in SHENG.items() if v == ys), None)
        if producer and delta.get(producer, 0) > 0:
            score += 1
        # 克用神的五行增量算负
        ke_to_ys = next((k for k, v in KE.items() if v == ys), None)
        if ke_to_ys and delta.get(ke_to_ys, 0) > 0:
            score -= 1
    if score >= 2:
        return "得地"
    if score >= 0:
        return "平"
    if score >= -2:
        return "弱化"
    return "严重失地"


def _simple_yong_shen(day_master_wuxing: str, wuxing_count: dict[str, int]) -> tuple[list[str], list[str]]:
    """简化用神判定：按身强身弱二分。
    身强（日主同类+生我五行 ≥4） → 用神为克我/我克/泄我（财官食伤）
    身弱（< 4） → 用神为同类+生我（比劫印枭）
    返回 (yong_shen_list, ji_shen_list).
    """
    if not day_master_wuxing:
        return [], []
    # 同类 + 生我
    producer = next((k for k, v in SHENG.items() if v == day_master_wuxing), None)
    self_count = wuxing_count.get(day_master_wuxing, 0)
    prod_count = wuxing_count.get(producer, 0) if producer else 0
    strong = (self_count + prod_count) >= 4

    if strong:
        # 用神：克我/我克/我生（官杀财食）— 即除"同类+生我"外的三种
        consumer_my = SHENG[day_master_wuxing]  # 我生
        consumer_ke = KE[day_master_wuxing]  # 我克
        ke_me = next((k for k, v in KE.items() if v == day_master_wuxing), None)  # 克我
        yong = [v for v in [ke_me, consumer_ke, consumer_my] if v]
        ji = [day_master_wuxing] + ([producer] if producer else [])
    else:
        # 用神：同类+生我
        yong = [day_master_wuxing] + ([producer] if producer else [])
        consumer_my = SHENG[day_master_wuxing]
        consumer_ke = KE[day_master_wuxing]
        ke_me = next((k for k, v in KE.items() if v == day_master_wuxing), None)
        ji = [v for v in [ke_me, consumer_ke, consumer_my] if v]
    return yong, ji


# ──────────────────────── 主入口 ────────────────────────

def calculate_bazi_period(
    profile: dict,
    expr: str,
    base_date: str = "",
    granularity: str = "month",
) -> dict[str, Any]:
    """主函数。"""
    # 1. 校验 + 计算本命四柱
    birthday = profile.get("birthday")
    birthtime = profile.get("birthtime")
    sex = profile.get("sex")
    if not birthday or not birthtime or sex is None:
        return {
            "error": "profile_incomplete",
            "hint": f"用户档案不完整：device_id={profile.get('device_id')}，缺生日/时辰/性别。",
        }

    parts = birthday.split("-")
    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
    time_idx = parse_shichen(birthtime) or 6
    hour, minute = TIME_MAP.get(time_idx, (11, 30))

    natal_solar = Solar.fromYmdHms(year, month, day, hour, minute, 0)
    natal_lunar = natal_solar.getLunar()
    natal_ec = natal_lunar.getEightChar()
    natal_ec.setSect(1)  # 晚子时区分

    day_gan = natal_ec.getDayGan()
    day_zhi = natal_ec.getDayZhi()
    day_master_wx = LunarUtil.WU_XING_GAN.get(day_gan, "")

    # 本命八字 + 五行计数
    natal_chars = [
        natal_ec.getYearGan(), natal_ec.getMonthGan(), day_gan, natal_ec.getTimeGan(),
        natal_ec.getYearZhi(), natal_ec.getMonthZhi(), day_zhi, natal_ec.getTimeZhi(),
    ]
    natal_wuxing = _wuxing_count(natal_chars)

    yong_shen, ji_shen = _simple_yong_shen(day_master_wx, natal_wuxing)

    natal_recap = {
        "year_gz": natal_ec.getYear(),
        "month_gz": natal_ec.getMonth(),
        "day_gz": natal_ec.getDay(),
        "hour_gz": natal_ec.getTime(),
        "day_master": f"{day_gan}{day_master_wx}",
        "yong_shen": yong_shen,
        "ji_shen": ji_shen,
        "wuxing_natal": natal_wuxing,
    }

    natal_zhi_list = [
        ("year_zhi", natal_ec.getYearZhi()),
        ("month_zhi", natal_ec.getMonthZhi()),
        ("day_zhi", day_zhi),
        ("hour_zhi", natal_ec.getTimeZhi()),
    ]

    # 2. 解析时段 + 切分
    cal = resolve_calendar(expr=expr, base_date=base_date, view="bazi", granularity=granularity)
    if "error" in cal:
        return cal
    by_period_input = cal.get("by_period", [])
    if not by_period_input and cal.get("granularity") == "year":
        # year 粒度：用流年作为唯一周期（取年中点查 EightChar）
        g = cal["resolved"]["gregorian"]
        s_start = date.fromisoformat(g[0])
        s_end = date.fromisoformat(g[1])
        mid = s_start + (s_end - s_start) / 2
        ec_solar = Solar.fromYmdHms(mid.year, mid.month, mid.day, 12, 0, 0)
        ec = ec_solar.getLunar().getEightChar()
        by_period_input = [{
            "solar_range": g,
            "lunar_range": cal["resolved"].get("lunar", ""),
            "ganzhi_month": ec.getYear(),  # year 粒度用流年干支
            "lunar_month_idx": 0,
            "is_partial": False,
            "_use_year": True,
        }]

    # 3. 每月计算
    by_period_out: list[dict] = []
    for p in by_period_input:
        sr = p.get("solar_range", [])
        if len(sr) != 2:
            continue
        liu_gz = p.get("ganzhi_month") or ""
        if not liu_gz or len(liu_gz) < 2:
            continue
        liu_gan = liu_gz[0]
        liu_zhi = liu_gz[1] if len(liu_gz) >= 2 else ""

        ten_god_gan = _shi_shen(day_gan, liu_gan)
        ten_god_zhi_list = _hide_gan_shi_shen(day_gan, liu_zhi)
        delta = _wuxing_delta(natal_wuxing, liu_gan, liu_zhi)
        ys_status = _yong_shen_status(yong_shen, delta)
        interactions = _interactions(liu_zhi, natal_zhi_list)

        by_period_out.append({
            "solar_range": sr,
            "lunar_range": p.get("lunar_range"),
            "ganzhi_month": liu_gz,
            "ten_god_to_day_gan": ten_god_gan,
            "ten_god_to_day_zhi": ten_god_zhi_list,
            "interactions_with_natal": interactions,
            "wuxing_delta": delta,
            "yong_shen_status": ys_status,
            "is_partial": p.get("is_partial", False),
        })

    return {
        "natal_recap": natal_recap,
        "resolved": cal["resolved"],
        "view": "bazi",
        "granularity": cal["granularity"],
        "by_period": by_period_out,
        "scope_note": "用神得失地为参考性判定（B 级），不同流派可能有差异；日柱粒度未实现，需要按日时调用 granularity='day' 不返回流日（流日命理价值低）。",
    }
