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
    lines = ["----------周易筮法----------"]
    lines.append(f"日期：{d.get('日期', '未知')}")

    dayansf = d.get("大衍筮法", [])
    if dayansf and len(dayansf) >= 3:
        lines.append(f"爻数：{dayansf[0]}")
        lines.append(f"本卦：{dayansf[1]}")
        lines.append(f"之卦：{dayansf[2]}")
        if len(dayansf) > 3 and isinstance(dayansf[3], dict):
            for yao_idx, yao_text in dayansf[3].items():
                lines.append(f"  {yao_text}")

    bengua = d.get("本卦", {})
    if bengua:
        lines.append(f"\n【本卦】{bengua.get('卦', '')}")
        lines.append(f"  五星：{bengua.get('五星', '')}")
        lines.append(f"  世应：{bengua.get('世應卦', '')}")

    zhigua = d.get("之卦", {})
    if zhigua:
        lines.append(f"\n【之卦】{zhigua.get('卦', '')}")
        lines.append(f"  五星：{zhigua.get('五星', '')}")
        lines.append(f"  世应：{zhigua.get('世應卦', '')}")

    return "\n".join(lines)


def _build_lookup_text(gua_name: str, desc: dict) -> str:
    lines = [f"----------{gua_name}卦----------"]
    if isinstance(desc, dict):
        for idx in sorted(desc.keys()):
            lines.append(desc[idx])
    return "\n".join(lines)
