from __future__ import annotations
import uuid
from typing import Any
from app.engine.registry import ChartRequest, ChartResult, register

from ichingshifa.ichingshifa import Iching


@register("iching")
def calculate_iching(req: ChartRequest) -> ChartResult:
    ic = Iching()
    mode = req.extra.get("mode", "time")  # "time" 起卦 or "lookup" 查卦辞

    if mode == "lookup":
        gua_name = req.extra.get("gua", "乾")
        desc = ic.show_sixtyfourguadescription(gua_name)
        data = {"gua": gua_name, "description": desc}
        text = _build_lookup_text(gua_name, desc)
    else:
        parts = req.birth_date.split("-")
        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        hour, minute = _parse_hour_minute(req.birth_time)
        data = ic.qigua_time(year, month, day, hour, minute)
        text = _build_qigua_text(data)

    return ChartResult(
        chart_id=f"ch_{uuid.uuid4().hex[:12]}",
        system="iching", raw_data=data, text_summary=text,
    )


def _parse_hour_minute(time_str: str) -> tuple[int, int]:
    if ":" in time_str:
        h, m = time_str.split(":")
        return int(h), int(m)
    try:
        idx = int(time_str)
        return idx * 2 + 1, 0
    except ValueError:
        return 10, 0


def _build_qigua_text(d: dict[str, Any]) -> str:
    lines = ["══════════ 周易大衍筮法 ══════════"]
    lines.append(f"日期：{d.get('日期', '?')}")

    dayansf = d.get("大衍筮法", [])
    if dayansf and len(dayansf) >= 3:
        lines += [
            "",
            "──── 起卦 ────",
            f"  爻数：{dayansf[0]}",
            f"  本卦：{dayansf[1]}",
            f"  之卦：{dayansf[2]}",
        ]
        if len(dayansf) > 3 and isinstance(dayansf[3], dict):
            lines.append("  动爻爻辞：")
            for yao_idx, yao_text in dayansf[3].items():
                lines.append(f"    {yao_text}")

    for tag, key in [("本卦", "本卦"), ("之卦", "之卦")]:
        gua = d.get(key, {})
        if not gua:
            continue
        lines += ["", f"──── 【{tag}】{gua.get('卦', '?')} ────"]
        for field, label in [
            ("五星", "五星"), ("世應卦", "世应"), ("六親用神", "六亲用神"),
            ("納甲", "纳甲"), ("五行", "五行"), ("星宿", "星宿"),
        ]:
            v = gua.get(field)
            if v is None:
                continue
            if isinstance(v, (list, tuple)):
                v = "、".join(str(x) for x in v)
            elif isinstance(v, dict):
                v = "、".join(f"{k}={x}" for k, x in v.items())
            lines.append(f"  {label}：{v}")

    fei = d.get("飛神")
    if fei:
        if isinstance(fei, (list, tuple)):
            fei_str = "、".join(str(x) for x in fei)
        elif isinstance(fei, dict):
            fei_str = "、".join(f"{k}={v}" for k, v in fei.items())
        else:
            fei_str = str(fei)
        lines += ["", f"──── 飞神 ────", f"  {fei_str}"]

    return "\n".join(lines)


def _build_lookup_text(gua_name: str, desc: dict) -> str:
    lines = [f"----------{gua_name}卦----------"]
    if isinstance(desc, dict):
        for idx in sorted(desc.keys()):
            lines.append(desc[idx])
    return "\n".join(lines)
