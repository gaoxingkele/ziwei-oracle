from __future__ import annotations
import json
import sys
import uuid
from pathlib import Path
from typing import Any
from app.engine.registry import ChartRequest, ChartResult, register

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "namedict"

# --- Stroke count dictionary (康熙字典笔画) ---
_STROKE_DICT: dict[str, int] | None = None

def _load_stroke_dict() -> dict[str, int]:
    global _STROKE_DICT
    if _STROKE_DICT is not None:
        return _STROKE_DICT
    sys.path.insert(0, str(DATA_DIR))
    try:
        import full_wuxing_dict as fwd
        d: dict[str, int] = {}
        for wd in [fwd.jin_dict, fwd.mu_dict, fwd.huo_dict, fwd.shui_dict, fwd.tu_dict]:
            for num, chars in wd.items():
                for c in chars:
                    d[c] = num
        _STROKE_DICT = d
    finally:
        sys.path.pop(0)
    return _STROKE_DICT

# --- Wuxing from stroke count ---
WUXING_MAP = {1: "木", 2: "木", 3: "火", 4: "火", 5: "土", 6: "土", 7: "金", 8: "金", 9: "水", 0: "水"}

def _stroke_to_wuxing(n: int) -> str:
    return WUXING_MAP[n % 10]

# --- Sancai (三才) lookup ---
_SANCAI_DICT: dict[str, dict] | None = None

def _load_sancai() -> dict[str, dict]:
    global _SANCAI_DICT
    if _SANCAI_DICT is not None:
        return _SANCAI_DICT
    _SANCAI_DICT = {}
    fp = DATA_DIR / "sancai.txt"
    with open(fp, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    i = 0
    while i < len(lines):
        header = lines[i]
        if len(header) >= 3 and all(c in "金木水火土" for c in header[:3]):
            key = header[:3]
            desc_lines = []
            level = ""
            i += 1
            while i < len(lines) and not (len(lines[i]) >= 3 and all(c in "金木水火土" for c in lines[i][:3])):
                line = lines[i]
                if line.startswith("【") and line.endswith("】"):
                    level = line[1:-1]
                else:
                    desc_lines.append(line)
                i += 1
            _SANCAI_DICT[key] = {
                "level": level,
                "description": "".join(desc_lines),
            }
        else:
            i += 1
    return _SANCAI_DICT

# --- 81 数理吉凶 ---
SHULI_81 = {
    1: ("大吉", "太极之数，万物开泰，生发无穷，利禄亨通"),
    2: ("大凶", "两仪之数，混沌未开，进退保守，志望难达"),
    3: ("大吉", "三才之数，天地人和，大事大业，繁荣昌隆"),
    4: ("大凶", "四象之数，待于生发，万事慎重，不具营谋"),
    5: ("大吉", "五行之数，循环相生，圆通畅达，福祉无穷"),
    6: ("大吉", "六爻之数，发展变化，天赋美德，吉祥安泰"),
    7: ("吉", "七政之数，精悍严谨，天赋之力，吉星照耀"),
    8: ("吉", "八卦之数，乾坎艮震，巽离坤兑，无穷无尽"),
    9: ("凶", "大成之数，蕴涵凶险，或成或败，难以把握"),
    10: ("凶", "终结之数，雪暗飘零，偶或有成，回顾茫然"),
    11: ("大吉", "旱苗逢雨，枯木逢春，挽回家运，平稳强健"),
    12: ("凶", "掘井无泉，意志薄弱，家庭寂寞，企图不力"),
    13: ("大吉", "春日牡丹，才艺多能，智谋奇略，忍柔当事"),
    14: ("凶", "破兆之数，家庭缘薄，孤独遭难，谋事不达"),
    15: ("大吉", "福寿之数，福寿圆满，富贵荣誉，涵养雅量"),
    16: ("大吉", "厚重之数，厚重载德，安富尊荣，财官双美"),
    17: ("半吉", "刚强之数，突破万难，如能容忍，必获成功"),
    18: ("大吉", "铁镜重磨，权威显达，博得名利，且养柔德"),
    19: ("凶", "多难之数，风云蔽日，辛苦重来，虽有智谋"),
    20: ("凶", "屋下藏金，非业破运，灾难叠至，进退维谷"),
    21: ("大吉", "明月中天，独立权威，能为首领，兴家立业"),
    22: ("凶", "秋草逢霜，困难疾弱，虽出豪杰，人生波折"),
    23: ("大吉", "壮丽之数，旭日东升，壮丽壮观，权威旺盛"),
    24: ("大吉", "掘藏得金，家门余庆，金钱丰盈，白手成家"),
    25: ("大吉", "资性英敏，才能奇特，克服傲慢，尚可成功"),
    26: ("半吉", "变怪之谜，英雄豪杰，波澜重叠，而奏大功"),
    27: ("凶", "欲望无止，自我强烈，多受毁谤，尚可成功"),
    28: ("凶", "遭难之数，豪杰气概，四海漂泊，终世浮躁"),
    29: ("大吉", "智谋之数，智谋优秀，财力归集，名闻海内"),
    30: ("半吉", "非运之数，绝处逢生，沉浮不定，统帅众人"),
    31: ("大吉", "春日花开，智勇得志，博得名利，统领众人"),
    32: ("大吉", "宝马金鞍，侥幸多望，贵人得助，财帛如裕"),
    33: ("大吉", "旭日升天，鸾凤相会，名闻天下，隆昌至极"),
    35: ("大吉", "高楼望月，优雅发展，此数最合女性，或可成大业"),
    37: ("大吉", "猛虎出林，权威显达，热诚忠信，宜着雅量"),
    38: ("半吉", "磨铁成针，薄弱无力，孤独刚毅，可望成功"),
    39: ("大吉", "富贵荣华，财帛丰盈，暗藏险象，德泽四方"),
    41: ("大吉", "天赋吉运，德望兼备，继续努力，前途无限"),
    45: ("大吉", "顺风扬帆，新生泰和，智谋经纬，富贵繁荣"),
    47: ("大吉", "点石成金，开花之象，祯祥吉庆，全力进取"),
    48: ("大吉", "青松立鹤，智谋兼备，德量荣达，威望成师"),
    52: ("大吉", "达眼之数，先见之明，理想实现，利达名望"),
    57: ("半吉", "日照春松，寒雪青松，夺天之巧，可望成功"),
    61: ("大吉", "名利双收，繁荣富贵，只谈温饱，则似锦绣"),
    63: ("大吉", "富贵尊荣，子孙繁荣，再经天纬，万事大成"),
    65: ("大吉", "富贵长寿，长短平衡，能获众望，成就大业"),
    67: ("大吉", "利路亨通，达人天命，家运隆昌，大吉大利"),
    68: ("大吉", "顺风吹帆，智虑周密，兴盛发达，名满天下"),
    81: ("大吉", "万物回春，还原复始，繁荣富贵，涵养柔德"),
}

def _get_shuli(n: int) -> tuple[str, str]:
    n = ((n - 1) % 81) + 1
    return SHULI_81.get(n, ("平", "普通数理"))


def _get_stroke(char: str) -> int:
    d = _load_stroke_dict()
    return d.get(char, 0)


def _calc_wuge(surname: str, given_name: str) -> dict[str, Any]:
    s_strokes = [_get_stroke(c) for c in surname]
    g_strokes = [_get_stroke(c) for c in given_name]

    s_total = sum(s_strokes)
    g_total = sum(g_strokes)

    tiange = s_total + 1 if len(surname) == 1 else s_strokes[0] + s_strokes[1]
    renge = s_strokes[-1] + g_strokes[0]
    dige = g_total + 1 if len(given_name) == 1 else sum(g_strokes)
    zongge = s_total + g_total
    waige = zongge - renge + 1

    if waige <= 0:
        waige = 1

    sancai_key = _stroke_to_wuxing(tiange) + _stroke_to_wuxing(renge) + _stroke_to_wuxing(dige)
    sancai_data = _load_sancai().get(sancai_key, {"level": "未知", "description": ""})

    return {
        "surname": surname,
        "given_name": given_name,
        "full_name": surname + given_name,
        "strokes": {"surname": s_strokes, "given_name": g_strokes},
        "wuge": {
            "天格": {"value": tiange, "wuxing": _stroke_to_wuxing(tiange), **dict(zip(["jixiong", "meaning"], _get_shuli(tiange)))},
            "人格": {"value": renge, "wuxing": _stroke_to_wuxing(renge), **dict(zip(["jixiong", "meaning"], _get_shuli(renge)))},
            "地格": {"value": dige, "wuxing": _stroke_to_wuxing(dige), **dict(zip(["jixiong", "meaning"], _get_shuli(dige)))},
            "外格": {"value": waige, "wuxing": _stroke_to_wuxing(waige), **dict(zip(["jixiong", "meaning"], _get_shuli(waige)))},
            "总格": {"value": zongge, "wuxing": _stroke_to_wuxing(zongge), **dict(zip(["jixiong", "meaning"], _get_shuli(zongge)))},
        },
        "sancai": {
            "config": sancai_key,
            "level": sancai_data["level"],
            "description": sancai_data["description"],
        },
    }


@register("name_analysis")
def calculate_name_analysis(req: ChartRequest) -> ChartResult:
    full_name = req.name.strip()
    surname_len = int(req.extra.get("surname_len", 1))
    surname = full_name[:surname_len]
    given_name = full_name[surname_len:]
    if not given_name:
        from app.common.exceptions import BusinessError
        raise BusinessError("请输入完整姓名（至少两个字）")

    data = _calc_wuge(surname, given_name)
    text = _build_text(data)
    return ChartResult(
        chart_id=f"ch_{uuid.uuid4().hex[:12]}",
        system="name_analysis", raw_data=data, text_summary=text,
    )


def _build_text(d: dict[str, Any]) -> str:
    lines = [
        "----------姓名五格分析----------",
        f"姓名：{d['full_name']}",
        f"姓氏笔画：{d['strokes']['surname']}",
        f"名字笔画：{d['strokes']['given_name']}",
        "",
        "【五格】",
    ]
    for ge_name, ge in d["wuge"].items():
        lines.append(f"  {ge_name}：{ge['value']} ({ge['wuxing']}) — {ge['jixiong']} {ge['meaning']}")

    sc = d["sancai"]
    lines.extend([
        "",
        "【三才配置】",
        f"  {sc['config']} — {sc['level']}",
        f"  {sc['description'][:200]}",
    ])
    return "\n".join(lines)
