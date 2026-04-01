# -*- coding: utf-8 -*-
"""
宫位模块：定命宫、排12宫、定五行局、命主身主。
"""
from __future__ import annotations

from dataclasses import dataclass

from .calendar import CalendarInfo
from .data.constants import (
    GAN,
    ZHI,
    NAYIN,
    PALACE_NAMES,
    SOUL_STAR,
    BODY_STAR,
    WU_XING_JU,
    TIME_INDEX_TO_ZHI_INDEX,
    nayin_to_wuxing,
)


@dataclass
class PalaceInfo:
    """单个宫位的基础信息"""
    index: int  # 0=寅宫, 1=卯宫, ..., 11=丑宫
    name: str  # 宫位名称（命宫/兄弟/...）
    heavenly_stem: str  # 天干
    earthly_branch: str  # 地支
    is_body_palace: bool  # 是否身宫
    is_original_palace: bool  # 是否来因宫


@dataclass
class PalaceLayout:
    """12宫排列结果"""
    palaces: list[PalaceInfo]  # 12个宫位，index 0=寅宫
    soul_palace_index: int  # 命宫在 palaces 中的 index
    body_palace_index: int  # 身宫在 palaces 中的 index
    five_elements_class: str  # 五行局名称，如 "木三局"
    five_elements_value: int  # 五行局数，如 3
    soul_star: str  # 命主星，如 "破军"
    body_star: str  # 身主星，如 "文昌"


def _zhi_index_to_palace_index(zhi_index: int) -> int:
    """地支索引(0-based, 子=0) → 宫位索引(0=寅)"""
    return (zhi_index - 2 + 12) % 12


def _palace_index_to_zhi_index(palace_index: int) -> int:
    """宫位索引(0=寅) → 地支索引(0-based, 子=0)"""
    return (palace_index + 2) % 12


def calc_soul_palace_zhi_index(lunar_month: int, time_index: int) -> int:
    """
    计算命宫地支索引。
    口诀：寅上起正月，顺数到生月，逆数到生时。

    Args:
        lunar_month: 农历月份（正数，闰月按原月算）
        time_index: 时辰序号 0-12

    Returns:
        地支索引 (0-based, 子=0, 丑=1, ..., 亥=11)
    """
    time_zhi_index = TIME_INDEX_TO_ZHI_INDEX[time_index]
    # 寅(2) + 月偏移(month-1) - 时偏移(time_zhi_index)
    return (2 + lunar_month - 1 - time_zhi_index + 12) % 12


def calc_body_palace_zhi_index(lunar_month: int, time_index: int) -> int:
    """
    计算身宫地支索引。
    口诀：寅上起正月，顺数到生月，顺数到生时。
    """
    time_zhi_index = TIME_INDEX_TO_ZHI_INDEX[time_index]
    return (2 + lunar_month - 1 + time_zhi_index) % 12


def calc_palace_stems(year_gan_index: int) -> list[str]:
    """
    计算12宫天干（五虎遁）。

    规则：甲/己年→寅起丙, 乙/庚→戊, 丙/辛→庚, 丁/壬→壬, 戊/癸→甲

    Args:
        year_gan_index: 年干索引 (0-based, 甲=0)

    Returns:
        12个天干，index 0=寅宫的天干
    """
    start_gan = ((year_gan_index % 5) * 2 + 2) % 10
    return [GAN[(start_gan + i) % 10] for i in range(12)]


def calc_five_elements(soul_stem: str, soul_branch: str) -> tuple[str, int]:
    """
    计算五行局。命宫天干+地支 → 查纳音 → 取五行 → 对应局数。

    Returns:
        (五行局名称, 局数) 如 ("木三局", 3)
    """
    gan_zhi = soul_stem + soul_branch
    nayin = NAYIN[gan_zhi]
    wuxing = nayin_to_wuxing(nayin)
    name, value = WU_XING_JU[wuxing]
    return name, value


def build_palace_layout(cal: CalendarInfo) -> PalaceLayout:
    """
    根据日历信息排出12宫布局。

    Args:
        cal: CalendarInfo 日历信息

    Returns:
        PalaceLayout 完整的宫位布局
    """
    # 闰月取绝对值
    lunar_month = abs(cal.lunar_month)

    # 1. 命宫、身宫地支
    soul_zhi = calc_soul_palace_zhi_index(lunar_month, cal.time_index)
    body_zhi = calc_body_palace_zhi_index(lunar_month, cal.time_index)

    soul_idx = _zhi_index_to_palace_index(soul_zhi)
    body_idx = _zhi_index_to_palace_index(body_zhi)

    # 2. 天干排列（五虎遁）
    stems = calc_palace_stems(cal.year_gan_index)

    # 3. 五行局（命宫天干+地支）
    soul_stem = stems[soul_idx]
    soul_branch = ZHI[soul_zhi]
    five_name, five_value = calc_five_elements(soul_stem, soul_branch)

    # 4. 来因宫：年干所在的宫位
    year_stem = cal.year_gan
    original_idx = stems.index(year_stem)
    # 如果年干出现两次（天干10个，宫12个），取第一个
    # 但需确认是从寅宫开始第一次出现的那个
    # 实际上天干10个循环排12宫，前10个唯一，后2个重复
    # 来因宫应该取 index < 10 的那个
    for i, s in enumerate(stems):
        if s == year_stem and i < 10:
            original_idx = i
            break

    # 5. 命主星、身主星
    soul_star = SOUL_STAR[ZHI[soul_zhi]]
    body_star = BODY_STAR[cal.year_zhi]

    # 6. 组装12宫
    palaces = []
    for i in range(12):
        zhi_idx = _palace_index_to_zhi_index(i)
        # 宫名 = 从命宫逆时针排列
        name_idx = (soul_idx - i + 12) % 12
        palaces.append(PalaceInfo(
            index=i,
            name=PALACE_NAMES[name_idx],
            heavenly_stem=stems[i],
            earthly_branch=ZHI[zhi_idx],
            is_body_palace=(i == body_idx),
            is_original_palace=(i == original_idx),
        ))

    return PalaceLayout(
        palaces=palaces,
        soul_palace_index=soul_idx,
        body_palace_index=body_idx,
        five_elements_class=five_name,
        five_elements_value=five_value,
        soul_star=soul_star,
        body_star=body_star,
    )
