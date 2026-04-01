# -*- coding: utf-8 -*-
"""
Pydantic 数据模型，对齐 py-iztro 的字段名和类型（含 camelCase alias）。
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, PrivateAttr

TimeIndexType = Literal[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
GenderType = Literal["男", "女"]
LanguageType = Literal["en-US", "ja-JP", "ko-KR", "zh-CN", "zh-TW", "vi-VN"]
StarType = Literal["major", "soft", "tough", "adjective", "flower", "helper", "lucun", "tianma"]


class StarModel(BaseModel):
    """星耀模型"""

    name: str = Field(alias="name", title="星耀名字")
    type: StarType = Field(alias="type", title="星耀类型")
    scope: str = Field(alias="scope", title="作用范围")
    brightness: str | None = Field(alias="brightness", default=None, title="星耀亮度")
    mutagen: str | None = Field(alias="mutagen", default=None, title="四化")

    model_config = {"populate_by_name": True}


class DecadalModel(BaseModel):
    """大限模型"""

    range: list[int] = Field(alias="range", title="大限起止年龄 [起始, 截止]")
    heavenly_stem: str = Field(alias="heavenlyStem", title="大限天干")
    earthly_branch: str = Field(alias="earthlyBranch", title="大限地支")

    model_config = {"populate_by_name": True}


class PalaceModel(BaseModel):
    """宫位模型"""

    index: int = Field(alias="index", title="宫位索引")
    name: str = Field(alias="name", title="宫位名称")
    is_body_palace: bool = Field(alias="isBodyPalace", default=False, title="是否身宫")
    is_original_palace: bool = Field(alias="isOriginalPalace", default=False, title="是否来因宫")
    heavenly_stem: str = Field(alias="heavenlyStem", title="宫位天干")
    earthly_branch: str = Field(alias="earthlyBranch", title="宫位地支")
    major_stars: list[StarModel] = Field(alias="majorStars", default_factory=list, title="主星")
    minor_stars: list[StarModel] = Field(alias="minorStars", default_factory=list, title="辅星")
    adjective_stars: list[StarModel] = Field(alias="adjectiveStars", default_factory=list, title="杂耀")
    changsheng12: str = Field(alias="changsheng12", default="", title="长生12神")
    boshi12: str = Field(alias="boshi12", default="", title="博士12神")
    jiangqian12: str = Field(alias="jiangqian12", default="", title="将前12神")
    suiqian12: str = Field(alias="suiqian12", default="", title="岁前12神")
    decadal: DecadalModel = Field(alias="decadal", title="大限")
    ages: list[int] = Field(alias="ages", default_factory=list, title="小限")

    model_config = {"populate_by_name": True}


class AstrolabeModel(BaseModel):
    """星盘模型"""

    gender: str = Field(alias="gender", title="性别")
    solar_date: str = Field(alias="solarDate", title="阳历日期")
    lunar_date: str = Field(alias="lunarDate", title="农历日期")
    chinese_date: str = Field(alias="chineseDate", title="干支纪年日期")
    time: str = Field(alias="time", title="时辰")
    time_range: str = Field(alias="timeRange", title="时辰对应时间段")
    sign: str = Field(alias="sign", title="星座")
    zodiac: str = Field(alias="zodiac", title="生肖")
    earthly_branch_of_soul_palace: str = Field(alias="earthlyBranchOfSoulPalace", title="命宫地支")
    earthly_branch_of_body_palace: str = Field(alias="earthlyBranchOfBodyPalace", title="身宫地支")
    soul: str = Field(alias="soul", title="命主")
    body: str = Field(alias="body", title="身主")
    five_elements_class: str = Field(alias="fiveElementsClass", title="五行局")
    palaces: list[PalaceModel] = Field(alias="palaces", title="十二宫数据")

    # 内部状态（不序列化），用于 horoscope() 方法
    _context: dict[str, Any] = PrivateAttr(default_factory=dict)

    model_config = {"populate_by_name": True}

    def horoscope(self, date: str | None = None, time_index: int | None = None) -> "HoroscopeModel":
        """
        获取运限数据。

        Args:
            date: 阳历日期，默认当天
            time_index: 时辰索引 0-12，默认 0
        """
        from .horoscope import calc_horoscope
        from datetime import datetime

        if date is None:
            now = datetime.now()
            date = f"{now.year}-{now.month}-{now.day}"
        if time_index is None:
            time_index = 0

        ctx = self._context
        return calc_horoscope(
            birth_cal=ctx["birth_cal"],
            birth_gender=ctx["gender"],
            birth_direction=ctx["direction"],
            soul_palace_index=ctx["soul_palace_index"],
            wu_xing_value=ctx["wu_xing_value"],
            palace_stems=ctx["palace_stems"],
            decadals=ctx["decadals"],
            ages_table=ctx["ages_table"],
            horoscope_date=date,
            horoscope_time_index=time_index,
        )


class HoroscopeItemModel(BaseModel):
    """运限对象模型"""

    index: int = Field(alias="index", title="所在宫位索引")
    name: str = Field(alias="name", title="运限名称")
    heavenly_stem: str = Field(alias="heavenlyStem", title="天干")
    earthly_branch: str = Field(alias="earthlyBranch", title="地支")
    palace_names: list[str] = Field(alias="palaceNames", title="十二宫")
    mutagen: list[str] = Field(alias="mutagen", title="四化星")
    stars: list[list[StarModel]] | None = Field(alias="stars", default=None, title="流耀")

    model_config = {"populate_by_name": True}


class HoroscopeItemAgeModel(HoroscopeItemModel):
    """运限小限模型"""

    nominal_age: int = Field(alias="nominalAge", title="虚岁")


class YearlyDecStarModel(BaseModel):
    """流年12神模型"""

    jiangqian12: list[str] = Field(alias="jiangqian12", title="将前12神")
    suiqian12: list[str] = Field(alias="suiqian12", title="岁前12神")

    model_config = {"populate_by_name": True}


class HoroscopeItemYearlyModel(HoroscopeItemModel):
    """运限流年模型"""

    yearly_dec_star: YearlyDecStarModel = Field(alias="yearlyDecStar", title="流年12神")


class HoroscopeModel(BaseModel):
    """运限模型"""

    lunar_date: str = Field(alias="lunarDate", title="农历日期")
    solar_date: str = Field(alias="solarDate", title="阳历日期")
    decadal: HoroscopeItemModel = Field(alias="decadal", title="大限")
    age: HoroscopeItemAgeModel = Field(alias="age", title="小限")
    yearly: HoroscopeItemYearlyModel = Field(alias="yearly", title="流年")
    monthly: HoroscopeItemModel = Field(alias="monthly", title="流月")
    daily: HoroscopeItemModel = Field(alias="daily", title="流日")
    hourly: HoroscopeItemModel = Field(alias="hourly", title="流时")

    model_config = {"populate_by_name": True}


class YearDivideEnum(str, Enum):
    NORMAL = "normal"
    EXACT = "exact"


class AgeDivideEnum(str, Enum):
    NORMAL = "normal"
    BIRTHDAY = "birthday"


class AlgorithmEnum(str, Enum):
    DEFAULT = "default"
    ZHONGZHOU = "zhongzhou"


class ConfigModel(BaseModel):
    """配置模型"""

    mutagens: dict[str, list[str]] | None = Field(default_factory=dict, title="四化表")
    brightness: dict[str, list[str]] | None = Field(default_factory=dict, title="亮度表")
    year_divide: YearDivideEnum | None = Field(default=YearDivideEnum.NORMAL, alias="yearDivide")
    age_divide: AgeDivideEnum | None = Field(default=AgeDivideEnum.NORMAL, alias="ageDivide")
    horoscope_divide: YearDivideEnum | None = Field(default=YearDivideEnum.NORMAL, alias="horoscopeDivide")
    algorithm: AlgorithmEnum | None = Field(default=AlgorithmEnum.DEFAULT)

    model_config = {"populate_by_name": True}
