# -*- coding: utf-8 -*-
"""
辅星安星算法（14颗）：
左辅右弼、文昌文曲、禄存天马、擎羊陀罗、火星铃星、地空地劫、天魁天钺。
"""
from __future__ import annotations

from .data.constants import TIME_INDEX_TO_ZHI_INDEX

# ---------- 禄存 by 年干 (palace index, 0=寅) ----------
_LUCUN = (0, 1, 3, 4, 3, 4, 6, 7, 9, 10)
# 甲→寅(0), 乙→卯(1), 丙→巳(3), 丁→午(4), 戊→巳(3),
# 己→午(4), 庚→申(6), 辛→酉(7), 壬→亥(9), 癸→子(10)

# ---------- 天马 by 年支组 (palace index) ----------
# 寅午戌→申(6), 申子辰→寅(0), 巳酉丑→亥(9), 亥卯未→巳(3)
_TIANMA = (0, 9, 6, 3, 0, 9, 6, 3, 0, 9, 6, 3)
# 子=0, 丑=9, 寅=6, 卯=3, 辰=0, 巳=9, 午=6, 未=3, 申=0, 酉=9, 戌=6, 亥=3

# ---------- 天魁 by 年干 (palace index) ----------
_TIANKUI = (11, 10, 9, 9, 11, 10, 11, 4, 1, 1)
# 甲→丑(11), 乙→子(10), 丙→亥(9), 丁→亥(9), 戊→丑(11),
# 己→子(10), 庚→丑(11), 辛→午(4), 壬→卯(1), 癸→卯(1)

# ---------- 天钺 by 年干 (palace index) ----------
_TIANYUE = (5, 6, 7, 7, 5, 6, 5, 0, 3, 3)
# 甲→未(5), 乙→申(6), 丙→酉(7), 丁→酉(7), 戊→未(5),
# 己→申(6), 庚→未(5), 辛→寅(0), 壬→巳(3), 癸→巳(3)

# ---------- 火星起始宫位 by 年支 (palace index) ----------
# 寅午戌→丑(11), 申子辰→寅(0), 巳酉丑→卯(1), 亥卯未→酉(7)
_HUOXING_START = (0, 1, 11, 7, 0, 1, 11, 7, 0, 1, 11, 7)

# ---------- 铃星起始宫位 by 年支 (palace index) ----------
# 寅午戌→卯(1), 申子辰→戌(8), 巳酉丑→戌(8), 亥卯未→戌(8)
_LINGXING_START = (8, 8, 1, 8, 8, 8, 1, 8, 8, 8, 1, 8)


def place_minor_stars(
    year_gan_index: int,
    year_zhi_index: int,
    lunar_month: int,
    time_index: int,
) -> list[list[tuple[str, str]]]:
    """
    安14颗辅星到12宫。

    Args:
        year_gan_index: 年干索引 (0-based, 甲=0)
        year_zhi_index: 年支索引 (0-based, 子=0)
        lunar_month: 农历月份（正数）
        time_index: 时辰序号 0-12

    Returns:
        12个列表，每个列表包含 (star_name, star_type) 元组。
        index 0 = 寅宫。
    """
    palaces: list[list[tuple[str, str]]] = [[] for _ in range(12)]
    time_zhi = TIME_INDEX_TO_ZHI_INDEX[time_index]
    month = lunar_month  # 1-based

    def put(palace_idx: int, name: str, star_type: str):
        palaces[palace_idx % 12].append((name, star_type))

    # 安星顺序与 iztro 保持一致，决定同宫内的排列

    # 1. 左辅：辰宫(2)起正月顺数
    put((1 + month) % 12, "左辅", "soft")
    # 2. 右弼：戌宫(8)起正月逆数
    put((9 - month + 12) % 12, "右弼", "soft")
    # 3. 文昌：戌宫(8)起子时逆数
    wenchang_idx = (8 - time_zhi + 12) % 12
    put(wenchang_idx, "文昌", "soft")
    # 4. 文曲：辰宫(2)起子时顺数
    wenqu_idx = (2 + time_zhi) % 12
    put(wenqu_idx, "文曲", "soft")
    # 5. 天魁
    put(_TIANKUI[year_gan_index], "天魁", "soft")
    # 6. 天钺
    put(_TIANYUE[year_gan_index], "天钺", "soft")
    # 7. 禄存
    lucun_idx = _LUCUN[year_gan_index]
    put(lucun_idx, "禄存", "lucun")
    # 8. 天马
    put(_TIANMA[year_zhi_index], "天马", "tianma")
    # 9. 地空：亥宫(9)起子时逆数
    put((9 - time_zhi + 12) % 12, "地空", "tough")
    # 10. 地劫：亥宫(9)起子时顺数
    put((9 + time_zhi) % 12, "地劫", "tough")
    # 11. 火星：按年支组起始 + 时支
    put((_HUOXING_START[year_zhi_index] + time_zhi) % 12, "火星", "tough")
    # 12. 铃星：按年支组起始 + 时支
    put((_LINGXING_START[year_zhi_index] + time_zhi) % 12, "铃星", "tough")
    # 13. 擎羊：禄存前一位
    put((lucun_idx + 1) % 12, "擎羊", "tough")
    # 14. 陀罗：禄存后一位
    put((lucun_idx - 1 + 12) % 12, "陀罗", "tough")

    return palaces
