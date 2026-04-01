# -*- coding: utf-8 -*-
"""
辅助排列：长生12神、博士12神、将前12神、岁前12神。
"""
from __future__ import annotations

# 长生12神名称
CHANGSHENG_NAMES = ("长生", "沐浴", "冠带", "临官", "帝旺", "衰", "病", "死", "墓", "绝", "胎", "养")

# 博士12神名称
BOSHI_NAMES = ("博士", "力士", "青龙", "小耗", "将军", "奏书", "飞廉", "喜神", "病符", "大耗", "伏兵", "官府")

# 将前12神名称
JIANGQIAN_NAMES = ("将星", "攀鞍", "岁驿", "息神", "华盖", "劫煞", "灾煞", "天煞", "指背", "咸池", "月煞", "亡神")

# 岁前12神名称
SUIQIAN_NAMES = ("岁建", "晦气", "丧门", "贯索", "官符", "小耗", "大耗", "龙德", "白虎", "天德", "吊客", "病符")

# 长生起始宫位 by 五行局数 (palace index, 0=寅)
# 水二局→申(6), 木三局→亥(9), 金四局→巳(3), 土五局→申(6), 火六局→寅(0)
_CHANGSHENG_START = {2: 6, 3: 9, 4: 3, 5: 6, 6: 0}

# 将前12神起始 by 年支三合组 (palace index)
# 子辰申→子(10), 丑巳酉→酉(7), 寅午戌→午(4), 卯未亥→卯(1)
_JIANGQIAN_START = (10, 7, 4, 1, 10, 7, 4, 1, 10, 7, 4, 1)


def place_changsheng12(
    wu_xing_value: int, is_clockwise: bool
) -> list[str]:
    """
    排长生12神。

    Args:
        wu_xing_value: 五行局数 (2/3/4/5/6)
        is_clockwise: 是否顺行（阳男阴女顺行，阴男阳女逆行）

    Returns:
        12个字符串，index 0=寅宫的长生12神名称。
    """
    result = [""] * 12
    start = _CHANGSHENG_START[wu_xing_value]
    step = 1 if is_clockwise else -1
    for i, name in enumerate(CHANGSHENG_NAMES):
        idx = (start + i * step) % 12
        result[idx] = name
    return result


def place_boshi12(
    lucun_palace_index: int, is_clockwise: bool
) -> list[str]:
    """
    排博士12神。从禄存所在宫位开始。

    Args:
        lucun_palace_index: 禄存所在 palace index (0=寅)
        is_clockwise: 是否顺行

    Returns:
        12个字符串。
    """
    result = [""] * 12
    step = 1 if is_clockwise else -1
    for i, name in enumerate(BOSHI_NAMES):
        idx = (lucun_palace_index + i * step) % 12
        result[idx] = name
    return result


def place_jiangqian12(year_zhi_index: int) -> list[str]:
    """
    排将前12神。永远顺行。

    Args:
        year_zhi_index: 年支索引 (0=子)

    Returns:
        12个字符串。
    """
    result = [""] * 12
    start = _JIANGQIAN_START[year_zhi_index]
    for i, name in enumerate(JIANGQIAN_NAMES):
        idx = (start + i) % 12
        result[idx] = name
    return result


def place_suiqian12(year_zhi_index: int) -> list[str]:
    """
    排岁前12神。从年支所在宫位顺行。

    Args:
        year_zhi_index: 年支索引 (0=子)

    Returns:
        12个字符串。
    """
    result = [""] * 12
    start = (year_zhi_index - 2 + 12) % 12  # ZHI → palace index
    for i, name in enumerate(SUIQIAN_NAMES):
        idx = (start + i) % 12
        result[idx] = name
    return result
