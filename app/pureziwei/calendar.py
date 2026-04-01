# -*- coding: utf-8 -*-
"""
日历转换模块：阳历↔阴历，四柱计算，时辰处理。
封装内联的 _lunar 包，提供紫微斗数排盘所需的全部日历信息。
"""
from __future__ import annotations

from dataclasses import dataclass

from ._lunar import Solar, Lunar
from .data.constants import (
    GAN,
    ZHI,
    NAYIN,
    SHICHEN_NAME,
    SHICHEN_RANGE,
    TIME_INDEX_TO_ZHI_INDEX,
    XING_ZUO,
    nayin_to_wuxing,
)


@dataclass(frozen=True)
class CalendarInfo:
    """排盘所需的全部日历信息"""

    # 阳历
    solar_year: int
    solar_month: int
    solar_day: int

    # 阴历
    lunar_year: int
    lunar_month: int  # 负数表示闰月，如 -6 = 闰六月
    lunar_day: int

    # 四柱（干支）
    year_gan: str  # 年干
    year_zhi: str  # 年支
    month_gan: str  # 月干
    month_zhi: str  # 月支
    day_gan: str  # 日干
    day_zhi: str  # 日支
    hour_gan: str  # 时干
    hour_zhi: str  # 时支

    # 时辰
    time_index: int  # 0-12
    time_name: str  # 如 "寅时"
    time_range: str  # 如 "03:00~05:00"

    # 其他
    zodiac: str  # 生肖，如 "龙"
    sign: str  # 西洋星座，如 "狮子座"

    # 格式化输出
    solar_date_str: str  # "2000-8-16"
    lunar_date_str: str  # "二〇〇〇年七月十七"
    chinese_date_str: str  # "庚辰 甲申 丙午 庚寅"

    @property
    def year_gan_index(self) -> int:
        """年干索引 (0-based)"""
        return GAN.index(self.year_gan)

    @property
    def year_zhi_index(self) -> int:
        """年支索引 (0-based)"""
        return ZHI.index(self.year_zhi)

    @property
    def month_gan_index(self) -> int:
        return GAN.index(self.month_gan)

    @property
    def month_zhi_index(self) -> int:
        return ZHI.index(self.month_zhi)

    @property
    def day_gan_index(self) -> int:
        return GAN.index(self.day_gan)

    @property
    def day_zhi_index(self) -> int:
        return ZHI.index(self.day_zhi)

    @property
    def hour_gan_index(self) -> int:
        return GAN.index(self.hour_gan)

    @property
    def hour_zhi_index(self) -> int:
        return ZHI.index(self.hour_zhi)

    @property
    def month_zhi_index(self) -> int:
        return ZHI.index(self.month_zhi)

    @property
    def nayin(self) -> str:
        """年柱纳音，如 '白蜡金'"""
        return NAYIN[self.year_gan + self.year_zhi]

    @property
    def nayin_wuxing(self) -> str:
        """年柱纳音五行，如 '金'"""
        return nayin_to_wuxing(self.nayin)


def hour_to_time_index(hour: int) -> int:
    """
    将24小时制的小时数转换为时辰序号 (0-12)。

    映射规则：
        0点  → 0 (早子时)     1-2点  → 1 (丑时)
        3-4点 → 2 (寅时)      5-6点  → 3 (卯时)
        7-8点 → 4 (辰时)      9-10点 → 5 (巳时)
        11-12点 → 6 (午时)    13-14点 → 7 (未时)
        15-16点 → 8 (申时)    17-18点 → 9 (酉时)
        19-20点 → 10 (戌时)   21-22点 → 11 (亥时)
        23点 → 12 (晚子时)
    """
    if hour < 0 or hour > 23:
        raise ValueError(f"hour must be 0-23, got {hour}")
    if hour == 0:
        return 0  # 早子时
    if hour == 23:
        return 12  # 晚子时
    return (hour + 1) // 2


def _time_index_to_hour(time_index: int) -> int:
    """时辰序号转小时数，用于构造 Lunar 对象"""
    if time_index == 0:
        return 0  # 早子时 23:00-01:00，用 0 点
    elif time_index == 12:
        return 23  # 晚子时，用 23 点
    else:
        return time_index * 2 - 1  # 丑=1, 寅=3, 卯=5, ...


def _compute_time_ganzhi(day_gan_index: int, time_index: int) -> tuple[str, str]:
    """
    根据日干和时辰序号计算时柱干支。
    时干 = (日干序号 % 5 * 2 + 时支序号) % 10
    """
    zhi_index = TIME_INDEX_TO_ZHI_INDEX[time_index]
    gan_index = (day_gan_index % 5 * 2 + zhi_index) % 10
    return GAN[gan_index], ZHI[zhi_index]


def _format_lunar_date(lunar: Lunar) -> str:
    """格式化阴历日期，如 '二〇〇〇年七月十七'"""
    year_str = lunar.getYearInChinese()
    month_str = lunar.getMonthInChinese()
    day_str = lunar.getDayInChinese()
    # 闰月前面加"闰"
    if lunar.getMonth() < 0:
        return f"{year_str}年闰{month_str}月{day_str}"
    return f"{year_str}年{month_str}月{day_str}"


def _get_sign(solar: Solar) -> str:
    """获取西洋星座名称（带'座'）"""
    return solar.getXingZuo() + "座"


def solar_to_calendar_info(
    solar_date_str: str,
    time_index: int,
    *,
    year_divide: str = "normal",
) -> CalendarInfo:
    """
    从阳历日期和时辰序号计算排盘所需的全部日历信息。

    Args:
        solar_date_str: 阳历日期，格式 "YYYY-M-D"
        time_index: 时辰序号 0-12（0=早子，12=晚子）
        year_divide: 年分界方式，"normal"=正月初一，"exact"=立春

    Returns:
        CalendarInfo 对象
    """
    parts = solar_date_str.split("-")
    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])

    hour = _time_index_to_hour(time_index)
    solar = Solar.fromYmdHms(year, month, day, hour, 0, 0)
    lunar = Lunar.fromSolar(solar)

    # 四柱：使用 Exact 版本（以立春分界）
    if year_divide == "exact":
        year_gan_zhi = lunar.getYearInGanZhiExact()
    else:
        year_gan_zhi = lunar.getYearInGanZhiByLiChun()
    month_gan_zhi = lunar.getMonthInGanZhiExact()
    day_gan_zhi = lunar.getDayInGanZhiExact2()

    year_gan, year_zhi = year_gan_zhi[0], year_gan_zhi[1]
    month_gan, month_zhi = month_gan_zhi[0], month_gan_zhi[1]
    day_gan, day_zhi = day_gan_zhi[0], day_gan_zhi[1]

    day_gan_idx = GAN.index(day_gan)
    hour_gan, hour_zhi = _compute_time_ganzhi(day_gan_idx, time_index)

    # 生肖：跟随年柱地支
    zodiac = lunar.getYearShengXiaoExact() if year_divide == "exact" else lunar.getYearShengXiaoByLiChun()

    # 时辰名称
    time_name = SHICHEN_NAME[time_index] + "时"
    time_range = SHICHEN_RANGE[time_index]

    # 格式化
    solar_fmt = f"{year}-{month}-{day}"
    lunar_date_fmt = _format_lunar_date(lunar)
    chinese_date_fmt = f"{year_gan_zhi} {month_gan_zhi} {day_gan_zhi} {hour_gan}{hour_zhi}"

    return CalendarInfo(
        solar_year=year,
        solar_month=month,
        solar_day=day,
        lunar_year=lunar.getYear(),
        lunar_month=lunar.getMonth(),
        lunar_day=lunar.getDay(),
        year_gan=year_gan,
        year_zhi=year_zhi,
        month_gan=month_gan,
        month_zhi=month_zhi,
        day_gan=day_gan,
        day_zhi=day_zhi,
        hour_gan=hour_gan,
        hour_zhi=hour_zhi,
        time_index=time_index,
        time_name=time_name,
        time_range=time_range,
        zodiac=zodiac,
        sign=_get_sign(solar),
        solar_date_str=solar_fmt,
        lunar_date_str=lunar_date_fmt,
        chinese_date_str=chinese_date_fmt,
    )


def lunar_to_calendar_info(
    lunar_date_str: str,
    time_index: int,
    *,
    is_leap_month: bool = False,
    year_divide: str = "normal",
) -> CalendarInfo:
    """
    从阴历日期和时辰序号计算排盘所需的全部日历信息。

    Args:
        lunar_date_str: 阴历日期，格式 "YYYY-M-D"
        time_index: 时辰序号 0-12
        is_leap_month: 是否闰月
        year_divide: 年分界方式

    Returns:
        CalendarInfo 对象
    """
    parts = lunar_date_str.split("-")
    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])

    if is_leap_month:
        month = -month

    hour = _time_index_to_hour(time_index)
    lunar = Lunar.fromYmdHms(year, month, day, hour, 0, 0)
    solar = lunar.getSolar()

    # 复用 solar_to_calendar_info 的逻辑
    solar_date_str = f"{solar.getYear()}-{solar.getMonth()}-{solar.getDay()}"
    return solar_to_calendar_info(solar_date_str, time_index, year_divide=year_divide)
