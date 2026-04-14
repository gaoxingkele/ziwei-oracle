from __future__ import annotations
import json
import random
import uuid
from pathlib import Path
from typing import Any
from app.engine.registry import ChartRequest, ChartResult, register

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "qianwen"

_CACHE: dict[str, list[dict]] = {}

SUPPORTED_TYPES = ["guanyin", "huangdaxian", "zhuge", "mazu"]


def _load(qtype: str) -> list[dict]:
    if qtype in _CACHE:
        return _CACHE[qtype]
    fp = DATA_DIR / f"{qtype}.json"
    if not fp.exists():
        raise FileNotFoundError(f"签文数据不存在: {fp}")
    with open(fp, "r", encoding="utf-8") as f:
        data = json.load(f)
    _CACHE[qtype] = data
    return data


@register("qianwen")
def calculate_qianwen(req: ChartRequest) -> ChartResult:
    qtype = req.extra.get("type", "guanyin")
    signs = _load(qtype)
    pick = random.choice(signs)
    data = {"type": qtype, "sign": pick, "total": len(signs)}
    text = _build_text(qtype, pick)
    return ChartResult(
        chart_id=f"ch_{uuid.uuid4().hex[:12]}",
        system="qianwen", raw_data=data, text_summary=text,
    )


TYPE_NAMES = {
    "guanyin": "观音灵签",
    "huangdaxian": "黄大仙灵签",
    "zhuge": "诸葛神算",
    "mazu": "妈祖六十甲子签",
}


def _build_text(qtype: str, sign: dict[str, Any]) -> str:
    title = TYPE_NAMES.get(qtype, qtype)
    head = f"第 {sign.get('number', '?')} 签"
    gz = sign.get("ganzhi", "")
    if gz:
        head += f"  {gz}"
    lines = [f"----------{title}----------", head]
    level = sign.get("level", "")
    if level:
        lines.append(f"吉凶：{level}")
    poem = sign.get("poem", "")
    if poem:
        lines.append(f"签诗：{poem}")
    interp = sign.get("interpretation", "")
    if interp:
        lines.append(f"解签：{interp}")
    story = sign.get("story", "")
    if story:
        lines.append(f"典故：{story}")
    return "\n".join(lines)
