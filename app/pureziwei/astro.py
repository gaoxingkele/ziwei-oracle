# -*- coding: utf-8 -*-
"""
主入口类 Astro：串联所有模块完成排盘。
"""
from __future__ import annotations

from .calendar import solar_to_calendar_info, lunar_to_calendar_info, CalendarInfo
from .palace import build_palace_layout, PalaceLayout
from .stars_major import place_major_stars
from .stars_minor import place_minor_stars
from .stars_adjective import place_adjective_stars
from .brightness import get_brightness
from .mutagen import get_mutagens
from .auxiliary import place_changsheng12, place_boshi12, place_jiangqian12, place_suiqian12
from .horoscope import calc_direction, calc_decadal, calc_ages
from .models import (
    AstrolabeModel,
    PalaceModel,
    DecadalModel,
    StarModel,
    ConfigModel,
    GenderType,
    TimeIndexType,
    LanguageType,
)


def _find_palace_index(stars_list: list[list], star_name: str) -> int:
    """在星曜列表中查找指定星曜所在的 palace index。"""
    for i, sl in enumerate(stars_list):
        for s in sl:
            if s[0] == star_name:
                return i
    return -1


# 可参与四化的星（出现在四化表中的所有星）
_MUTAGEN_ELIGIBLE = frozenset({
    "紫微", "天机", "太阳", "武曲", "天同", "廉贞",
    "天府", "太阴", "贪狼", "巨门", "天相", "天梁", "七杀", "破军",
    "文昌", "文曲", "左辅", "右弼",
})


def _build_star_model(
    name: str,
    star_type: str,
    palace_index: int,
    mutagen_map: dict[str, str],
    scope: str = "origin",
) -> StarModel:
    """构建 StarModel，附加亮度和四化。"""
    brightness = get_brightness(name, palace_index)
    mutagen_value = mutagen_map.get(name)
    # 可四化星：mutagen="" 或实际值；不可四化星：mutagen=None
    if name in _MUTAGEN_ELIGIBLE:
        mutagen_display = mutagen_value if mutagen_value else ""
    else:
        mutagen_display = None

    return StarModel(
        name=name,
        type=star_type,
        scope=scope,
        brightness=brightness,
        mutagen=mutagen_display,
    )


class Astro:
    """紫微斗数排盘主类，API 兼容 py-iztro。"""

    def config(self, config: ConfigModel):
        """全局配置四化和亮度。"""
        from .config import get_global_config
        get_global_config().apply(config)

    def get_config(self) -> ConfigModel:
        """获取当前配置。"""
        from .config import get_global_config
        return get_global_config().to_model()

    def by_solar(
        self,
        solar_date_str: str,
        time_index: TimeIndexType,
        gender: GenderType,
        fix_leap: bool = True,
        language: LanguageType = "zh-CN",
    ) -> AstrolabeModel:
        """
        通过阳历获取星盘信息。

        Args:
            solar_date_str: 阳历日期【YYYY-M-D】
            time_index: 出生时辰序号【0~12】
            gender: 性别【男|女】
            fix_leap: 是否调整闰月情况
            language: 输出语言（暂仅支持 zh-CN）

        Returns:
            星盘模型
        """
        cal = solar_to_calendar_info(solar_date_str, time_index)
        return self._build_astrolabe(cal, gender)

    def by_lunar(
        self,
        lunar_date_str: str,
        time_index: TimeIndexType,
        gender: GenderType,
        fix_leap: bool = True,
        language: LanguageType = "zh-CN",
    ) -> AstrolabeModel:
        """通过农历获取星盘信息。"""
        cal = lunar_to_calendar_info(lunar_date_str, time_index)
        return self._build_astrolabe(cal, gender)

    def _build_astrolabe(self, cal: CalendarInfo, gender: str) -> AstrolabeModel:
        """核心排盘逻辑。"""
        lunar_month = abs(cal.lunar_month)

        # 1. 宫位布局
        layout = build_palace_layout(cal)

        # 2. 14主星
        major_stars = place_major_stars(cal.lunar_day, layout.five_elements_value)

        # 3. 14辅星
        minor_stars = place_minor_stars(
            cal.year_gan_index, cal.year_zhi_index, lunar_month, cal.time_index
        )

        # 4. 38杂耀
        adj_stars = place_adjective_stars(
            cal.year_gan_index, cal.year_zhi_index,
            lunar_month, cal.lunar_day, cal.time_index,
            layout.soul_palace_index, layout.body_palace_index,
            _find_palace_index(minor_stars, "左辅"),
            _find_palace_index(minor_stars, "右弼"),
            _find_palace_index(minor_stars, "文昌"),
            _find_palace_index(minor_stars, "文曲"),
        )

        # 5. 四化
        mutagen_map = get_mutagens(cal.year_gan_index)

        # 6. 方向（顺逆）
        direction = calc_direction(gender, cal.year_gan_index)
        is_clockwise = direction == 1

        # 7. 辅助12神
        changsheng = place_changsheng12(layout.five_elements_value, is_clockwise)
        lucun_idx = _find_palace_index(minor_stars, "禄存")
        boshi = place_boshi12(lucun_idx, is_clockwise)
        jiangqian = place_jiangqian12(cal.year_zhi_index)
        suiqian = place_suiqian12(cal.year_zhi_index)

        # 8. 大限
        palace_stems = [p.heavenly_stem for p in layout.palaces]
        decadals = calc_decadal(
            layout.soul_palace_index, layout.five_elements_value,
            direction, palace_stems
        )

        # 9. 小限
        ages = calc_ages(cal.year_zhi_index, gender, direction)

        # 10. 组装 PalaceModel
        palaces = []
        for i, p in enumerate(layout.palaces):
            # 主星
            major_list = [
                _build_star_model(name, "major", i, mutagen_map)
                for name in major_stars[i]
            ]
            # 辅星
            minor_list = [
                _build_star_model(name, stype, i, mutagen_map)
                for name, stype in minor_stars[i]
            ]
            # 杂耀
            adj_list = [
                _build_star_model(name, stype, i, mutagen_map)
                for name, stype in adj_stars[i]
            ]

            palaces.append(PalaceModel(
                index=i,
                name=p.name,
                isBodyPalace=p.is_body_palace,
                isOriginalPalace=p.is_original_palace,
                heavenlyStem=p.heavenly_stem,
                earthlyBranch=p.earthly_branch,
                majorStars=major_list,
                minorStars=minor_list,
                adjectiveStars=adj_list,
                changsheng12=changsheng[i],
                boshi12=boshi[i],
                jiangqian12=jiangqian[i],
                suiqian12=suiqian[i],
                decadal=DecadalModel(**decadals[i]),
                ages=ages[i],
            ))

        soul_branch = layout.palaces[layout.soul_palace_index].earthly_branch
        body_branch = layout.palaces[layout.body_palace_index].earthly_branch

        model = AstrolabeModel(
            gender=gender,
            solarDate=cal.solar_date_str,
            lunarDate=cal.lunar_date_str,
            chineseDate=cal.chinese_date_str,
            time=cal.time_name,
            timeRange=cal.time_range,
            sign=cal.sign,
            zodiac=cal.zodiac,
            earthlyBranchOfSoulPalace=soul_branch,
            earthlyBranchOfBodyPalace=body_branch,
            soul=layout.soul_star,
            body=layout.body_star,
            fiveElementsClass=layout.five_elements_class,
            palaces=palaces,
        )
        # 保存内部状态供 horoscope() 使用
        model._context = {
            "birth_cal": cal,
            "gender": gender,
            "direction": direction,
            "soul_palace_index": layout.soul_palace_index,
            "wu_xing_value": layout.five_elements_value,
            "palace_stems": palace_stems,
            "decadals": [d for d in decadals],
            "ages_table": ages,
        }
        return model
