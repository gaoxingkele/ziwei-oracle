from __future__ import annotations
import sys
import uuid
from typing import Any
from app.engine.registry import ChartRequest, ChartResult, register

# kinqimen 使用 `import config` 绝对导入，需要将其映射到 kinqimen.config
import kinqimen.config
if "config" not in sys.modules or sys.modules["config"] is not kinqimen.config:
    sys.modules.setdefault("config", kinqimen.config)

from kinqimen.kinqimen import Qimen


@register("qimen")
def calculate_qimen(req: ChartRequest) -> ChartResult:
    parts = req.birth_date.split("-")
    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
    hour, minute = _parse_hour_minute(req.birth_time)
    option = int(req.extra.get("method", 1))  # 1=拆补, 2=茅山, 3=置闰

    q = Qimen(year, month, day, hour, minute)
    data = q.pan(option)
    text = _build_text(data)
    return ChartResult(
        chart_id=f"ch_{uuid.uuid4().hex[:12]}",
        system="qimen", raw_data=data, text_summary=text,
    )


def _parse_hour_minute(time_str: str) -> tuple[int, int]:
    if ":" in time_str:
        h, m = time_str.split(":")
        return int(h), int(m)
    try:
        idx = int(time_str)
        return idx * 2 + 1, 0  # 时辰索引转近似小时
    except ValueError:
        return 10, 0


def _build_text(d: dict[str, Any]) -> str:
    lines = [
        "----------奇门遁甲----------",
        f"排盘方式：{d.get('排盤方式', '未知')}",
        f"干支：{d.get('干支', '未知')}",
        f"旬首：{d.get('旬首', '未知')}",
        f"旬空：{d.get('旬空', '')}",
        f"局日：{d.get('局日', '未知')}",
        f"排局：{d.get('排局', '未知')}",
        f"节气：{d.get('節氣', '未知')}",
        f"值符值使：{d.get('值符值使', '')}",
        f"天乙：{d.get('天乙', '')}",
    ]
    for section in ["天盤", "地盤", "門", "星", "神", "馬星"]:
        val = d.get(section, "")
        if val:
            lines.append(f"{section}：{val}")
    changsheng = d.get("長生運", "")
    if changsheng:
        lines.append(f"长生运：{changsheng}")
    return "\n".join(lines)
