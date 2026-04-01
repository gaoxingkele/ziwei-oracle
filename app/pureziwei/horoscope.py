# -*- coding: utf-8 -*-
"""
运限计算：大限、小限、流年/流月/流日/流时。
"""
from __future__ import annotations

from .data.constants import GAN, ZHI, PALACE_NAMES, TIME_INDEX_TO_ZHI_INDEX
from .data.mutagen_table import MUTAGEN, MUTAGEN_NAMES
from .stars_minor import _LUCUN, _TIANMA, _TIANKUI, _TIANYUE
from .stars_adjective import _NIANJIE
from .calendar import CalendarInfo, solar_to_calendar_info
from .models import StarModel, HoroscopeItemModel, HoroscopeItemAgeModel, HoroscopeItemYearlyModel, YearlyDecStarModel, HoroscopeModel
from .auxiliary import place_jiangqian12, place_suiqian12

# 小限起始宫位 by 年支 (palace index, 统一表，不分男女)
# 寅午戌→辰(2), 申子辰→戌(8), 巳酉丑→未(5), 亥卯未→丑(11)
_XIAOXIAN_START = (8, 5, 2, 11, 8, 5, 2, 11, 8, 5, 2, 11)
#                  子  丑  寅  卯   辰  巳  午  未   申  酉  戌  亥

# 文昌 by 天干 (palace index) — 用于流耀
_WENCHANG_BY_STEM = (3, 4, 6, 7, 6, 7, 9, 10, 0, 1)
# 甲→巳(3), 乙→午(4), 丙→申(6), 丁→酉(7), 戊→申(6),
# 己→酉(7), 庚→亥(9), 辛→子(10), 壬→寅(0), 癸→卯(1)

# 文曲 by 天干 (palace index) — 用于流耀
_WENQU_BY_STEM = (7, 6, 4, 3, 4, 3, 1, 0, 10, 9)
# 甲→酉(7), 乙→申(6), 丙→午(4), 丁→巳(3), 戊→午(4),
# 己→巳(3), 庚→卯(1), 辛→寅(0), 壬→子(10), 癸→亥(9)

# 流耀前缀
_SCOPE_PREFIX = {
    "decadal": "运",
    "yearly": "流",
    "monthly": "月",
    "daily": "日",
    "hourly": "时",
}


def is_yang_stem(gan_index: int) -> bool:
    return gan_index % 2 == 0


def calc_direction(gender: str, year_gan_index: int) -> int:
    """阳男阴女顺行(+1)，阴男阳女逆行(-1)。"""
    is_yang = is_yang_stem(year_gan_index)
    is_male = gender == "男"
    return 1 if is_male == is_yang else -1


def calc_decadal(
    soul_palace_index: int,
    wu_xing_value: int,
    direction: int,
    palace_stems: list[str],
) -> list[dict]:
    """计算12宫的大限。"""
    result = [None] * 12
    start_age = wu_xing_value
    for step in range(12):
        palace_idx = (soul_palace_index + step * direction) % 12
        age_start = start_age + step * 10
        age_end = age_start + 9
        zhi_idx = (palace_idx + 2) % 12
        result[palace_idx] = {
            "range": [age_start, age_end],
            "heavenlyStem": palace_stems[palace_idx],
            "earthlyBranch": ZHI[zhi_idx],
        }
    return result


def calc_ages(
    year_zhi_index: int,
    gender: str,
    direction: int,
    max_age: int = 120,
) -> list[list[int]]:
    """计算12宫的小限年龄列表。"""
    start = _XIAOXIAN_START[year_zhi_index]
    result: list[list[int]] = [[] for _ in range(12)]
    for age in range(1, max_age + 1):
        palace_idx = (start + (age - 1) * direction) % 12
        result[palace_idx].append(age)
    return result


def _palace_names_from(soul_idx: int) -> list[str]:
    """从命宫位置生成12宫名称列表（index 0=寅宫的名称）。"""
    result = [""] * 12
    for i in range(12):
        name_idx = (soul_idx - i + 12) % 12
        result[i] = PALACE_NAMES[name_idx]
    return result


def _place_period_stars(
    stem_index: int,
    branch_index: int,
    scope: str,
    include_nianjie: bool = False,
) -> list[list[StarModel]]:
    """
    安流耀（运限专用星）。

    Args:
        stem_index: 该运限天干 (0=甲)
        branch_index: 该运限地支 (0=子)
        scope: 作用范围 (decadal/yearly/monthly/daily/hourly)
        include_nianjie: 是否包含年解（流年专用）
    """
    palaces: list[list[StarModel]] = [[] for _ in range(12)]
    prefix = _SCOPE_PREFIX[scope]
    branch_palace = (branch_index - 2 + 12) % 12  # ZHI → palace

    def put(palace_idx: int, short_name: str, star_type: str):
        name = f"{prefix}{short_name}"
        palaces[palace_idx % 12].append(StarModel(
            name=name, type=star_type, scope=scope,
            brightness=None, mutagen=None,
        ))

    # 安星顺序与 iztro 保持一致（soft 在 tough 前）
    lucun_idx = _LUCUN[stem_index]
    # 1. 禄存
    put(lucun_idx, "禄", "lucun")
    # 2. 天马
    put(_TIANMA[branch_index], "马", "tianma")
    # 3. 文昌 by stem
    put(_WENCHANG_BY_STEM[stem_index], "昌", "soft")
    # 4. 文曲 by stem
    put(_WENQU_BY_STEM[stem_index], "曲", "soft")
    # 5. 天魁 by stem
    put(_TIANKUI[stem_index], "魁", "soft")
    # 天钺 by stem
    put(_TIANYUE[stem_index], "钺", "soft")
    # 擎羊（tough 在 soft 后、flower 前）
    put((lucun_idx + 1) % 12, "羊", "tough")
    # 陀罗
    put((lucun_idx - 1 + 12) % 12, "陀", "tough")
    # 红鸾 by branch
    hongluan_idx = (1 - branch_index + 12) % 12
    put(hongluan_idx, "鸾", "flower")
    # 天喜
    put((hongluan_idx + 6) % 12, "喜", "flower")

    # 年解（仅流年）
    if include_nianjie:
        nianjie_idx = _NIANJIE[branch_index]
        palaces[nianjie_idx % 12].append(StarModel(
            name="年解", type="helper", scope=scope,
            brightness=None, mutagen=None,
        ))

    return palaces


def _get_mutagen_stars(stem_index: int) -> list[str]:
    """获取四化星名列表。"""
    return list(MUTAGEN[stem_index])


def calc_horoscope(
    birth_cal: CalendarInfo,
    birth_gender: str,
    birth_direction: int,
    soul_palace_index: int,
    wu_xing_value: int,
    palace_stems: list[str],
    decadals: list[dict],
    ages_table: list[list[int]],
    horoscope_date: str,
    horoscope_time_index: int = 0,
) -> HoroscopeModel:
    """
    计算运限。

    Args:
        birth_cal: 出生日历信息
        birth_gender: 性别
        birth_direction: 顺逆方向
        soul_palace_index: 原盘命宫 palace index
        wu_xing_value: 五行局数
        palace_stems: 12宫天干列表
        decadals: 大限数据
        ages_table: 小限年龄表
        horoscope_date: 运限日期 "YYYY-M-D"
        horoscope_time_index: 运限时辰 0-12

    Returns:
        HoroscopeModel
    """
    # 运限日期的日历信息
    h_cal = solar_to_calendar_info(horoscope_date, horoscope_time_index)
    h_lunar_month = abs(h_cal.lunar_month)

    # === 流年 ===
    # 流年干支 = 运限日期的年干支（以立春分界，使用 ByLiChun）
    yearly_gan_idx = h_cal.year_gan_index
    yearly_zhi_idx = h_cal.year_zhi_index
    yearly_soul_idx = (yearly_zhi_idx - 2 + 12) % 12  # 流年命宫 = 年支的 palace

    yearly = HoroscopeItemYearlyModel(
        index=yearly_soul_idx,
        name="流年",
        heavenlyStem=h_cal.year_gan,
        earthlyBranch=h_cal.year_zhi,
        palaceNames=_palace_names_from(yearly_soul_idx),
        mutagen=_get_mutagen_stars(yearly_gan_idx),
        stars=_place_period_stars(yearly_gan_idx, yearly_zhi_idx, "yearly", include_nianjie=True),
        yearlyDecStar=YearlyDecStarModel(
            jiangqian12=place_jiangqian12(yearly_zhi_idx),
            suiqian12=place_suiqian12(yearly_zhi_idx),
        ),
    )

    # === 大限 ===
    # 虚岁 = 流年农历年 - 出生农历年 + 1
    nominal_age = h_cal.lunar_year - birth_cal.lunar_year + 1
    # 找到对应的大限宫位
    decadal_idx = -1
    for i, d in enumerate(decadals):
        if d["range"][0] <= nominal_age <= d["range"][1]:
            decadal_idx = i
            break
    if decadal_idx == -1:
        # fallback: 使用命宫
        decadal_idx = soul_palace_index

    dec_stem = palace_stems[decadal_idx]
    dec_branch_zhi = (decadal_idx + 2) % 12
    dec_gan_idx = GAN.index(dec_stem)

    decadal = HoroscopeItemModel(
        index=decadal_idx,
        name="大限",
        heavenlyStem=dec_stem,
        earthlyBranch=ZHI[dec_branch_zhi],
        palaceNames=_palace_names_from(decadal_idx),
        mutagen=_get_mutagen_stars(dec_gan_idx),
        stars=_place_period_stars(dec_gan_idx, dec_branch_zhi, "decadal"),
    )

    # === 小限 ===
    age_palace_idx = -1
    for i, age_list in enumerate(ages_table):
        if nominal_age in age_list:
            age_palace_idx = i
            break
    if age_palace_idx == -1:
        age_palace_idx = _XIAOXIAN_START[birth_cal.year_zhi_index]

    age_stem = palace_stems[age_palace_idx]
    age_branch_zhi = (age_palace_idx + 2) % 12
    age_gan_idx = GAN.index(age_stem)

    age = HoroscopeItemAgeModel(
        index=age_palace_idx,
        name="小限",
        heavenlyStem=age_stem,
        earthlyBranch=ZHI[age_branch_zhi],
        palaceNames=_palace_names_from(age_palace_idx),
        mutagen=_get_mutagen_stars(age_gan_idx),
        stars=[],
        nominalAge=nominal_age,
    )

    # === 流月 ===
    birth_month = abs(birth_cal.lunar_month)
    birth_time_zhi = TIME_INDEX_TO_ZHI_INDEX[birth_cal.time_index]
    monthly_soul_idx = (yearly_soul_idx - birth_month + birth_time_zhi + h_lunar_month + 12) % 12

    monthly_gan_idx = h_cal.month_gan_index
    monthly_zhi_idx = h_cal.month_zhi_index

    monthly = HoroscopeItemModel(
        index=monthly_soul_idx,
        name="流月",
        heavenlyStem=h_cal.month_gan,
        earthlyBranch=h_cal.month_zhi,
        palaceNames=_palace_names_from(monthly_soul_idx),
        mutagen=_get_mutagen_stars(monthly_gan_idx),
        stars=_place_period_stars(monthly_gan_idx, monthly_zhi_idx, "monthly"),
    )

    # === 流日 ===
    daily_soul_idx = (monthly_soul_idx + h_cal.lunar_day - 1) % 12

    daily_gan_idx = h_cal.day_gan_index
    daily_zhi_idx = h_cal.day_zhi_index

    daily = HoroscopeItemModel(
        index=daily_soul_idx,
        name="流日",
        heavenlyStem=h_cal.day_gan,
        earthlyBranch=h_cal.day_zhi,
        palaceNames=_palace_names_from(daily_soul_idx),
        mutagen=_get_mutagen_stars(daily_gan_idx),
        stars=_place_period_stars(daily_gan_idx, daily_zhi_idx, "daily"),
    )

    # === 流时 ===
    h_time_zhi = TIME_INDEX_TO_ZHI_INDEX[horoscope_time_index]
    hourly_soul_idx = (daily_soul_idx + h_time_zhi) % 12

    hourly_gan_idx = h_cal.hour_gan_index
    hourly_zhi_idx = h_cal.hour_zhi_index

    hourly = HoroscopeItemModel(
        index=hourly_soul_idx,
        name="流时",
        heavenlyStem=h_cal.hour_gan,
        earthlyBranch=h_cal.hour_zhi,
        palaceNames=_palace_names_from(hourly_soul_idx),
        mutagen=_get_mutagen_stars(hourly_gan_idx),
        stars=_place_period_stars(hourly_gan_idx, hourly_zhi_idx, "hourly"),
    )

    return HoroscopeModel(
        lunarDate=h_cal.lunar_date_str,
        solarDate=h_cal.solar_date_str,
        decadal=decadal,
        age=age,
        yearly=yearly,
        monthly=monthly,
        daily=daily,
        hourly=hourly,
    )
