# -*- coding: utf-8 -*-
"""
14主星安星算法：紫微星系（6颗）+ 天府星系（8颗）。
"""
from __future__ import annotations


def calc_ziwei_palace_index(lunar_day: int, wu_xing_value: int) -> int:
    """
    计算紫微星的宫位索引（0=寅宫）。

    算法口诀：
        六五四三二，酉午亥辰丑，
        局数除日数，商数宫前走；
        若见数无余，便要起虎口，
        日数小於局，还直宫中守。

    Args:
        lunar_day: 农历生日（1-30）
        wu_xing_value: 五行局数（2/3/4/5/6）

    Returns:
        紫微星所在宫位的 palace_index (0=寅, 1=卯, ..., 11=丑)
    """
    offset = 0
    while True:
        d = lunar_day + offset
        q, r = divmod(d, wu_xing_value)
        if r == 0:
            break
        offset += 1

    base = (q - 1) % 12
    if offset == 0:
        return base
    elif offset % 2 == 1:
        return (base - offset) % 12
    else:
        return (base + offset) % 12


def calc_tianfu_palace_index(ziwei_index: int) -> int:
    """
    计算天府星的宫位索引。天府与紫微关于寅-申轴对称。

    Args:
        ziwei_index: 紫微星的 palace_index (0=寅)

    Returns:
        天府星的 palace_index (0=寅)
    """
    return (12 - ziwei_index) % 12


# 紫微星系：从紫微位置逆时针排列
# 口诀："紫微逆去天机星，隔一太阳武曲辰，连接天同空二宫，廉贞居处方是真"
# (name, offset) — 紫微位置减去 offset
_ZIWEI_GROUP = (
    ("紫微", 0),
    ("天机", 1),
    # 隔一
    ("太阳", 3),
    ("武曲", 4),
    ("天同", 5),
    # 空二宫
    ("廉贞", 8),
)

# 天府星系：从天府位置顺时针排列
# 口诀："天府顺行有太阴，贪狼而后巨门临，随来天相天梁继，七杀空三是破军"
# (name, offset) — 天府位置加上 offset
_TIANFU_GROUP = (
    ("天府", 0),
    ("太阴", 1),
    ("贪狼", 2),
    ("巨门", 3),
    ("天相", 4),
    ("天梁", 5),
    ("七杀", 6),
    # 空三宫
    ("破军", 10),
)


def place_major_stars(
    lunar_day: int,
    wu_xing_value: int,
) -> list[list[str]]:
    """
    安14主星到12宫。

    Args:
        lunar_day: 农历生日（1-30）
        wu_xing_value: 五行局数（2/3/4/5/6）

    Returns:
        12 个列表，每个列表包含该宫的主星名称。
        index 0 = 寅宫, index 1 = 卯宫, ..., index 11 = 丑宫。
        同宫时紫微星系在前，天府星系在后。
    """
    palaces: list[list[str]] = [[] for _ in range(12)]

    ziwei_idx = calc_ziwei_palace_index(lunar_day, wu_xing_value)
    tianfu_idx = calc_tianfu_palace_index(ziwei_idx)

    # 紫微星系：逆时针（减 offset）
    for name, offset in _ZIWEI_GROUP:
        idx = (ziwei_idx - offset) % 12
        palaces[idx].append(name)

    # 天府星系：顺时针（加 offset）
    for name, offset in _TIANFU_GROUP:
        idx = (tianfu_idx + offset) % 12
        palaces[idx].append(name)

    return palaces
