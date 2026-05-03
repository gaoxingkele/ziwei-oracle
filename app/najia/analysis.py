# -*- coding: utf-8 -*-
"""纳甲六爻断卦分析层（增删卜易/卜筮正宗派）。

输入: Najia.compile() 之后的 obj.data
输出: 在原数据基础上补充每爻状态、卦身、用神、四神、断卦摘要

不修改 najia 库代码，独立模块。
"""
from __future__ import annotations
from typing import Any

from .yongshen import take_yongshen

# ── 五行 / 地支基础 ───────────────────────────────────────────────
ZHI_ORDER = "子丑寅卯辰巳午未申酉戌亥"
ZHI_WUXING: dict[str, str] = {
    "子": "水", "亥": "水",
    "寅": "木", "卯": "木",
    "巳": "火", "午": "火",
    "申": "金", "酉": "金",
    "辰": "土", "戌": "土", "丑": "土", "未": "土",
}
# 我生
SHENG_OF: dict[str, str] = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
# 我克
KE_OF: dict[str, str] = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
# 六冲
LIUCHONG: dict[str, str] = {
    "子": "午", "午": "子", "丑": "未", "未": "丑",
    "寅": "申", "申": "寅", "卯": "酉", "酉": "卯",
    "辰": "戌", "戌": "辰", "巳": "亥", "亥": "巳",
}
# 六合
LIUHE_PAIRS: dict[str, str] = {
    "子": "丑", "丑": "子", "寅": "亥", "亥": "寅",
    "卯": "戌", "戌": "卯", "辰": "酉", "酉": "辰",
    "巳": "申", "申": "巳", "午": "未", "未": "午",
}
# 三合局：每个支属于的局（局五行）
SANHE_GROUP: dict[str, tuple[tuple[str, ...], str]] = {
    "申": (("申", "子", "辰"), "水"), "子": (("申", "子", "辰"), "水"), "辰": (("申", "子", "辰"), "水"),
    "亥": (("亥", "卯", "未"), "木"), "卯": (("亥", "卯", "未"), "木"), "未": (("亥", "卯", "未"), "木"),
    "寅": (("寅", "午", "戌"), "火"), "午": (("寅", "午", "戌"), "火"), "戌": (("寅", "午", "戌"), "火"),
    "巳": (("巳", "酉", "丑"), "金"), "酉": (("巳", "酉", "丑"), "金"), "丑": (("巳", "酉", "丑"), "金"),
}
# 十二长生中"绝"位
JUE_OF: dict[str, str] = {"木": "申", "火": "亥", "金": "寅", "水": "巳", "土": "巳"}
# "墓"位
MU_OF: dict[str, str] = {"木": "未", "火": "戌", "金": "丑", "水": "辰", "土": "辰"}


def _wuxing_relation(w_self: str, w_other: str) -> str:
    """w_self 相对 w_other 的关系: 比和/生(我生)/被生/克(我克)/被克。"""
    if w_self == w_other:
        return "比和"
    if SHENG_OF[w_self] == w_other:
        return "生"
    if KE_OF[w_self] == w_other:
        return "克"
    if SHENG_OF[w_other] == w_self:
        return "被生"
    if KE_OF[w_other] == w_self:
        return "被克"
    return "比和"


def _wangshuai(yao_wx: str, month_zhi: str) -> str:
    """旺相休囚死 (按月令)。"""
    m_wx = ZHI_WUXING[month_zhi]
    rel = _wuxing_relation(yao_wx, m_wx)
    return {
        "比和": "旺",   # 当令
        "被生": "相",   # 月令生爻 (次旺)
        "生": "休",     # 爻生月令 (已退)
        "克": "囚",     # 爻克月令 (被困)
        "被克": "死",   # 月令克爻 (最弱)
    }[rel]


def _zhi_pair_relation(z1: str, z2: str) -> str:
    """两支之间的关系：临/冲/合/无。"""
    if z1 == z2:
        return "临"
    if LIUCHONG.get(z1) == z2:
        return "冲"
    if LIUHE_PAIRS.get(z1) == z2:
        return "合"
    return "无"


# ── 卦身 ─────────────────────────────────────────────────────────
def _calc_guashen(shi_pos: int, params: list[int]) -> str:
    """卦身: 阳世从子起初爻, 阴世从午起初爻。

    shi_pos: 世爻位 (1~6)
    params:  爻码 [1=少阳, 2=少阴, 3=老阳动, 4=老阴动]
    """
    shi_yang = params[shi_pos - 1] in (1, 3)
    base = 0 if shi_yang else 6  # 子=0、午=6
    idx = (base + shi_pos - 1) % 12
    return ZHI_ORDER[idx]


# ── 每爻状态 ─────────────────────────────────────────────────────
def _analyze_yao(
    qinx: list[str], qin6: list[str], god6: list[str], params: list[int],
    dong: list[int], bian_qinx: list[str] | None, bian_qin6: list[str] | None,
    hide: dict[str, Any] | None, gz: dict[str, str], xkong: str,
) -> list[dict[str, Any]]:
    month_zhi = gz["month"][1]
    day_zhi = gz["day"][1]
    states: list[dict[str, Any]] = []
    for i in range(6):
        zhi = qinx[i][1]
        wx = qinx[i][2]
        m_pair = _zhi_pair_relation(zhi, month_zhi)
        d_pair = _zhi_pair_relation(zhi, day_zhi)
        m_sk = _wuxing_relation(wx, ZHI_WUXING[month_zhi])
        d_sk = _wuxing_relation(wx, ZHI_WUXING[day_zhi])
        is_dong = i in dong
        kong = zhi in (xkong or "")
        po = (m_pair == "冲")  # 月破
        # 静爻被日辰冲 => 暗动；动爻被日冲 => 日破
        an_dong = (d_pair == "冲") and not is_dong
        ri_po = (d_pair == "冲") and is_dong

        state: dict[str, Any] = {
            "pos": i + 1,
            "zhi": zhi,
            "wuxing": wx,
            "qin6": qin6[i],
            "god": god6[i],
            "is_dong": is_dong,
            "wangshuai": _wangshuai(wx, month_zhi),
            "month_relation": m_pair,
            "day_relation": d_pair,
            "month_sheng_ke": m_sk,
            "day_sheng_ke": d_sk,
            "kong": kong,
            "an_dong": an_dong,
            "yue_po": po,
            "ri_po": ri_po,
        }
        # 伏神
        if hide and "seat" in hide and i in hide["seat"]:
            seat_idx = hide["seat"].index(i)
            # hide.qin6/qinx 是 6 元 list, seat 是其在该 list 中的下标列表
            state["fu_qin6"] = hide["qin6"][hide["seat"][seat_idx]] if isinstance(hide["qin6"][i], str) else None
            state["fu_qinx"] = hide["qinx"][hide["seat"][seat_idx]] if isinstance(hide["qinx"][i], str) else None

        # 动爻分析
        if is_dong and bian_qinx and len(bian_qinx) == 6 and bian_qinx[i]:
            bz = bian_qinx[i][1]
            bw = bian_qinx[i][2]
            changes: list[str] = []
            # 进/退神
            if wx == bw:
                if (zhi, bz) in (("寅", "卯"), ("巳", "午"), ("申", "酉"), ("亥", "子")):
                    changes.append("进神")
                elif (zhi, bz) in (("卯", "寅"), ("午", "巳"), ("酉", "申"), ("子", "亥")):
                    changes.append("退神")
            # 回头生/克
            sk = _wuxing_relation(bw, wx)
            if sk == "生":
                changes.append("回头生")
            elif sk == "克":
                changes.append("回头克")
            # 化空
            if bz in (xkong or ""):
                changes.append("化空")
            # 化破 (变爻被日冲)
            if LIUCHONG.get(bz) == day_zhi:
                changes.append("化破")
            # 化绝 / 化墓
            if bz == JUE_OF.get(bw):
                changes.append("化绝")
            if bz == MU_OF.get(bw):
                changes.append("化墓")
            state["bian_zhi"] = bz
            state["bian_wuxing"] = bw
            state["bian_qin6"] = bian_qin6[i] if bian_qin6 else None
            state["changes"] = changes

        states.append(state)
    return states


# ── 用神 / 元忌仇神 ───────────────────────────────────────────────
def _select_yongshen(
    yao_states: list[dict[str, Any]], shi_pos: int,
    question: str, gender: str,
) -> dict[str, Any]:
    """取用神，返回 {qin6, positions, wuxing, source}。

    若取到的六亲在卦中无现 (六亲不全) → 用神为伏神，positions 空。
    若 question 未命中规则 → 默认以世爻为用神。
    """
    qin = take_yongshen(question, gender)
    if qin is None:
        # 默认世爻
        st = yao_states[shi_pos - 1]
        return {
            "qin6": st["qin6"], "positions": [shi_pos],
            "wuxing": st["wuxing"], "source": "世爻(默认)",
        }
    positions = [s["pos"] for s in yao_states if s["qin6"] == qin]
    if not positions:
        return {"qin6": qin, "positions": [], "wuxing": None, "source": "伏神(卦中无现)"}
    # 多爻同六亲时，传统取动爻 > 临世应 > 旺相 > 取首位；这里取持世/动爻优先，否则首爻
    dong_pos = [p for p in positions if yao_states[p - 1]["is_dong"]]
    if dong_pos:
        chosen = dong_pos[0]
    elif shi_pos in positions:
        chosen = shi_pos
    else:
        chosen = positions[0]
    return {
        "qin6": qin, "positions": positions, "primary": chosen,
        "wuxing": yao_states[chosen - 1]["wuxing"], "source": "关键词匹配",
    }


def _four_gods(yong_wx: str | None) -> dict[str, str | None]:
    """元神(生用神)、忌神(克用神)、仇神(克元神)。"""
    if not yong_wx:
        return {"yuan": None, "ji": None, "chou": None}
    yuan = next(w for w, t in SHENG_OF.items() if t == yong_wx)  # 生用神之五行
    ji = next(w for w, t in KE_OF.items() if t == yong_wx)       # 克用神之五行
    chou = next(w for w, t in KE_OF.items() if t == yuan)        # 克元神之五行
    return {"yuan": yuan, "ji": ji, "chou": chou}


# ── 综合断卦 ─────────────────────────────────────────────────────
def _build_summary(
    yao_states: list[dict[str, Any]], yong: dict[str, Any],
    fg: dict[str, str | None], guashen: str,
) -> str:
    """生成 2~5 句断卦摘要。"""
    if not yong["positions"]:
        return f"用神({yong['qin6']}) 不上卦, 需取伏神. 卦身: {guashen}."

    primary = yong.get("primary") or yong["positions"][0]
    ys = yao_states[primary - 1]
    lines: list[str] = []

    # 1) 用神基本面
    state_tags = []
    if ys["kong"]:
        state_tags.append("旬空")
    if ys["yue_po"]:
        state_tags.append("月破")
    if ys["ri_po"]:
        state_tags.append("日破")
    if ys["an_dong"]:
        state_tags.append("暗动")
    extra = "/".join(ys.get("changes", []))
    tag_str = (", " + ", ".join(state_tags)) if state_tags else ""
    extra_str = (", " + extra) if extra else ""
    sk_phrase = {
        "比和": "比和", "生": "爻生{}", "克": "爻克{}",
        "被生": "{}生爻", "被克": "{}克爻",
    }
    m_phrase = sk_phrase[ys["month_sheng_ke"]].format("月")
    d_phrase = sk_phrase[ys["day_sheng_ke"]].format("日")
    lines.append(
        f"用神: {ys['qin6']}({ys['zhi']}{ys['wuxing']}, 第{primary}爻) "
        f"月令{ys['wangshuai']}, {m_phrase}, {d_phrase}{tag_str}{extra_str}."
    )

    # 2) 元神/忌神动否
    yuan_ji_lines = []
    for st in yao_states:
        if not st["is_dong"]:
            continue
        if st["wuxing"] == fg.get("yuan"):
            yuan_ji_lines.append(f"元神({st['qin6']}{st['zhi']}) 动")
        elif st["wuxing"] == fg.get("ji"):
            yuan_ji_lines.append(f"忌神({st['qin6']}{st['zhi']}) 动")
    if yuan_ji_lines:
        lines.append("; ".join(yuan_ji_lines) + ".")
    else:
        lines.append("元神/忌神俱静.")

    # 3) 简易吉凶倾向 (用神状态 × 元忌神动否)
    yuan_dong = any(st["is_dong"] and st["wuxing"] == fg.get("yuan") for st in yao_states)
    ji_dong = any(st["is_dong"] and st["wuxing"] == fg.get("ji") for st in yao_states)
    yong_bad = (
        ys["kong"] or ys["yue_po"] or ys["ri_po"]
        or ys["wangshuai"] in ("囚", "死")
        or any(c in ys.get("changes", []) for c in ("回头克", "化绝", "化墓", "化破", "化空", "退神"))
    )
    yong_good = ys["wangshuai"] in ("旺", "相") and not yong_bad

    if yong_bad and ji_dong:
        verdict = "倾向: 用神受损又逢忌神动克, 偏凶."
    elif yong_good and yuan_dong:
        verdict = "倾向: 元神发动生扶, 用神旺相, 偏吉."
    elif ji_dong and not yuan_dong:
        verdict = "倾向: 忌神动而克用神, 偏不利."
    elif yuan_dong and not ji_dong:
        verdict = "倾向: 元神动而生用神, 偏吉."
    elif yong_bad:
        verdict = "倾向: 用神失令受制, 偏不利."
    elif yong_good:
        verdict = "倾向: 用神旺相静守, 略吉."
    else:
        verdict = "倾向: 平稳, 待时而动."
    lines.append(verdict)

    # 4) 卦身
    lines.append(f"卦身: {guashen} (世爻所主之事).")
    return " ".join(lines)


# ── 主入口 ──────────────────────────────────────────────────────
def analyze(data: dict[str, Any], question: str = "", gender: str = "") -> dict[str, Any]:
    """对 najia.data 做断卦分析, 返回扩展字段。"""
    qinx = data["qinx"]
    qin6 = data["qin6"]
    god6 = data["god6"]
    params = data["params"]
    dong = data.get("dong", [])
    bian = data.get("bian") or {}
    bian_qinx = bian.get("qinx") if bian else None
    bian_qin6 = bian.get("qin6") if bian else None
    hide = data.get("hide")
    gz = data["lunar"]["gz"]
    xkong = data["lunar"]["xkong"]
    shi_pos, _, _ = data["shiy"]

    yao_states = _analyze_yao(
        qinx, qin6, god6, params, dong, bian_qinx, bian_qin6, hide, gz, xkong,
    )
    guashen = _calc_guashen(shi_pos, params)
    yong = _select_yongshen(yao_states, shi_pos, question, gender)
    fg = _four_gods(yong.get("wuxing"))
    summary = _build_summary(yao_states, yong, fg, guashen)

    tts_text = _build_tts(yao_states, yong, fg, guashen, question, gz)
    return {
        "yao_states": yao_states,
        "guashen": guashen,
        "yongshen": yong,
        "four_gods": fg,
        "summary": summary,
        "tts_text": tts_text,
    }


# ── TTS 友好版结论（80~150 字，口语化，无括号无英文）────────────
def _build_tts(
    yao_states: list[dict[str, Any]], yong: dict[str, Any],
    fg: dict[str, str | None], guashen: str,
    question: str, gz: dict[str, str],
) -> str:
    parts: list[str] = []
    q = (question or "").strip()
    if q:
        parts.append(f"占问{q}。")

    if not yong["positions"]:
        parts.append(f"用神{yong['qin6']}不上卦，需取伏神断之。卦身落在{guashen}位。")
        return "".join(parts)

    primary = yong.get("primary") or yong["positions"][0]
    ys = yao_states[primary - 1]
    pos_cn = "初二三四五六"[primary - 1]
    parts.append(f"用神{ys['qin6']}，{ys['zhi']}{ys['wuxing']}居第{pos_cn}爻。")

    sk_phrase = {
        "比和": "与月令比和", "生": "爻生月令", "克": "爻克月令",
        "被生": "得月令生扶", "被克": "受月令克制",
    }
    parts.append(sk_phrase[ys["month_sheng_ke"]] + "，")
    sk_phrase_d = {
        "比和": "日辰临之", "生": "爻生日辰", "克": "爻克日辰",
        "被生": "日辰生爻", "被克": "日辰克爻",
    }
    parts.append(sk_phrase_d[ys["day_sheng_ke"]] + "。")

    flags: list[str] = []
    if ys["kong"]: flags.append("旬空")
    if ys["yue_po"]: flags.append("月破")
    if ys["ri_po"]: flags.append("日破")
    if ys["an_dong"]: flags.append("暗动")
    flags.extend(ys.get("changes", []))
    if flags:
        parts.append("用神" + "、".join(flags) + "。")

    yuan_dong = [s for s in yao_states if s["is_dong"] and s["wuxing"] == fg.get("yuan")]
    ji_dong = [s for s in yao_states if s["is_dong"] and s["wuxing"] == fg.get("ji")]
    if yuan_dong and not ji_dong:
        parts.append("元神发动生扶用神，吉。")
    elif ji_dong and not yuan_dong:
        parts.append("忌神发动相克用神，凶。")
    elif yuan_dong and ji_dong:
        parts.append("元神忌神俱动，吉凶相参。")
    else:
        parts.append("元神忌神俱静。")

    yong_bad = (
        ys["kong"] or ys["yue_po"] or ys["ri_po"]
        or ys["wangshuai"] in ("囚", "死")
        or any(c in ys.get("changes", []) for c in ("回头克", "化绝", "化墓", "化破", "化空", "退神"))
    )
    yong_good = ys["wangshuai"] in ("旺", "相") and not yong_bad
    if yong_bad and ji_dong:
        verdict = "综合判断，事难谐，宜守不宜进。"
    elif yong_good and yuan_dong:
        verdict = "综合判断，事可成。"
    elif ji_dong and not yuan_dong:
        verdict = "综合判断，忌神动克用神，不利。"
    elif yuan_dong and not ji_dong:
        verdict = "综合判断，元神生扶，偏吉。"
    elif yong_bad:
        verdict = "综合判断，用神失令受制，宜慎。"
    elif yong_good:
        verdict = "综合判断，平稳略吉。"
    else:
        verdict = "综合判断，平稳，待时而动。"
    parts.append(verdict)
    parts.append(f"卦身在{guashen}位。")
    return "".join(parts)
