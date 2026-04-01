from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
import sys


def _import_najia():
    """
    优先从已安装包导入；失败时回退到本地仓库路径:
    D:/BaiduSyncdisk/aicoding/najia
    """
    try:
        from najia import Najia  # type: ignore
        return Najia
    except Exception:
        pass

    local_repo = Path(r"D:\BaiduSyncdisk\aicoding\najia")
    if local_repo.exists():
        parent = str(local_repo.parent)
        if parent not in sys.path:
            sys.path.insert(0, parent)
    try:
        from najia import Najia  # type: ignore
        return Najia
    except Exception:
        from najia.najia import Najia  # type: ignore
        return Najia


def normalize_liuyao_params(raw: str) -> list[int]:
    """
    解析六爻输入，格式示例: "2 2 1 2 4 2"
    规则:
      - 仅取前 6 个
      - 非法值按 2(少阴) 处理
      - 不足 6 个时补 2
      - 每位限制在 1~4
    """
    items = (raw or "").strip().split()
    vals: list[int] = []
    for token in items[:6]:
        try:
            v = int(token)
        except ValueError:
            v = 2
        vals.append(max(1, min(4, v)))
    while len(vals) < 6:
        vals.append(2)
    return vals


def calculate_liuyao(
    *,
    params: list[int],
    date_str: str | None = None,
    gender: str | None = None,
    title: str | None = None,
    guaci: bool = False,
    verbose: int = 2,
) -> dict[str, Any]:
    Najia = _import_najia()
    if len(params) != 6:
        raise ValueError("六爻参数必须为 6 位（每位 1~4）")
    params = [max(1, min(4, int(x))) for x in params]
    use_date = date_str or datetime.now().strftime("%Y-%m-%d %H:%M")
    obj = Najia(verbose=verbose).compile(
        params=params,
        date=use_date,
        gender=gender or "",
        title=title or "",
        guaci=guaci,
    )
    rendered = obj.render()
    data = obj.data or {}
    return {
        "rendered_text": rendered,
        "params": params,
        "date": use_date,
        "data": data,
    }


def build_liuyao_context(result: dict[str, Any]) -> str:
    data = result.get("data", {}) or {}
    lunar = data.get("lunar", {}) or {}
    gz = lunar.get("gz", {}) or {}
    shiy = data.get("shiy", ())
    shi = shiy[0] if isinstance(shiy, (list, tuple)) and len(shiy) > 0 else ""
    ying = shiy[1] if isinstance(shiy, (list, tuple)) and len(shiy) > 1 else ""
    lines = [
        "【六爻排盘上下文（najia）】",
        f"- 占题: {data.get('title', '')}",
        f"- 起卦时间: {result.get('date', '')}",
        f"- 本卦: {data.get('name', '')}",
        f"- 卦宫: {data.get('gong', '')}",
        f"- 世应: 世爻{shi} / 应爻{ying}",
        f"- 动爻位: {data.get('dong', [])}",
        f"- 六神: {data.get('god6', [])}",
        f"- 六亲: {data.get('qin6', [])}",
        f"- 日干支: {gz.get('day', '')}，旬空: {lunar.get('xkong', '')}",
    ]
    bian = data.get("bian")
    if isinstance(bian, dict) and bian:
        lines.append(f"- 变卦: {bian.get('name', '')}（卦宫 {bian.get('gong', '')}）")
    hide = data.get("hide")
    if isinstance(hide, dict) and hide:
        lines.append(f"- 伏神卦: {hide.get('name', '')}")
    return "\n".join(lines)
