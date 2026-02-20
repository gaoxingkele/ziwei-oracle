# 紫微排盘：基于 py-iztro，输出文本与排盘图
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    from py_iztro import Astro
except ImportError:
    Astro = None  # type: ignore

# 时辰序号 0~12：早子、丑、寅、卯、辰、巳、午、未、申、酉、戌、亥、晚子
SHICHEN_NAMES = "早子 丑 寅 卯 辰 巳 午 未 申 酉 戌 亥 晚子".split()


def _ensure_astro():
    if Astro is None:
        raise RuntimeError("请先安装 py-iztro: pip install py-iztro")
    return Astro()


def get_astrolabe_data(
    date: str,
    time_index: int,
    gender: str,
    calendar: str = "solar",
) -> dict[str, Any]:
    """排盘，返回与文档兼容的字典（camelCase 键）。"""
    astro = _ensure_astro()
    gender_cn = "男" if str(gender).strip().lower() in ("male", "m", "男") else "女"
    time_idx = max(0, min(12, int(time_index)))
    if calendar == "lunar":
        raw = astro.by_lunar(date, time_idx, gender_cn)  # type: ignore
    else:
        raw = astro.by_solar(date, time_idx, gender_cn)  # type: ignore
    return raw.model_dump(by_alias=True, mode="json")


def build_text_description(main_json_data: dict[str, Any]) -> str:
    """将命盘 JSON 转为长文本，供 LLM 解读。"""
    lines = []
    lines.append("----------基本信息----------")
    lines.append(f"命主性别：{main_json_data.get('gender', '未知')}")
    lines.append(f"阳历生日：{main_json_data.get('solarDate', '未知')}")
    lines.append(f"阴历生日：{main_json_data.get('lunarDate', '未知')}")
    lines.append(f"八字：{main_json_data.get('chineseDate', '未知')}")
    lines.append(
        f"生辰时辰：{main_json_data.get('time', '未知')} ({main_json_data.get('timeRange', '未知')})"
    )
    lines.append(f"星座：{main_json_data.get('sign', '未知')}")
    lines.append(f"生肖：{main_json_data.get('zodiac', '未知')}")
    lines.append(f"身宫地支：{main_json_data.get('earthlyBranchOfBodyPalace', '未知')}")
    lines.append(f"命宫地支：{main_json_data.get('earthlyBranchOfSoulPalace', '未知')}")
    lines.append(f"命主星：{main_json_data.get('soul', '未知')}")
    lines.append(f"身主星：{main_json_data.get('body', '未知')}")
    lines.append(f"五行局：{main_json_data.get('fiveElementsClass', '未知')}")
    lines.append("----------宫位信息----------")
    for palace in main_json_data.get("palaces") or []:
        lines.append(_palace_to_text(palace))
        lines.append("----------")
    return "\n".join(lines)


def _palace_to_text(p: dict[str, Any]) -> str:
    lines = []
    lines.append(f"宫位{p.get('index')}号位，宫位名称是{p.get('name', '未知')}。")
    lines.append(
        f"{'是' if p.get('isBodyPalace') else '不是'}身宫，"
        f"{'是' if p.get('isOriginalPalace') else '不是'}来因宫。"
    )
    lines.append(
        f"宫位天干为{p.get('heavenlyStem', '未知')}，"
        f"宫位地支为{p.get('earthlyBranch', '未知')}。"
    )
    major = p.get("majorStars") or []
    major_desc = "主星:" + "，".join(
        f"{s.get('name', '')}（{s.get('brightness', '')}）" for s in major
    ) if major else "主星:无"
    lines.append(major_desc)
    minor = p.get("minorStars") or []
    lines.append("辅星：" + "，".join(s.get("name", "") for s in minor) if minor else "辅星：无")
    adj = p.get("adjectiveStars") or []
    lines.append("杂耀:" + "，".join(s.get("name", "") for s in adj) if adj else "杂耀:无")
    lines.append(f"长生12神:{p.get('changsheng12', '未知')}。")
    lines.append(f"博士12神:{p.get('boshi12', '未知')}。")
    dec = p.get("decadal")
    if isinstance(dec, dict) and isinstance(dec.get("range"), list):
        r = dec.get("range", [0, 0])
        lines.append(
            f"大限:{r[0]},{r[1]} "
            f"(运限天干{dec.get('heavenlyStem', '')}，地支{dec.get('earthlyBranch', '')})。"
        )
    return "\n".join(lines)


def render_chart_image(
    main_json_data: dict[str, Any],
    save_path: str | Path,
    cell_w: int = 140,
    cell_h: int = 100,
) -> str:
    """将命盘画成 4x3 宫位图，保存为 PNG，返回保存路径。"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        raise RuntimeError("请先安装 Pillow: pip install Pillow")
    out = Path(save_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    w, h = cell_w * 3, cell_h * 4
    img = Image.new("RGB", (w, h), color=(255, 252, 240))
    draw = ImageDraw.Draw(img)
    font_path = None
    for name in (
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "msyh.ttc",
        "simhei.ttf",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    ):
        if name and os.path.isfile(name):
            font_path = name
            break
    try:
        font_l = ImageFont.truetype(font_path, 14) if font_path else ImageFont.load_default()
        font_s = ImageFont.truetype(font_path, 11) if font_path else ImageFont.load_default()
    except OSError:
        font_l = font_s = ImageFont.load_default()
    palaces = main_json_data.get("palaces") or []
    for i, p in enumerate(palaces[:12]):
        row, col = i // 3, i % 3
        x0, y0 = col * cell_w, row * cell_h
        name = p.get("name", "?")
        major_stars = p.get("majorStars") or []
        star_names = " ".join(s.get("name", "") for s in major_stars[:4])
        draw.rectangle([x0, y0, x0 + cell_w - 1, y0 + cell_h - 1], outline=(80, 60, 40), width=1)
        draw.text((x0 + 4, y0 + 2), name, fill=(0, 0, 0), font=font_l)
        draw.text((x0 + 4, y0 + 22), star_names or "-", fill=(60, 40, 20), font=font_s)
    img.save(str(out))
    return str(out)
