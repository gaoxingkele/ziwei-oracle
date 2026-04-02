"""黄道吉日查询引擎 — 在日期范围内筛选适合特定事项的吉日"""
from __future__ import annotations
import uuid
from datetime import date, timedelta
from typing import Any
from app.engine.registry import ChartRequest, ChartResult, register
from app.lunar import Solar

# 常见事项别名映射（用户可能输入的口语 → 黄历标准术语）
_ACTIVITY_ALIAS = {
    "结婚": "嫁娶", "婚嫁": "嫁娶", "领证": "嫁娶",
    "搬家": "移徙", "搬迁": "移徙", "乔迁": "移徙",
    "入宅": "入宅", "进宅": "入宅",
    "开业": "开市", "开张": "开市", "开工": "开市",
    "装修": "修造", "盖房": "盖屋", "建房": "盖屋",
    "出行": "出行", "旅行": "出行", "出差": "出行",
    "签约": "立券", "签合同": "立券",
    "动土": "动土", "破土": "破土",
    "安葬": "安葬", "下葬": "安葬",
    "祈福": "祈福", "拜拜": "祈福",
    "开光": "开光",
    "纳财": "纳财", "收款": "纳财",
    "交易": "交易", "买卖": "交易",
    "求嗣": "求嗣", "求子": "求嗣",
    "安床": "安床",
    "裁衣": "裁衣",
    "理发": "理发", "剃头": "理发",
    "提车": "纳畜", "买车": "纳畜",
}

# 所有黄历支持的标准事项（用于模糊匹配）
_ALL_ACTIVITIES = [
    "嫁娶", "祭祀", "祈福", "求嗣", "开光", "出行", "解除", "动土",
    "起基", "开市", "交易", "立券", "纳财", "挂匾", "栽种", "入殓",
    "破土", "安葬", "移柩", "入宅", "移徙", "安床", "修造", "造庙",
    "盖屋", "竖柱", "上梁", "纳畜", "牧养", "冠笄", "会亲友", "进人口",
    "裁衣", "经络", "伐木", "架马", "作灶", "治病", "安机械", "造车器",
    "合帐", "开池", "补垣", "塞穴", "置产", "放水", "理发",
]


def _resolve_activity(raw: str) -> str:
    """将用户输入转为黄历标准术语。"""
    raw = raw.strip()
    if raw in _ACTIVITY_ALIAS:
        return _ACTIVITY_ALIAS[raw]
    # 已经是标准术语
    if raw in _ALL_ACTIVITIES:
        return raw
    # 模糊匹配：包含关系
    for act in _ALL_ACTIVITIES:
        if raw in act or act in raw:
            return act
    return raw


def _parse_date(s: str) -> date:
    parts = s.split("-")
    return date(int(parts[0]), int(parts[1]), int(parts[2]))


@register("jiri")
def calculate_jiri(req: ChartRequest) -> ChartResult:
    extra = req.extra
    activity_raw = req.question.strip() or extra.get("activity", "嫁娶")
    activity = _resolve_activity(activity_raw)

    start_str = extra.get("start_date", req.birth_date)
    end_str = extra.get("end_date", "")
    start = _parse_date(start_str)
    if end_str:
        end = _parse_date(end_str)
    else:
        end = start + timedelta(days=30)

    # 限制范围最多 180 天
    if (end - start).days > 180:
        end = start + timedelta(days=180)
    if end < start:
        start, end = end, start

    results = []
    current = start
    while current <= end:
        solar = Solar.fromYmd(current.year, current.month, current.day)
        lunar = solar.getLunar()
        yi = lunar.getDayYi()
        ji = lunar.getDayJi()

        if activity in yi and activity not in ji:
            results.append({
                "solar_date": str(solar),
                "lunar_date": str(lunar),
                "weekday": ["一", "二", "三", "四", "五", "六", "日"][current.weekday()],
                "gan_zhi": lunar.getDayInGanZhi(),
                "tian_shen": lunar.getDayTianShen(),
                "tian_shen_luck": lunar.getDayTianShenLuck(),
                "zhi_xing": lunar.getZhiXing(),
                "yi": yi,
                "ji": ji,
                "chong_desc": lunar.getDayChongDesc(),
                "sha": lunar.getDaySha(),
            })
        current += timedelta(days=1)

    data = {
        "activity": activity,
        "activity_raw": activity_raw,
        "start_date": str(start),
        "end_date": str(end),
        "total_days": (end - start).days + 1,
        "matches": results,
        "match_count": len(results),
    }
    text = _build_text(data)
    return ChartResult(
        chart_id=f"ch_{uuid.uuid4().hex[:12]}",
        system="jiri", raw_data=data, text_summary=text,
    )


def _build_text(d: dict[str, Any]) -> str:
    lines = [
        f"══════════ 黄道吉日查询 ══════════",
        f"查询事项: {d['activity']}"
        + (f" (原始输入: {d['activity_raw']})" if d['activity_raw'] != d['activity'] else ""),
        f"查询范围: {d['start_date']} ~ {d['end_date']} ({d['total_days']}天)",
        f"找到吉日: {d['match_count']} 个",
        "",
    ]

    if not d["matches"]:
        lines.append("该范围内未找到适合此事项的黄道吉日，建议扩大查询范围。")
    else:
        for i, m in enumerate(d["matches"], 1):
            yi_str = "、".join(m["yi"][:6])
            if len(m["yi"]) > 6:
                yi_str += "..."
            ji_str = "、".join(m["ji"][:4])
            if len(m["ji"]) > 4:
                ji_str += "..."
            lines.append(
                f"【{i}】{m['solar_date']} 周{m['weekday']}  "
                f"农历{m['lunar_date']}  {m['gan_zhi']}日"
            )
            lines.append(
                f"    {m['tian_shen']}({m['tian_shen_luck']}) "
                f"值星:{m['zhi_xing']}  "
                f"冲{m['chong_desc']}  煞{m['sha']}"
            )
            lines.append(f"    宜: {yi_str}")
            lines.append(f"    忌: {ji_str}")
            lines.append("")

    return "\n".join(lines)
