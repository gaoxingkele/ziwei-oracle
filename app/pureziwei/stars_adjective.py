# -*- coding: utf-8 -*-
"""
杂耀安星算法（38颗）。
"""
from __future__ import annotations

from .data.constants import TIME_INDEX_TO_ZHI_INDEX

# ---------- 咸池 by 年支 (palace index, 0=寅) ----------
# 子辰申→酉(7), 丑巳酉→午(4), 寅午戌→卯(1), 卯未亥→子(10)
_XIANCHI = (7, 4, 1, 10, 7, 4, 1, 10, 7, 4, 1, 10)

# ---------- 华盖 by 年支 ----------
# 子辰申→辰(2), 丑巳酉→丑(11), 寅午戌→戌(8), 卯未亥→未(5)
_HUAGAI = (2, 11, 8, 5, 2, 11, 8, 5, 2, 11, 8, 5)

# ---------- 孤辰 by 年支 ----------
# 寅卯辰→巳(3), 巳午未→申(6), 申酉戌→亥(9), 亥子丑→寅(0)
_GUCHEN = (0, 0, 3, 3, 3, 6, 6, 6, 9, 9, 9, 0)

# ---------- 寡宿 by 年支 ----------
# 寅卯辰→丑(11), 巳午未→辰(2), 申酉戌→未(5), 亥子丑→戌(8)
_GUASU = (8, 8, 11, 11, 11, 2, 2, 2, 5, 5, 5, 8)

# ---------- 破碎 by 年支 ----------
# 子午卯酉→巳(3), 寅申巳亥→酉(7), 辰戌丑未→丑(11)
_POSUI = (3, 11, 7, 3, 11, 7, 3, 11, 7, 3, 11, 7)

# ---------- 天厨 by 年干 (palace index) ----------
_TIANCHU = (3, 4, 10, 3, 4, 6, 0, 4, 7, 9)
# 甲→巳(3), 乙→午(4), 丙→子(10), 丁→巳(3), 戊→午(4),
# 己→申(6), 庚→寅(0), 辛→午(4), 壬→酉(7), 癸→亥(9)

# ---------- 蜚廉 by 年支 (palace index) ----------
_FEILIAN = (6, 7, 8, 3, 4, 5, 0, 1, 2, 9, 10, 11)

# ---------- 天官 by 年干 (palace index) ----------
_TIANGUAN = (5, 2, 3, 0, 1, 7, 9, 7, 8, 4)
# 甲→未(5), 乙→辰(2), 丙→巳(3), 丁→寅(0), 戊→卯(1),
# 己→酉(7), 庚→亥(9), 辛→酉(7), 壬→戌(8), 癸→午(4)

# ---------- 天福 by 年干 (palace index) ----------
_TIANFU_ADJ = (7, 6, 10, 9, 1, 0, 4, 3, 4, 3)
# 甲→酉(7), 乙→申(6), 丙→子(10), 丁→亥(9), 戊→卯(1),
# 己→寅(0), 庚→午(4), 辛→巳(3), 壬→午(4), 癸→巳(3)

# ---------- 阴煞 by 月 (palace index) ----------
# monthIndex%6 → [寅(0), 子(10), 戌(8), 申(6), 午(4), 辰(2)]
_YINSHA = (0, 10, 8, 6, 4, 2)

# ---------- 天月 by 月 (palace index) ----------
_TIANYUE = (8, 3, 2, 0, 5, 1, 9, 5, 0, 4, 8, 0)

# ---------- 天巫 by 月 ----------
# monthIndex%4 → [巳(3), 申(6), 寅(0), 亥(9)]
_TIANWU = (3, 6, 0, 9)

# ---------- 解神 by 月 ----------
# monthIndex//2 → [申(6), 戌(8), 子(10), 寅(0), 辰(2), 午(4)]
_JIESHEN = (6, 8, 10, 0, 2, 4)

# ---------- 年解 by 年支 (palace index) ----------
_NIANJIE = (8, 7, 6, 5, 4, 3, 2, 1, 0, 11, 10, 9)

# ---------- 截路/空亡 by 年干组 ----------
# 甲己→申酉(6,7), 乙庚→午未(4,5), 丙辛→辰巳(2,3), 丁壬→寅卯(0,1), 戊癸→子丑(10,11)
_JIEKONG_PAIRS = ((6, 7), (4, 5), (2, 3), (0, 1), (10, 11))


def _calc_xunkong(year_gan_index: int, year_zhi_index: int) -> int:
    """计算旬空位置（甲子旬空亡第一个分支的 palace index）"""
    # 旬内位置 = 干支之差（保证正数）
    pos_in_xun = (year_gan_index - year_zhi_index + 12) % 12
    # 如果 pos_in_xun >= 10 说明不是合法干支（不会发生），取 mod 10
    # 旬头地支 = year_zhi_index - year_gan_index (mod 12)
    xun_head_zhi = (year_zhi_index - year_gan_index + 12) % 12
    # 旬空的两个地支 = 旬头+10 和 旬头+11 (mod 12)
    kong1_zhi = (xun_head_zhi + 10) % 12
    # 转 palace index
    return (kong1_zhi - 2 + 12) % 12


def place_adjective_stars(
    year_gan_index: int,
    year_zhi_index: int,
    lunar_month: int,
    lunar_day: int,
    time_index: int,
    soul_palace_index: int,
    body_palace_index: int,
    zuofu_palace_index: int,
    youbi_palace_index: int,
    wenchang_palace_index: int,
    wenqu_palace_index: int,
) -> list[list[tuple[str, str]]]:
    """
    安38颗杂耀到12宫。

    Args:
        year_gan_index: 年干索引 (0-based, 甲=0)
        year_zhi_index: 年支索引 (0-based, 子=0)
        lunar_month: 农历月份（正数, 1-12）
        lunar_day: 农历日（1-30）
        time_index: 时辰序号 0-12
        soul_palace_index: 命宫 palace index (0=寅)
        body_palace_index: 身宫 palace index
        zuofu_palace_index: 左辅 palace index
        youbi_palace_index: 右弼 palace index
        wenchang_palace_index: 文昌 palace index
        wenqu_palace_index: 文曲 palace index

    Returns:
        12个列表，每个列表包含 (star_name, star_type) 元组。
    """
    palaces: list[list[tuple[str, str]]] = [[] for _ in range(12)]
    time_zhi = TIME_INDEX_TO_ZHI_INDEX[time_index]
    mi = lunar_month - 1  # 0-based month index
    di = lunar_day - 1  # 0-based day index

    def put(palace_idx: int, name: str, star_type: str):
        palaces[palace_idx % 12].append((name, star_type))

    # 安星顺序与 iztro 保持一致（决定同宫内排列）

    # 1. 花星
    hongluan_idx = (1 - year_zhi_index + 12) % 12
    put(hongluan_idx, "红鸾", "flower")
    put((hongluan_idx + 6) % 12, "天喜", "flower")
    put(_XIANCHI[year_zhi_index], "咸池", "flower")
    put((10 + lunar_month) % 12, "天姚", "flower")

    # 2. 解神（月）
    put(_JIESHEN[mi // 2], "解神", "helper")

    # 3. 年支星（龙池凤阁）
    put((2 + year_zhi_index) % 12, "龙池", "adjective")
    put((8 - year_zhi_index + 12) % 12, "凤阁", "adjective")

    # 4. 日星（三台八座恩光天贵）
    put((zuofu_palace_index + di) % 12, "三台", "adjective")
    put((youbi_palace_index - di + 12) % 12, "八座", "adjective")
    put((wenchang_palace_index + di - 1 + 12) % 12, "恩光", "adjective")
    put((wenqu_palace_index + di - 1 + 12) % 12, "天贵", "adjective")

    # 5. 时星（台辅封诰）
    put((4 + time_zhi) % 12, "台辅", "adjective")
    put(time_zhi % 12, "封诰", "adjective")

    # 6. 天才天寿（命宫/身宫 + 年支）
    put((soul_palace_index + year_zhi_index) % 12, "天才", "adjective")
    put((body_palace_index + year_zhi_index) % 12, "天寿", "adjective")

    # 7. 月星（天巫天刑天厨阴煞）
    put(_TIANWU[mi % 4], "天巫", "adjective")
    put((6 + lunar_month) % 12, "天刑", "adjective")
    put(_TIANCHU[year_gan_index], "天厨", "adjective")
    put(_YINSHA[mi % 6], "阴煞", "adjective")

    # 8. 年干星（天官天月天哭天虚天福天空）
    put(_TIANGUAN[year_gan_index], "天官", "adjective")
    put(_TIANYUE[mi], "天月", "adjective")
    put((4 - year_zhi_index + 12) % 12, "天哭", "adjective")
    put((4 + year_zhi_index) % 12, "天虚", "adjective")
    put(_TIANFU_ADJ[year_gan_index], "天福", "adjective")
    put((year_zhi_index + 1 - 2 + 12) % 12, "天空", "adjective")

    # 9. 截路/空亡/旬空
    stem_group = year_gan_index % 5
    jie_idx, kong_idx = _JIEKONG_PAIRS[stem_group]
    put(jie_idx, "截路", "adjective")
    put(kong_idx, "空亡", "adjective")
    put(_calc_xunkong(year_gan_index, year_zhi_index), "旬空", "adjective")

    # 10. 天德月德
    put((7 + year_zhi_index) % 12, "天德", "adjective")
    put((3 + year_zhi_index) % 12, "月德", "adjective")

    # 11. 蜚廉孤辰寡宿破碎华盖
    put(_FEILIAN[year_zhi_index], "蜚廉", "adjective")
    put(_GUCHEN[year_zhi_index], "孤辰", "adjective")
    put(_GUASU[year_zhi_index], "寡宿", "adjective")
    put(_POSUI[year_zhi_index], "破碎", "adjective")
    put(_HUAGAI[year_zhi_index], "华盖", "adjective")

    # 12. 年解
    put(_NIANJIE[year_zhi_index], "年解", "helper")

    # 13. 天伤天使（与命宫相关）
    put((soul_palace_index + 5) % 12, "天伤", "adjective")
    put((soul_palace_index + 7) % 12, "天使", "adjective")

    return palaces
