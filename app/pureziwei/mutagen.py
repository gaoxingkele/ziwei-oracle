# -*- coding: utf-8 -*-
"""四化计算：根据年干查表返回四化星及其类型。"""
from __future__ import annotations

from .data.mutagen_table import MUTAGEN, MUTAGEN_NAMES


def get_mutagens(year_gan_index: int) -> dict[str, str]:
    """
    查询年干四化。

    Args:
        year_gan_index: 年干索引 (0=甲, ..., 9=癸)

    Returns:
        {星曜名称: 四化类型} 字典，如 {"太阳": "禄", "武曲": "权", ...}
    """
    stars = MUTAGEN[year_gan_index]
    return {star: hua for star, hua in zip(stars, MUTAGEN_NAMES)}
