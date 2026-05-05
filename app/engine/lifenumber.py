# -*- coding: utf-8 -*-
"""生命密码 (Life Number) 引擎 — 中文流派 (蔡光辉一脉)

输入: 公历生日 (YYYY-MM-DD)
输出: 三个核心数字
  - talent_number  天赋数 = 出生日期所有数字相加 (一般是 2 位数)
  - life_number    生命数 = 天赋数继续相加到一位; 11/22/33 大师数不还原
  - birthday_number 生日数 = 出生日 (1-31) 相加; 11/22 大师数不还原

每个数字 1-9 + 大师数 11/22/33 都有固定性格解读, 三种数字含义略有侧重:
  - 生命数: 此生主轴特质, 最稳重
  - 天赋数: 与生俱来潜能, 短期才华
  - 生日数: 个性外显, 给他人的印象
"""
from __future__ import annotations
import uuid
from typing import Any
from app.engine.registry import ChartRequest, ChartResult, register


# ── 1-9 + 大师数 11/22/33 核心解读 ────────────────────────────────
NUMBER_CORE: dict[int, dict[str, str]] = {
    1: {
        "title": "开创者 / 领导者",
        "essence": "独立、自信、有主见, 喜欢从无到有把事情做出来。",
        "strength": "决断力强、行动派、不畏开局难。",
        "shadow": "自我中心、不够耐烦、不擅长合作时容易硬扛。",
    },
    2: {
        "title": "协调者 / 共情者",
        "essence": "敏感细腻, 善于倾听, 在关系里寻找平衡。",
        "strength": "亲和、共情、懂照顾人, 适合做润滑剂。",
        "shadow": "犹豫不决、容易把别人需求放自己之前、内耗多。",
    },
    3: {
        "title": "表达者 / 创意者",
        "essence": "活泼乐观, 喜欢沟通和创造, 天生有魅力。",
        "strength": "想象力丰富、感染力强、社交能量充沛。",
        "shadow": "三分钟热度、说得比做得多、情绪起伏大。",
    },
    4: {
        "title": "建造者 / 实干家",
        "essence": "踏实稳重, 重纪律, 一步一脚印地把基础打牢。",
        "strength": "可靠、有耐心、把事情做细做实。",
        "shadow": "固执保守、抗拒变化、容易钻牛角尖。",
    },
    5: {
        "title": "自由人 / 探险家",
        "essence": "好奇心强, 喜欢变化和新体验, 不喜欢被规则束缚。",
        "strength": "适应力强、点子多、勇于尝试。",
        "shadow": "缺乏定力、贪图新鲜、对承诺不耐久。",
    },
    6: {
        "title": "守护者 / 责任者",
        "essence": "重情义、重家庭、把照顾他人当成自我实现。",
        "strength": "可靠、有责任感、富同情心、适合带团队或家。",
        "shadow": "爱操心、控制欲、把别人的人生扛在自己肩上。",
    },
    7: {
        "title": "思考者 / 智者",
        "essence": "内向、善思辨, 在自己的精神世界里寻找意义。",
        "strength": "洞察力深、独立思考、能看穿表象。",
        "shadow": "孤僻、多疑、习惯把感受藏起来不说。",
    },
    8: {
        "title": "成就者 / 实业家",
        "essence": "野心大、目标导向, 看重权力、地位和物质成就。",
        "strength": "执行力强、能扛压力、商业嗅觉敏锐。",
        "shadow": "急功近利、过度物质化、忽视情感面。",
    },
    9: {
        "title": "理想者 / 博爱者",
        "essence": "胸怀大格局、关心人类共同议题, 容易把自己投入到使命里。",
        "strength": "慈悲心、艺术感、有跨群体的影响力。",
        "shadow": "完美主义、易自我牺牲、对琐事不耐烦。",
    },
    11: {
        "title": "大师数 · 直觉者",
        "essence": "高度敏感的灵性数字, 直觉极强, 像 2 的升级版。",
        "strength": "灵感、洞察、有神秘感, 适合创作或精神工作。",
        "shadow": "情绪起伏剧烈、易焦虑, 需要稳定的内在练习。",
    },
    22: {
        "title": "大师数 · 实践者",
        "essence": "把宏大的愿景落地的能力, 像 4 + 11 的合体。",
        "strength": "格局大、能成事, 通常是改变行业或社会的角色。",
        "shadow": "压力极大、容易透支自己、害怕辜负使命。",
    },
    33: {
        "title": "大师数 · 守护者",
        "essence": "至高无私的爱与教导能量, 像 6 的升级版, 极罕见。",
        "strength": "感化、疗愈、用大爱影响他人。",
        "shadow": "自我牺牲过度、把别人的痛苦扛在自己身上。",
    },
}


def _reduce_to_digit(n: int, keep_master: bool = True) -> int:
    """持续相加到一位数; keep_master=True 时遇到 11/22/33 停止。"""
    while n > 9:
        if keep_master and n in (11, 22, 33):
            return n
        n = sum(int(c) for c in str(n))
    return n


def _calc(birth_date: str) -> dict[str, Any]:
    """从 'YYYY-MM-DD' 算三数。"""
    y, m, d = birth_date.split("-")
    digits_all = [int(c) for c in (y + m + d)]
    talent = sum(digits_all)               # 天赋数 (一般 2 位)
    life = _reduce_to_digit(talent)        # 生命数 (1-9 或 11/22/33)
    day_int = int(d)
    birthday_num = _reduce_to_digit(day_int)
    return {
        "birth_date": birth_date,
        "digits_string": "+".join(str(x) for x in digits_all),
        "talent_number": talent,
        "life_number": life,
        "birthday_number": birthday_num,
    }


def _interp(num: int) -> dict[str, str]:
    """取数字解读, 找不到时降到一位数兜底。"""
    if num in NUMBER_CORE:
        return NUMBER_CORE[num]
    # 未在表中则还原到一位 (例如 talent=12 -> 3)
    fallback = _reduce_to_digit(num, keep_master=False)
    return NUMBER_CORE.get(fallback, NUMBER_CORE[1])


def _build_text(d: dict[str, Any]) -> str:
    life = d["life_number"]
    talent = d["talent_number"]
    birthday = d["birthday_number"]
    life_i = _interp(life)
    talent_i = _interp(talent)
    birthday_i = _interp(birthday)
    is_master_life = life in (11, 22, 33)
    is_master_talent = talent in (11, 22, 33)
    is_master_bday = birthday in (11, 22)

    lines = [
        "══════════ 生命密码 ══════════",
        f"公历生日: {d['birth_date']}",
        f"算式: {d['digits_string']} = {talent} → {life}{'  ★大师数' if is_master_life else ''}",
        "",
        f"──── ① 生命数 {life} · {life_i['title']} ────",
        f"  本质: {life_i['essence']}",
        f"  优势: {life_i['strength']}",
        f"  阴影: {life_i['shadow']}",
        f"  ★ 此数代表此生主轴特质, 是最稳定的底色。",
        "",
        f"──── ② 天赋数 {talent}{' · ' + talent_i['title'] if is_master_talent else ''} ────",
        f"  含义: 与生俱来的潜能与天赋方向。",
    ]
    if is_master_talent:
        lines += [
            f"  本质: {talent_i['essence']}",
            f"  优势: {talent_i['strength']}",
            f"  阴影: {talent_i['shadow']}",
        ]
    elif talent < 10:
        # 一位数天赋数 (年月日和本身就 ≤ 9): 天赋 = 生命, 极简单一
        lines.append(f"  说明: 天赋数即生命数 {talent}, 此生天赋与主轴高度统一, 是更纯粹的「{talent_i['title']}」能量。")
    else:
        # 普通双位数天赋数: 拆开看两位数字的组合启示
        a, b = divmod(talent, 10)
        if b == 0:
            lines.append(f"  组合启示: 整十数, 单股「{NUMBER_CORE[a]['title']}」能量极致放大, 也意味着这股特质需要更强的自觉。")
        else:
            lines.append(f"  组合启示: 由 {a} 与 {b} 两股能量混合 — {NUMBER_CORE[a]['title']} + {NUMBER_CORE[b]['title']}。")

    lines += [
        "",
        f"──── ③ 生日数 {birthday} · {birthday_i['title']} ────",
        f"  含义: 个性外显, 给他人的第一印象与日常表现倾向。",
        f"  本质: {birthday_i['essence']}",
        f"  阴影: {birthday_i['shadow']}",
    ]

    lines += [
        "",
        "──── 综合解读 ────",
        f"  你这一生的主旋律是「{life_i['title']}」, "
        f"携带「{talent_i.get('title', '组合天赋') if is_master_talent else '混合潜能'}」入世, "
        f"日常则呈现「{birthday_i['title']}」的样子让别人看到。",
        f"  扬长建议: {life_i['strength']}",
        f"  避坑提醒: {life_i['shadow']}",
    ]

    return "\n".join(lines)


@register("lifenumber")
def calculate_lifenumber_engine(req: ChartRequest) -> ChartResult:
    if not req.birth_date or "-" not in req.birth_date:
        raise ValueError("生命密码需要公历生日 (YYYY-MM-DD)")
    data = _calc(req.birth_date)
    data["interpretations"] = {
        "life": _interp(data["life_number"]),
        "talent": _interp(data["talent_number"]),
        "birthday": _interp(data["birthday_number"]),
    }
    text = _build_text(data)
    return ChartResult(
        chart_id=f"ch_{uuid.uuid4().hex[:12]}",
        system="lifenumber",
        raw_data=data,
        text_summary=text,
    )
