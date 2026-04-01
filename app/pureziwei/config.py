# -*- coding: utf-8 -*-
"""
配置管理：四化表、亮度表、算法选择的全局配置。
"""
from __future__ import annotations

from .data.brightness_table import BRIGHTNESS as _DEFAULT_BRIGHTNESS
from .data.mutagen_table import MUTAGEN as _DEFAULT_MUTAGEN
from .models import ConfigModel, YearDivideEnum, AgeDivideEnum, AlgorithmEnum


class _Config:
    """全局配置单例。"""

    def __init__(self):
        self.mutagens: dict[str, list[str]] = {}  # 自定义四化覆盖
        self.brightness: dict[str, list[str]] = {}  # 自定义亮度覆盖
        self.year_divide: YearDivideEnum = YearDivideEnum.NORMAL
        self.age_divide: AgeDivideEnum = AgeDivideEnum.NORMAL
        self.horoscope_divide: YearDivideEnum = YearDivideEnum.NORMAL
        self.algorithm: AlgorithmEnum = AlgorithmEnum.DEFAULT

    def apply(self, config: ConfigModel):
        """应用配置。"""
        if config.mutagens:
            self.mutagens.update(config.mutagens)
        if config.brightness:
            self.brightness.update(config.brightness)
        if config.year_divide is not None:
            self.year_divide = config.year_divide
        if config.age_divide is not None:
            self.age_divide = config.age_divide
        if config.horoscope_divide is not None:
            self.horoscope_divide = config.horoscope_divide
        if config.algorithm is not None:
            self.algorithm = config.algorithm

    def to_model(self) -> ConfigModel:
        """导出为 ConfigModel。"""
        # 合并默认四化表 + 自定义覆盖
        from .data.constants import GAN
        full_mutagens = {}
        for i, stem in enumerate(GAN):
            stars = list(_DEFAULT_MUTAGEN[i])
            if stem in self.mutagens:
                stars = self.mutagens[stem]
            full_mutagens[stem] = stars

        # 合并默认亮度表 + 自定义覆盖
        full_brightness = {}
        for star, values in _DEFAULT_BRIGHTNESS.items():
            full_brightness[star] = list(values)
        for star, values in self.brightness.items():
            full_brightness[star] = list(values)

        return ConfigModel(
            mutagens=full_mutagens,
            brightness=full_brightness,
            yearDivide=self.year_divide,
            ageDivide=self.age_divide,
            horoscopeDivide=self.horoscope_divide,
            algorithm=self.algorithm,
        )


# 全局实例
_global_config = _Config()


def get_global_config() -> _Config:
    return _global_config
