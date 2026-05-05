# -*- coding: utf-8 -*-
"""生命密码流年时运 (lifenumber_period) — 个人年 / 个人月 / 个人日。

毕达哥拉斯派标准算法:
  - 个人年 = (出生月数字 + 出生日数字 + 当前年份数字) 全加到一位
  - 个人月 = 个人年 + 当前月数字
  - 个人日 = 个人月 + 当前日数字

流年场景大师数 (11/22/33) 不保留, 一律还原到一位 (流年本就九年循环, 大师数
反而打乱节奏).

依赖: app/engine/calendar.resolve_calendar (复用时间表达式解析).
"""
from __future__ import annotations
from datetime import date, datetime
from typing import Any

from app.engine.calendar import resolve_calendar


# ── 1-9 个人年解读 (核心主题 + 关键词 + 宜/忌) ────────────────────
YEAR_THEME: dict[int, dict[str, Any]] = {
    1: {
        "title": "起始年 · 播种",
        "keywords": ["新开始", "立项", "独立", "主动出击"],
        "essence": "九年循环的开端, 一切重新开始。适合启动新阶段, 哪怕看不清结果也要先迈第一步。",
        "do": ["开新项目/换工作/创业", "学新技能", "建立独立的判断和习惯"],
        "avoid": ["拖延等观望", "凡事征求他人意见", "守在已不喜欢的旧关系/旧位置"],
    },
    2: {
        "title": "合作年 · 等待",
        "keywords": ["合伙", "关系", "耐心", "感情突破"],
        "essence": "节奏放慢的一年, 单干不利, 合作出彩。感情和合伙人议题特别明显。",
        "do": ["谈合作签合同", "处理积压的人际关系", "感情上前进或断舍"],
        "avoid": ["独断独行", "急于求成", "和盟友翻脸"],
    },
    3: {
        "title": "表达年 · 社交",
        "keywords": ["创意", "曝光", "玩乐", "多说多写"],
        "essence": "能量外放的一年。说话、写作、自媒体、社交场合都有特别的吸引力, 适合做自己的品牌。",
        "do": ["公开演讲/写作/直播", "拓展社交圈", "做有趣的副业"],
        "avoid": ["分散精力面面俱到", "光说不练", "情绪波动后退缩"],
    },
    4: {
        "title": "实干年 · 打基础",
        "keywords": ["纪律", "苦干", "储蓄", "健康"],
        "essence": "节奏踏实的一年。要有耐心打基础, 不易看到亮眼成绩, 但每一步都在积累。",
        "do": ["把工作流程做细", "存钱买保险定财务计划", "锻炼身体每周稳定运动"],
        "avoid": ["投机取巧", "频繁跳槽搬家", "对慢节奏失去耐性"],
    },
    5: {
        "title": "变化年 · 自由",
        "keywords": ["跳槽", "搬家", "旅行", "新体验"],
        "essence": "动荡的一年, 旧的不再适用, 新的还没成形。拥抱变化反而轻松, 抗拒会很累。",
        "do": ["旅行/出差/换城市", "考虑换工作或调岗", "尝试新爱好"],
        "avoid": ["签长期合同", "重大投资", "婚姻大事仓促决定"],
    },
    6: {
        "title": "责任年 · 家庭",
        "keywords": ["婚嫁", "买房", "亲子", "扛责任"],
        "essence": "家庭和承诺议题的一年。婚姻、孩子、房子、照顾父母这些重头议题集中出现。",
        "do": ["谈婚论嫁/买房安家", "陪伴家人", "承担更多责任并享受其中"],
        "avoid": ["逃避亲密关系", "推卸家庭责任", "操控他人想替别人做主"],
    },
    7: {
        "title": "内省年 · 学习",
        "keywords": ["读书", "独处", "灵性", "深度思考"],
        "essence": "向内走的一年。表面热闹反而焦虑, 沉静读书冥想反而通透。是为下一阶段储备智慧的时机。",
        "do": ["系统读书/进修/写作", "独处冥想瑜伽", "深度复盘自己"],
        "avoid": ["逼自己社交", "做需要大量曝光的事", "因孤独感乱交友"],
    },
    8: {
        "title": "收获年 · 财权",
        "keywords": ["赚钱", "升迁", "权力", "签大单"],
        "essence": "九年循环里物质能量最强的一年。前几年的积累在此变现, 也是下决心做大事的一年。",
        "do": ["谈钱谈条件不退让", "争取升迁/项目主导权", "做大额投资但要算账"],
        "avoid": ["怕谈钱羞于争取", "贪心过度赌一把", "用权力压人"],
    },
    9: {
        "title": "了结年 · 释放",
        "keywords": ["断舍离", "总结", "告别", "宽恕"],
        "essence": "九年循环的尾声。不该带走的人事物在此告别, 旧账要结清, 心态要清空, 才能迎接下一个 1 年。",
        "do": ["做年度大复盘", "原谅旧人放下旧事", "捐赠/义工/利他行为"],
        "avoid": ["开启重大新项目", "纠结小事不放手", "因失去而怨恨"],
    },
}


# ── 1-9 个人月主题 (与年呼应, 但更细) ─────────────────────────────
MONTH_THEME: dict[int, str] = {
    1: "本月主开局, 适合启动新事项",
    2: "本月主关系, 合作与感情议题突出",
    3: "本月主表达, 多说多写人气旺",
    4: "本月主实干, 埋头做事最稳",
    5: "本月主变化, 突发情况多, 灵活应对",
    6: "本月主家事, 家庭与责任议题集中",
    7: "本月主沉静, 适合学习独处",
    8: "本月主财运, 谈钱争权的好时机",
    9: "本月主收尾, 处理积压、清理旧事",
}


# ── 1-9 个人日主题 (短决策导向) ────────────────────────────────────
DAY_THEME: dict[int, str] = {
    1: "今日宜开始, 主动出击",
    2: "今日宜合作, 慢一点听他人",
    3: "今日宜社交, 多说多笑",
    4: "今日宜踏实, 完成手头事",
    5: "今日多变, 灵活反应",
    6: "今日宜家事, 关注亲人",
    7: "今日宜独处, 安静思考",
    8: "今日宜谈钱, 抓住机会",
    9: "今日宜收尾, 不开新项",
}


# ── 算法 ──────────────────────────────────────────────────────────
def _reduce(n: int) -> int:
    """流年场景: 一律还原到一位 (不保留大师数)。"""
    while n > 9:
        n = sum(int(c) for c in str(n))
    return n


def _personal_year(birth_month: int, birth_day: int, year: int) -> int:
    return _reduce(birth_month + birth_day + year)


def _personal_month(personal_year: int, month: int) -> int:
    return _reduce(personal_year + month)


def _personal_day(personal_month: int, day: int) -> int:
    return _reduce(personal_month + day)


# ── 时间表达式 → 代表日期 + 粒度 ──────────────────────────────────
def _resolve_period(expr: str, base_date: str) -> tuple[date, str, dict]:
    """解析 expr, 返回 (代表日, 粒度, 原始解析结果)。"""
    resolved = resolve_calendar(expr=expr, base_date=base_date, view="raw", granularity="auto")
    if resolved.get("error"):
        raise ValueError(resolved.get("hint", f"无法解析: {expr}"))
    g = resolved.get("resolved", {}).get("gregorian", [])
    if not g or len(g) != 2:
        raise ValueError(f"无法解析: {expr}")
    sp = g[0].split("-")
    ep = g[1].split("-")
    start = date(int(sp[0]), int(sp[1]), int(sp[2]))
    end = date(int(ep[0]), int(ep[1]), int(ep[2]))
    span_days = (end - start).days

    # 自动选粒度
    if span_days >= 60:
        gran = "year"
        rep = start + (end - start) / 2  # 中点代表
    elif span_days >= 7:
        gran = "month"
        rep = start + (end - start) / 2
    else:
        gran = "day"
        rep = start
    if isinstance(rep, datetime):
        rep = rep.date()
    return rep, gran, resolved


# ── 主入口 ────────────────────────────────────────────────────────
def calculate_lifenumber_period(
    profile: dict,
    expr: str,
    base_date: str = "",
    granularity: str = "auto",
) -> dict[str, Any]:
    """主函数: 给定 profile + 时间表达式, 返回该时段的个人年/月/日运势。"""
    birthday = profile.get("birthday") or profile.get("birth_date") or ""
    if not birthday or "-" not in birthday:
        return {
            "error": "profile_incomplete",
            "hint": f"用户档案不完整: device_id={profile.get('device_id')}, 缺公历生日。",
        }

    try:
        parts = birthday.split("-")
        b_y, b_m, b_d = int(parts[0]), int(parts[1]), int(parts[2])
    except Exception:
        return {"error": "bad_birthday", "hint": f"生日格式错: {birthday}"}

    try:
        rep_date, auto_gran, resolved = _resolve_period(expr, base_date)
    except ValueError as e:
        return {"error": "calendar_resolve_failed", "hint": str(e)}

    # 强制粒度 (LLM 显式指定)
    use_gran = granularity if granularity in ("year", "month", "day") else auto_gran

    # 算三层数字
    py = _personal_year(b_m, b_d, rep_date.year)
    pm = _personal_month(py, rep_date.month) if use_gran in ("month", "day") else None
    pd = _personal_day(pm, rep_date.day) if (use_gran == "day" and pm is not None) else None

    # 解读
    yt = YEAR_THEME[py]
    interp = {"year": yt}
    summary_parts = [
        f"{rep_date.year} 年是你的【{py} 年 · {yt['title']}】"
    ]
    if pm is not None:
        interp["month"] = {"number": pm, "theme": MONTH_THEME[pm]}
        summary_parts.append(f"{rep_date.month} 月主【{pm} 月】 — {MONTH_THEME[pm]}")
    if pd is not None:
        interp["day"] = {"number": pd, "theme": DAY_THEME[pd]}
        summary_parts.append(f"{rep_date.day} 日主【{pd} 日】 — {DAY_THEME[pd]}")

    summary_parts.append(f"主题: {yt['essence']}")

    return {
        "birthday": birthday,
        "period": {
            "expr": expr,
            "gregorian": resolved.get("resolved", {}).get("gregorian"),
            "granularity": use_gran,
            "representative_date": rep_date.isoformat(),
        },
        "personal_year": py,
        "personal_month": pm,
        "personal_day": pd,
        "interpretations": interp,
        "recommendations": {"do": yt["do"], "avoid": yt["avoid"]},
        "summary": " | ".join(summary_parts),
    }
