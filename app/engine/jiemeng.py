from __future__ import annotations
import json
import uuid
from pathlib import Path
from typing import Any
from app.engine.registry import ChartRequest, ChartResult, register

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "jiemeng"

_CACHE: list[dict] | None = None


def _load() -> list[dict]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    fp = DATA_DIR / "dreams.json"
    if not fp.exists():
        raise FileNotFoundError(f"解梦数据不存在: {fp}")
    with open(fp, "r", encoding="utf-8") as f:
        _CACHE = json.load(f)
    return _CACHE


@register("jiemeng")
def calculate_jiemeng(req: ChartRequest) -> ChartResult:
    query = req.question.strip()
    if not query:
        query = req.extra.get("keyword", "")
    dreams = _load()
    matches = _search(dreams, query)
    data = {"query": query, "matches": matches, "total_db": len(dreams)}
    text = _build_text(query, matches)
    return ChartResult(
        chart_id=f"ch_{uuid.uuid4().hex[:12]}",
        system="jiemeng", raw_data=data, text_summary=text,
    )


def _search(dreams: list[dict], query: str, limit: int = 5) -> list[dict]:
    if not query:
        return []
    results = []
    for d in dreams:
        kw = d.get("keyword", "")
        if query in kw or kw in query:
            results.append(d)
            if len(results) >= limit:
                break
    if not results:
        for d in dreams:
            interp = d.get("interpretation", "")
            if query in interp:
                results.append(d)
                if len(results) >= limit:
                    break
    return results


def _build_text(query: str, matches: list[dict[str, Any]]) -> str:
    lines = [
        "----------周公解梦----------",
        f"查询：{query}",
        f"匹配结果：{len(matches)} 条",
    ]
    for i, m in enumerate(matches, 1):
        lines.append(f"\n【{i}】{m.get('keyword', '未知')}")
        cat = m.get("category", "")
        if cat:
            lines.append(f"  分类：{cat}")
        lines.append(f"  解梦：{m.get('interpretation', '暂无')}")
    if not matches:
        lines.append("未找到相关解梦条目")
    return "\n".join(lines)
