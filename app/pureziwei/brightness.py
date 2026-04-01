# -*- coding: utf-8 -*-
"""亮度计算：根据星曜名称和所在宫位查表返回亮度。"""
from __future__ import annotations

from .data.brightness_table import BRIGHTNESS


def get_brightness(star_name: str, palace_index: int) -> str | None:
    """
    查询星曜亮度。

    Args:
        star_name: 星曜名称
        palace_index: 宫位索引 (0=寅, ..., 11=丑)

    Returns:
        亮度字符串（庙/旺/得/利/平/不/陷/空字符串），无亮度数据返回 None。
    """
    table = BRIGHTNESS.get(star_name)
    if table is None:
        return None
    return table[palace_index]
