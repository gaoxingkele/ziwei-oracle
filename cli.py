# 命令行主程序：菜单、输出到文件并回显终端
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

from config import OUTPUT_DIR

# 确保 output 目录存在
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _safe_filename(s: str, max_len: int = 120) -> str:
    """将字符串整理为可作文件名的形式：去掉非法字符，限制长度。"""
    s = (s or "").strip()
    for c in r'\/:*?"<>|':
        s = s.replace(c, "_")
    s = s.strip(".") or "unnamed"
    return s[:max_len] if len(s) > max_len else s


def _normalize_birth_date(raw: str) -> str:
    """将用户输入的生日规范为 YYYY-MM-DD（如 1978-4-14 -> 1978-04-14），无效返回空串。"""
    raw = (raw or "").strip()
    if not raw:
        return ""
    parts = raw.replace(" ", "").split("-")
    if len(parts) != 3:
        return ""
    try:
        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
        if 1900 <= y <= 2100 and 1 <= m <= 12 and 1 <= d <= 31:
            return f"{y:04d}-{m:02d}-{d:02d}"
    except (ValueError, TypeError):
        pass
    return ""


# 时辰名 -> 序号，与 ziwei.SHICHEN_NAMES 一致
_SHICHEN_ORDER = "早子 丑 寅 卯 辰 巳 午 未 申 酉 戌 亥 晚子".split()
_ALL_READING_MODES = {"ziwei", "astro", "bazi", "six", "meihua"}


def _format_modes(modes: set[str]) -> str:
    if not modes:
        return "base"
    return " ".join(sorted(modes))


def _apply_mode_command(user_input: str, current_modes: set[str]) -> tuple[set[str], str]:
    """
    /mode 指令：
    - /mode full
    - /mode base
    - /mode list
    - /mode ziwei astro
    - /mode +ziwei -astro
    """
    parts = user_input.strip().split()
    if len(parts) == 1 or (len(parts) == 2 and parts[1] == "list"):
        return current_modes, f"当前模式: {_format_modes(current_modes)}"
    args = parts[1:]
    if len(args) == 1 and args[0] == "full":
        return set(_ALL_READING_MODES), "已切换到 full（ziwei astro bazi six meihua）"
    if len(args) == 1 and args[0] in ("base", "none"):
        return set(), "已切换到 base（仅主回答）"

    next_modes = set(current_modes)
    explicit: set[str] = set()
    for token in args:
        if token.startswith("+") and token[1:] in _ALL_READING_MODES:
            next_modes.add(token[1:])
        elif token.startswith("-") and token[1:] in _ALL_READING_MODES:
            next_modes.discard(token[1:])
        elif token in _ALL_READING_MODES:
            explicit.add(token)
        else:
            return current_modes, (
                "无效模式参数。可用: full | base | list | "
                "ziwei astro bazi six meihua（支持 +mode/-mode）"
            )
    if explicit:
        next_modes = explicit
    return next_modes, f"模式已更新: {_format_modes(next_modes)}"


def _hour_to_shichen(hour: int) -> int:
    """将 0~23 小时转换为时辰序号 0~12。"""
    if hour == 0:
        return 0   # 早子
    if hour == 23:
        return 12  # 晚子
    # 1→1(丑), 3→2(寅), 5→3(卯), 7→4(辰), 9→5(巳), 11→6(午)
    # 13→7(未), 15→8(申), 17→9(酉), 19→10(戌), 21→11(亥)
    return (hour + 1) // 2


def _parse_shichen(s: str) -> int:
    """解析时辰，支持多种格式：
    - 时辰序号: 0~12
    - 时辰名: 早子/丑/寅/.../亥/晚子
    - 24小时制: 14:00, 14:30, 14
    - 中文时间: 上午9点, 下午3点, 凌晨2点, 晚上8点
    """
    import re
    s = (s or "").strip()
    if not s:
        return 6

    # 时辰名匹配
    for i, n in enumerate(_SHICHEN_ORDER):
        if n == s:
            return i

    # 24小时制: "14:00", "14:30", "9:00"
    m = re.match(r'^(\d{1,2}):(\d{2})$', s)
    if m:
        return _hour_to_shichen(int(m.group(1)) % 24)

    # 中文时间: "上午9点", "下午3点", "凌晨2点", "晚上8点", "早上6点"
    m = re.match(r'^(上午|早上|凌晨|下午|晚上|傍晚)(\d{1,2})点?$', s)
    if m:
        period, h = m.group(1), int(m.group(2))
        if period in ("下午", "晚上", "傍晚") and 1 <= h <= 11:
            h += 12
        elif period == "凌晨" and h == 12:
            h = 0
        return _hour_to_shichen(h % 24)

    # 纯数字: 先尝试当作时辰序号(0~12)，再当作小时(13~23)
    if s.isdigit():
        n = int(s)
        if 0 <= n <= 12:
            return n
        if 13 <= n <= 23:
            return _hour_to_shichen(n)

    return 6


def _parse_gender(s: str) -> str:
    """解析性别：男/女。"""
    s = (s or "").strip()
    if s == "男" or (len(s) <= 3 and s.lower() in ("male", "m", "nan")):
        return "男"
    return "女"


def _parse_ziwei_inputs(skip_if_empty: bool = False):
    """
    在一行内读取：姓名 生日 时辰 性别（空格分隔）。
    例：张三 1978-4-14 6 男  或  李四 2000-08-16 午 女
    返回 (date_str, time_index, gender, name)。若 skip_if_empty 且用户留空，返回 (None, None, None, None)。
    """
    prompt = "请输入：姓名 生日 时间 性别（空格分隔，例：张三 1978-4-14 14:00 男 或 张三 1978-4-14 下午2点 男）"
    if skip_if_empty:
        prompt += "，留空跳过"
    prompt += "："
    line = input(prompt).strip()
    if skip_if_empty and not line:
        return None, None, None, None
    parts = line.split(maxsplit=3)
    name = (parts[0] or "未填").strip()
    raw_date = (parts[1] or "").strip() if len(parts) > 1 else ""
    shichen_raw = (parts[2] or "6").strip() if len(parts) > 2 else "6"
    gender_raw = (parts[3] or "女").strip() if len(parts) > 3 else "女"
    date_str = _normalize_birth_date(raw_date) if raw_date else ""
    if not date_str:
        date_str = "2000-08-16"
        print("  使用默认日期:", date_str)
    time_index = _parse_shichen(shichen_raw)
    gender = _parse_gender(gender_raw)
    shichen_name = _SHICHEN_ORDER[time_index]
    hour_range = [
        "23:00-01:00", "01:00-03:00", "03:00-05:00", "05:00-07:00",
        "07:00-09:00", "09:00-11:00", "11:00-13:00", "13:00-15:00",
        "15:00-17:00", "17:00-19:00", "19:00-21:00", "21:00-23:00", "23:00-01:00",
    ]
    print(f"  已解析：姓名 {name}，生日 {date_str}，{shichen_name}时 ({hour_range[time_index]})，性别 {gender}")
    return date_str, time_index, gender, name


def _save_md(content: str, prefix: str) -> str:
    path = os.path.join(OUTPUT_DIR, f"{prefix}_{_timestamp()}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def _generate_western_astrology_files(
    *,
    name: str,
    date_str: str,
    time_index: int,
    gender: str,
    shichen_name: str,
) -> tuple[str, str, str]:
    """调用 kerykeion 生成西方星盘文本+SVG，返回 (md_path, svg_path, context_text)。"""
    from astrology import generate_kerykeion_chart_and_text

    file_base = _safe_filename(f"{name}_{date_str}_{shichen_name}_{gender}")
    md_path, svg_path, context_text = generate_kerykeion_chart_and_text(
        name=name,
        date_str=date_str,
        time_index=time_index,
        gender=gender,
        output_dir=str(Path(OUTPUT_DIR).resolve()),
        file_base=file_base,
    )
    print("已自动生成西方星相学星盘：")
    print(f"  文本: {md_path}")
    print(f"  SVG : {svg_path}")
    return md_path, svg_path, context_text


def _build_six_context_from_params(
    *,
    raw_params: str,
    birth_desc: str,
    title: str = "多轮咨询六爻参考",
) -> tuple[str, str]:
    """
    依据用户输入的六爻码生成六爻上下文和落盘文本文件。
    返回 (six_context, md_path)。
    """
    from liuyao import build_liuyao_context, calculate_liuyao, normalize_liuyao_params

    params = normalize_liuyao_params(raw_params)
    result = calculate_liuyao(
        params=params,
        date_str=datetime.now().strftime("%Y-%m-%d %H:%M"),
        gender="",
        title=title,
        guaci=False,
        verbose=2,
    )
    six_context = build_liuyao_context(result)
    body = "\n".join(
        [
            "# 六爻排盘（najia）",
            "",
            f"- 出生信息: {birth_desc}",
            f"- 六爻码: {' '.join(str(x) for x in params)}",
            "",
            "## 六爻上下文",
            six_context,
            "",
            "## 原始排盘",
            result.get("rendered_text", ""),
        ]
    )
    path_md = _save_md(body, "liuyao_chart")
    return six_context, path_md


def _echo_md(content: str) -> None:
    """在终端回显 Markdown 文本。"""
    print("\n" + "=" * 60 + "\n")
    print(content)
    print("\n" + "=" * 60 + "\n")


def _ask_llm_reading(engine_name: str, text_summary: str, question: str = "") -> None:
    """通用：展示引擎计算结果后，询问用户是否调用大模型解读。"""
    choice = input("\n是否调用大模型进行深度解读？(y/n，默认 y): ").strip().lower()
    if choice == "n":
        return
    if not question:
        question = input("您想问的问题（留空则使用默认解读）: ").strip() or f"请对以上{engine_name}结果进行全面解读"
    from kimi_client import chat
    from prompts import SYSTEM_ORACLE, format_engine_reading
    prompt = format_engine_reading(engine_name, question, text_summary)
    print(f"正在调用大模型解读{engine_name}...")
    try:
        answer = chat(prompt, system_content=SYSTEM_ORACLE)
    except Exception as e:
        answer = f"调用失败: {e}"
    out = f"# {engine_name}解读\n\n## 问题\n{question}\n\n## 计算结果摘要\n{text_summary[:500]}\n\n## 解读\n{answer}"
    path_md = _save_md(out, f"{engine_name}_reading")
    print(f"已保存: {path_md}")
    _echo_md("## 解读\n\n" + answer)


def run_bazi():
    """八字排盘 + 可选大模型解读。"""
    import importlib
    importlib.import_module("app.engine.bazi")
    from app.engine.registry import ChartRequest, calculate
    import asyncio

    print("【八字排盘】")
    date_str, time_index, gender, name = _parse_ziwei_inputs()
    req = ChartRequest(
        system="bazi", name=name, birth_date=date_str,
        birth_time=str(time_index), gender=gender,
    )
    try:
        result = asyncio.run(calculate(req))
    except Exception as e:
        print(f"八字排盘失败: {e}")
        return
    text = result.text_summary
    path_md = _save_md("# 八字排盘\n\n" + text, "bazi")
    print(f"已保存: {path_md}")
    _echo_md(text)
    _ask_llm_reading("八字", text)


def run_almanac():
    """黄历查询 + 可选大模型解读。"""
    import importlib
    importlib.import_module("app.engine.almanac")
    from app.engine.registry import ChartRequest, calculate
    import asyncio

    print("【黄历查询】")
    date_str = input("查询日期 (YYYY-MM-DD，留空为今天): ").strip()
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    date_str = _normalize_birth_date(date_str) or datetime.now().strftime("%Y-%m-%d")
    req = ChartRequest(
        system="almanac", name="查询", birth_date=date_str,
        birth_time="0", gender="男",
    )
    try:
        result = asyncio.run(calculate(req))
    except Exception as e:
        print(f"黄历查询失败: {e}")
        return
    text = result.text_summary
    path_md = _save_md("# 黄历查询\n\n" + text, "almanac")
    print(f"已保存: {path_md}")
    _echo_md(text)
    _ask_llm_reading("黄历", text)


def run_qimen():
    """奇门遁甲排盘 + 可选大模型解读。"""
    import importlib
    importlib.import_module("app.engine.qimen")
    from app.engine.registry import ChartRequest, calculate
    import asyncio

    print("【奇门遁甲】")
    date_str = input("日期 (YYYY-MM-DD，留空为今天): ").strip()
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    date_str = _normalize_birth_date(date_str) or datetime.now().strftime("%Y-%m-%d")
    time_raw = input("时辰 (0~12 或 早子/丑/.../亥/晚子，留空为当前): ").strip()
    if not time_raw:
        time_raw = str(datetime.now().hour // 2)
    time_index = _parse_shichen(time_raw)
    question = input("占问（可留空）: ").strip() or "当前时局如何"
    req = ChartRequest(
        system="qimen", name="占问", birth_date=date_str,
        birth_time=str(time_index), gender="男", question=question,
    )
    try:
        result = asyncio.run(calculate(req))
    except Exception as e:
        print(f"奇门遁甲排盘失败: {e}")
        return
    text = result.text_summary
    path_md = _save_md("# 奇门遁甲\n\n" + text, "qimen")
    print(f"已保存: {path_md}")
    _echo_md(text)
    _ask_llm_reading("奇门遁甲", text, question)


def run_liuren():
    """大六壬排盘 + 可选大模型解读。"""
    import importlib
    importlib.import_module("app.engine.liuren")
    from app.engine.registry import ChartRequest, calculate
    import asyncio

    print("【大六壬】")
    date_str = input("日期 (YYYY-MM-DD，留空为今天): ").strip()
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    date_str = _normalize_birth_date(date_str) or datetime.now().strftime("%Y-%m-%d")
    time_raw = input("时辰 (0~12 或 早子/丑/.../亥/晚子，留空为当前): ").strip()
    if not time_raw:
        time_raw = str(datetime.now().hour // 2)
    time_index = _parse_shichen(time_raw)
    guiren = input("贵人选择 (1=昼贵 2=夜贵，默认1): ").strip() or "1"
    question = input("占问（可留空）: ").strip() or "当前事态如何"
    req = ChartRequest(
        system="liuren", name="占问", birth_date=date_str,
        birth_time=str(time_index), gender="男",
        question=question, extra={"guiren": guiren},
    )
    try:
        result = asyncio.run(calculate(req))
    except Exception as e:
        print(f"大六壬排盘失败: {e}")
        return
    text = result.text_summary
    path_md = _save_md("# 大六壬\n\n" + text, "liuren")
    print(f"已保存: {path_md}")
    _echo_md(text)
    _ask_llm_reading("大六壬", text, question)


def run_iching():
    """周易筮法 + 可选大模型解读。"""
    import importlib
    importlib.import_module("app.engine.iching")
    from app.engine.registry import ChartRequest, calculate
    import asyncio

    print("【周易筮法】")
    date_str = input("日期 (YYYY-MM-DD，留空为今天): ").strip()
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    date_str = _normalize_birth_date(date_str) or datetime.now().strftime("%Y-%m-%d")
    time_raw = input("时辰 (0~12 或 早子/丑/.../亥/晚子，留空为当前): ").strip()
    if not time_raw:
        time_raw = str(datetime.now().hour // 2)
    time_index = _parse_shichen(time_raw)
    question = input("占问: ").strip() or "问前程"
    req = ChartRequest(
        system="iching", name="占问", birth_date=date_str,
        birth_time=str(time_index), gender="男", question=question,
    )
    try:
        result = asyncio.run(calculate(req))
    except Exception as e:
        print(f"周易筮法失败: {e}")
        return
    text = result.text_summary
    path_md = _save_md("# 周易筮法\n\n" + text, "iching")
    print(f"已保存: {path_md}")
    _echo_md(text)
    _ask_llm_reading("周易", text, question)


def run_qianwen():
    """求签（观音/黄大仙/诸葛）+ 可选大模型解读。"""
    import importlib
    importlib.import_module("app.engine.qianwen")
    from app.engine.registry import ChartRequest, calculate
    import asyncio

    print("【求签】")
    print("  1. 观音灵签 (98签)")
    print("  2. 黄大仙灵签 (100签)")
    print("  3. 诸葛神算 (384签)")
    type_choice = input("选择签种 (1/2/3，默认1): ").strip() or "1"
    type_map = {"1": "guanyin", "2": "huangdaxian", "3": "zhuge"}
    qtype = type_map.get(type_choice, "guanyin")
    question = input("心中所问（可留空）: ").strip() or "求一签"
    req = ChartRequest(
        system="qianwen", name="求签", birth_date=datetime.now().strftime("%Y-%m-%d"),
        birth_time="0", gender="男", question=question,
        extra={"type": qtype},
    )
    try:
        result = asyncio.run(calculate(req))
    except Exception as e:
        print(f"求签失败: {e}")
        return
    text = result.text_summary
    path_md = _save_md("# 求签\n\n" + text, "qianwen")
    print(f"已保存: {path_md}")
    _echo_md(text)
    _ask_llm_reading("灵签", text, question)


def run_jiemeng():
    """周公解梦 + 可选大模型解读。"""
    import importlib
    importlib.import_module("app.engine.jiemeng")
    from app.engine.registry import ChartRequest, calculate
    import asyncio

    print("【周公解梦】")
    keyword = input("梦境关键词 (如：蛇、飞、水): ").strip()
    if not keyword:
        print("请输入梦境关键词。")
        return
    req = ChartRequest(
        system="jiemeng", name="解梦", birth_date=datetime.now().strftime("%Y-%m-%d"),
        birth_time="0", gender="男", question=keyword,
    )
    try:
        result = asyncio.run(calculate(req))
    except Exception as e:
        print(f"解梦查询失败: {e}")
        return
    text = result.text_summary
    path_md = _save_md("# 周公解梦\n\n" + text, "jiemeng")
    print(f"已保存: {path_md}")
    _echo_md(text)
    _ask_llm_reading("解梦", text, f"梦见{keyword}是什么含义")


def run_name_analysis():
    """姓名五格分析 + 可选大模型解读。"""
    import importlib
    importlib.import_module("app.engine.name_analysis")
    from app.engine.registry import ChartRequest, calculate
    import asyncio

    print("【姓名五格分析】")
    name = input("请输入姓名 (如：张三丰): ").strip()
    if not name:
        print("请输入姓名。")
        return
    req = ChartRequest(
        system="name_analysis", name=name,
        birth_date="2000-01-01", birth_time="0", gender="男",
    )
    try:
        result = asyncio.run(calculate(req))
    except Exception as e:
        print(f"姓名分析失败: {e}")
        return
    text = result.text_summary
    path_md = _save_md("# 姓名五格分析\n\n" + text, "name_analysis")
    print(f"已保存: {path_md}")
    _echo_md(text)
    _ask_llm_reading("姓名五格", text)


def run_jiri():
    """黄道吉日查询 + 可选大模型解读。"""
    import importlib
    importlib.import_module("app.engine.jiri")
    from app.engine.registry import ChartRequest, calculate
    import asyncio

    print("【黄道吉日查询】")
    activity = input("查询事项 (如：结婚/搬家/开业/出行/动土): ").strip()
    if not activity:
        print("请输入查询事项。")
        return
    start = input("起始日期 (YYYY-MM-DD，留空为今天): ").strip()
    if not start:
        start = datetime.now().strftime("%Y-%m-%d")
    start = _normalize_birth_date(start) or datetime.now().strftime("%Y-%m-%d")
    end = input("截止日期 (YYYY-MM-DD，留空为起始日期后30天): ").strip()
    if end:
        end = _normalize_birth_date(end) or ""
    req = ChartRequest(
        system="jiri", name="吉日查询",
        birth_date=start, birth_time="0", gender="男",
        question=activity,
        extra={"start_date": start, "end_date": end} if end else {"start_date": start},
    )
    try:
        result = asyncio.run(calculate(req))
    except Exception as e:
        print(f"吉日查询失败: {e}")
        return
    text = result.text_summary
    path_md = _save_md("# 黄道吉日查询\n\n" + text, "jiri")
    print(f"已保存: {path_md}")
    _echo_md(text)
    _ask_llm_reading("黄道吉日", text, f"从以上吉日中推荐最适合{activity}的日子")


def run_hehun():
    """八字合婚 + 可选大模型解读。"""
    import importlib
    importlib.import_module("app.engine.hehun")
    from app.engine.registry import ChartRequest, calculate
    import asyncio

    print("【八字合婚】")
    print("请输入甲方信息：")
    date_a, time_a, gender_a, name_a = _parse_ziwei_inputs()
    print("请输入乙方信息：")
    date_b, time_b, gender_b, name_b = _parse_ziwei_inputs()
    req = ChartRequest(
        system="hehun", name=name_a, birth_date=date_a,
        birth_time=str(time_a), gender=gender_a,
        extra={
            "spouse_birth_date": date_b,
            "spouse_birth_time": str(time_b),
            "spouse_gender": gender_b,
        },
    )
    try:
        result = asyncio.run(calculate(req))
    except Exception as e:
        print(f"合婚分析失败: {e}")
        return
    text = result.text_summary
    path_md = _save_md("# 八字合婚\n\n" + text, "hehun")
    print(f"已保存: {path_md}")
    _echo_md(text)
    _ask_llm_reading("八字合婚", text)


def run_ziwei_chart():
    """1. 紫微排盘：输入姓名、生日、时辰、性别后，调用 py-iztro 输出文本与排盘图，文件名：姓名+生日+时辰+性别。"""
    from ziwei import get_astrolabe_data, output_chart_text_and_image, SHICHEN_NAMES

    print("【紫微排盘】")
    out_dir_abs = str(Path(OUTPUT_DIR).resolve())
    print(f"输出目录: {out_dir_abs}")
    date_str, time_index, gender, name = _parse_ziwei_inputs()
    try:
        data = get_astrolabe_data(date_str, time_index, gender, "solar")
    except Exception as e:
        print(f"排盘计算失败: {e}")
        return
    shichen_name = SHICHEN_NAMES[time_index] if 0 <= time_index < len(SHICHEN_NAMES) else str(time_index)
    file_base = _safe_filename(f"{name}_{date_str}_{shichen_name}_{gender}")
    try:
        _generate_western_astrology_files(
            name=name,
            date_str=date_str,
            time_index=time_index,
            gender=gender,
            shichen_name=shichen_name,
        )
    except Exception as e:
        print(f"西方星盘生成失败（不影响紫微流程）: {e}")
    try:
        path_md, path_png = output_chart_text_and_image(data, out_dir_abs, file_base, timestamp=None)
    except Exception as e:
        print(f"保存排盘文本/图片时出错: {e}")
        return
    print("")
    print("========== 排盘输出文件（请到下方目录查看）==========")
    print(f"  目录: {out_dir_abs}")
    print(f"  文本: {Path(path_md).name}")
    print(f"  图片: {Path(path_png).name}" if path_png else "  图片: 未生成")
    print("==================================================")
    if path_md and Path(path_md).exists():
        print(f"  文本完整路径: {path_md}")
    if path_png and Path(path_png).exists():
        print(f"  图片完整路径: {path_png}")
    print("")
    try:
        text = Path(path_md).read_text(encoding="utf-8").replace("# 紫微排盘（文本版本）\n\n", "")
        _echo_md(text)
    except Exception as e:
        print(f"读取已保存文本失败: {e}")
    if not path_png:
        print("（PNG 未生成：请安装 Pillow 且 Windows 需有中文字体，如 微软雅黑）")


def run_meihua_draw():
    """2. 梅花易数起卦：输入占题与时间，输出卦象文本。"""
    from meihua import calculate_meihua, TRIGRAMS, MOVING_LINE_NAMES

    print("【梅花易数起卦】")
    topic = input("占题 (如：本周面试能否通过): ").strip() or "近期运势"
    when = input("起卦时间 (留空为当前时间，或 YYYY-MM-DD HH:MM): ").strip()
    if when:
        try:
            occurred = datetime.strptime(when, "%Y-%m-%d %H:%M")
        except ValueError:
            occurred = datetime.now()
    else:
        occurred = datetime.now()
    gua = calculate_meihua(topic, occurred)
    gua["topic"] = topic
    lines = [
        "# 梅花易数起卦",
        "",
        f"- 占题：{topic}",
        f"- 起卦时间：{gua.get('occurred_at', '')}",
        f"- 本卦：{gua['base_gua']}",
        f"- 互卦：{gua['mutual_gua']}",
        f"- 变卦：{gua['changed_gua']}",
        f"- 动爻：{gua['moving_line_name']}",
        f"- 体卦：{gua['ti_gua']}，用卦：{gua['yong_gua']}，体用关系：{gua['relation']}",
    ]
    text = "\n".join(lines)
    path_md = _save_md(text, "meihua_gua")
    print(f"已保存: {path_md}")
    _echo_md(text)


def run_ziwei_reading():
    """3. 紫微长线解读：排盘后输出文本+PNG，再调用 Kimi 解读。"""
    from ziwei import get_astrolabe_data, build_text_description, output_chart_text_and_image, SHICHEN_NAMES
    from kimi_client import chat
    from prompts import SYSTEM_ORACLE, format_ziwei_reading

    print("【紫微长线解读】")
    date_str, time_index, gender, name = _parse_ziwei_inputs()
    question = input("您想问的问题 (如：未来半年事业与感情): ").strip() or "未来半年整体运势与行动建议"
    data = get_astrolabe_data(date_str, time_index, gender, "solar")
    shichen_name = SHICHEN_NAMES[time_index] if 0 <= time_index < len(SHICHEN_NAMES) else str(time_index)
    file_base = _safe_filename(f"{name}_{date_str}_{shichen_name}_{gender}")
    try:
        _generate_western_astrology_files(
            name=name,
            date_str=date_str,
            time_index=time_index,
            gender=gender,
            shichen_name=shichen_name,
        )
    except Exception as e:
        print(f"西方星盘生成失败（不影响紫微解读）: {e}")
    path_md, path_png = output_chart_text_and_image(data, str(Path(OUTPUT_DIR).resolve()), file_base, timestamp=None)
    print(f"紫微盘面文本已保存: {path_md}")
    if path_png:
        print(f"紫微排盘盘面图片 PNG 已保存: {path_png}")
    chart_text = build_text_description(data)
    chart_summary = "\n".join(chart_text.splitlines()[:40])
    prompt = format_ziwei_reading(question, chart_summary)
    print("正在调用 Kimi 解读…")
    try:
        answer = chat(prompt, system_content=SYSTEM_ORACLE)
    except Exception as e:
        answer = f"调用失败: {e}\n\n（请检查 KIMI_API_KEY 或 MOONSHOT_API_KEY）"
    out = f"# 紫微长线解读\n\n## 问题\n{question}\n\n## 命盘摘要（前40行）\n{chart_summary}\n\n## 解读\n{answer}"
    path_md = _save_md(out, "ziwei_reading")
    print(f"已保存: {path_md}")
    _echo_md("## 解读\n\n" + answer)


def run_meihua_reading():
    """4. 梅花易数解读：起卦 + 调用 Kimi 解读，输出 MD。"""
    from meihua import calculate_meihua
    from kimi_client import chat
    from prompts import SYSTEM_ORACLE, format_meihua_reading

    print("【梅花易数解读】")
    topic = input("占题: ").strip() or "近期运势"
    when = input("起卦时间 (留空为当前): ").strip()
    occurred = datetime.now()
    if when:
        try:
            occurred = datetime.strptime(when, "%Y-%m-%d %H:%M")
        except ValueError:
            pass
    gua = calculate_meihua(topic, occurred)
    gua["topic"] = topic
    prompt = format_meihua_reading(gua)
    print("正在调用 Kimi 解读…")
    try:
        answer = chat(prompt, system_content=SYSTEM_ORACLE)
    except Exception as e:
        answer = f"调用失败: {e}"
    out = f"# 梅花易数解读\n\n## 占题\n{topic}\n\n## 卦象\n本卦 {gua['base_gua']}，互卦 {gua['mutual_gua']}，变卦 {gua['changed_gua']}，动爻 {gua['moving_line_name']}，体用 {gua['relation']}\n\n## 解读\n{answer}"
    path_md = _save_md(out, "meihua_reading")
    print(f"已保存: {path_md}")
    _echo_md("## 解读\n\n" + answer)


def run_liuyao_draw():
    """六爻排盘：输入六爻码，生成排盘文本。"""
    from liuyao import calculate_liuyao, normalize_liuyao_params

    print("【六爻排盘（najia）】")
    raw = input("请输入六爻码（6个1~4，空格分隔，如：2 2 1 2 4 2）: ").strip()
    params = normalize_liuyao_params(raw)
    title = input("占题（可留空）: ").strip() or "六爻排盘"
    date_str = input("起卦时间（留空为当前，格式 YYYY-MM-DD HH:MM）: ").strip()
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        result = calculate_liuyao(
            params=params,
            date_str=date_str,
            gender="",
            title=title,
            guaci=False,
            verbose=2,
        )
    except Exception as e:
        print(f"六爻排盘失败: {e}")
        return
    text = result.get("rendered_text", "")
    path_md = _save_md("# 六爻排盘（najia）\n\n" + text, "liuyao_gua")
    print(f"已保存: {path_md}")
    _echo_md(text)


def run_liuyao_reading():
    """六爻解读：排盘后调用 Kimi 进行同题解读。"""
    from kimi_client import chat
    from liuyao import build_liuyao_context, calculate_liuyao, normalize_liuyao_params
    from prompts import SYSTEM_ORACLE, format_six_chat

    print("【六爻解读（Kimi）】")
    raw = input("请输入六爻码（6个1~4，空格分隔，如：2 2 1 2 4 2）: ").strip()
    params = normalize_liuyao_params(raw)
    title = input("占题（可留空）: ").strip() or "六爻问事"
    question = input("您想问的问题（留空则使用占题）: ").strip() or title
    date_str = input("起卦时间（留空为当前，格式 YYYY-MM-DD HH:MM）: ").strip()
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        result = calculate_liuyao(
            params=params,
            date_str=date_str,
            gender="",
            title=title,
            guaci=False,
            verbose=2,
        )
        six_context = build_liuyao_context(result)
    except Exception as e:
        print(f"六爻排盘失败: {e}")
        return
    prompt = format_six_chat(user_query=question, six_context=six_context, birth_context="")
    print("正在调用 Kimi 解读…")
    try:
        answer = chat(prompt, system_content=SYSTEM_ORACLE)
    except Exception as e:
        answer = f"调用失败: {e}"
    out = (
        "# 六爻解读\n\n"
        f"## 占题\n{title}\n\n"
        f"## 问题\n{question}\n\n"
        "## 六爻上下文\n"
        f"{six_context}\n\n"
        "## 原始排盘\n"
        f"{result.get('rendered_text', '')}\n\n"
        "## 解读\n"
        f"{answer}"
    )
    path_md = _save_md(out, "liuyao_reading")
    print(f"已保存: {path_md}")
    _echo_md("## 解读\n\n" + answer)


def run_marriage_analysis():
    """5. 姻缘分析：排盘后输出文本+PNG，再三类分析（婚姻道路、困难挑战、伴侣性格）。"""
    from ziwei import get_astrolabe_data, build_text_description, output_chart_text_and_image, SHICHEN_NAMES
    from kimi_client import chat
    from prompts import (
        SYSTEM_ORACLE,
        PROMPT_MARRIAGE_PATH,
        PROMPT_CHALLENGES,
        PROMPT_PARTNER_CHARACTER,
    )

    print("【姻缘分析】将依次：输出紫微盘面文本与 PNG 图，再进行婚姻道路、困难挑战、伴侣性格 三项解读。")
    date_str, time_index, gender, name = _parse_ziwei_inputs()
    data = get_astrolabe_data(date_str, time_index, gender, "solar")
    shichen_name = SHICHEN_NAMES[time_index] if 0 <= time_index < len(SHICHEN_NAMES) else str(time_index)
    file_base = _safe_filename(f"{name}_{date_str}_{shichen_name}_{gender}")
    try:
        _generate_western_astrology_files(
            name=name,
            date_str=date_str,
            time_index=time_index,
            gender=gender,
            shichen_name=shichen_name,
        )
    except Exception as e:
        print(f"西方星盘生成失败（不影响姻缘分析）: {e}")
    path_md, path_png = output_chart_text_and_image(data, str(Path(OUTPUT_DIR).resolve()), file_base, timestamp=None)
    print(f"紫微盘面文本已保存: {path_md}")
    if path_png:
        print(f"紫微排盘盘面图片 PNG 已保存: {path_png}")
    chart = build_text_description(data)
    results = {}
    for section_name, prompt_tpl in [
        ("婚姻道路", PROMPT_MARRIAGE_PATH),
        ("困难挑战", PROMPT_CHALLENGES),
        ("伴侣性格", PROMPT_PARTNER_CHARACTER),
    ]:
        print(f"  正在分析：{section_name}…")
        try:
            results[section_name] = chat(prompt_tpl.format(chart=chart), system_content=SYSTEM_ORACLE)
        except Exception as e:
            results[section_name] = f"调用失败: {e}"
    lines = ["# 姻缘分析", "", f"姓名 {name}，生日 {date_str}，时辰 {shichen_name}，性别 {gender}", ""]
    for name, text in results.items():
        lines.append(f"## {name}\n")
        lines.append(text)
        lines.append("")
    out = "\n".join(lines)
    path_md = _save_md(out, "marriage_analysis")
    print(f"已保存: {path_md}")
    _echo_md(out)


def run_oracle_chat():
    """6. 智能体咨询：多轮对话，保持上下文，直到用户输入 /menu 或 0 或 exit 返回主菜单。"""
    from kimi_client import chat, chat_with_messages
    from meihua import calculate_meihua
    from prompts import (
        SYSTEM_ASTRO,
        SYSTEM_ORACLE,
        format_astrology_chat,
        format_bazi_chat,
        format_meihua_chat,
        format_six_chat,
        format_ziwei_chat,
    )
    from ziwei import build_text_description, get_astrolabe_data

    print("【智能体多轮咨询】结合紫微/梅花思路，可连续提问。输入 /menu 或 0 或 exit 返回主菜单。")
    print("模式命令: /mode full | /mode base | /mode list | /mode ziwei astro bazi six meihua | /mode +astro -six")
    print("六爻命令: /six 2 2 1 2 4 2  （设置/更新六爻码）")
    date_str, time_index, gender, name = _parse_ziwei_inputs(skip_if_empty=True)
    system = SYSTEM_ORACLE
    birth_desc = "无"
    astrology_context = ""
    ziwei_context = ""
    bazi_context = ""
    six_context = ""
    active_modes = set(_ALL_READING_MODES)
    if date_str is not None and name is not None:
        shichen_name = _SHICHEN_ORDER[time_index] if time_index is not None and 0 <= time_index < len(_SHICHEN_ORDER) else str(time_index or "")
        birth_desc = f"姓名 {name}，生日 {date_str}，时辰 {shichen_name}，性别 {gender or '女'}"
        system = system + "\n\n用户提供的出生信息（可用于紫微思路）：" + birth_desc
        # 先准备紫微盘文本上下文，用于每轮同题研读
        try:
            z_data = get_astrolabe_data(date_str, time_index or 6, gender or "女", "solar")
            ziwei_text = build_text_description(z_data)
            ziwei_context = "【紫微盘面摘要（节选）】\n" + "\n".join(ziwei_text.splitlines()[:120])
            bazi_context = "\n".join(
                [
                    "【八字基础信息】",
                    f"- 阳历生日: {z_data.get('solarDate', date_str)}",
                    f"- 阴历生日: {z_data.get('lunarDate', '')}",
                    f"- 八字: {z_data.get('chineseDate', '')}",
                    f"- 五行局: {z_data.get('fiveElementsClass', '')}",
                    f"- 性别: {z_data.get('gender', gender or '女')}",
                ]
            )
            print("已加载紫微盘上下文（用于每轮同题解读）。")
        except Exception as e:
            print(f"紫微盘上下文加载失败（不影响继续咨询）: {e}")
        try:
            _md_path, _svg_path, astrology_context = _generate_western_astrology_files(
                name=name,
                date_str=date_str,
                time_index=time_index or 6,
                gender=gender or "女",
                shichen_name=shichen_name,
            )
        except Exception as e:
            print(f"西方星盘生成失败（不影响继续咨询）: {e}")
        six_seed = input("可选：请输入六爻码（6个1~4，空格分隔；留空跳过）: ").strip()
        if six_seed:
            try:
                six_context, six_md_path = _build_six_context_from_params(
                    raw_params=six_seed,
                    birth_desc=birth_desc,
                )
                print(f"已生成六爻排盘: {six_md_path}")
            except Exception as e:
                print(f"六爻排盘生成失败（可稍后用 /six 设置）: {e}")

    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    session_lines = ["# 智能体多轮咨询", "", f"姓名 生日 时辰 性别: {birth_desc}", "", f"模式: {_format_modes(active_modes)}", ""]
    if ziwei_context:
        session_lines.append("## 紫微盘面摘要\n")
        session_lines.append(ziwei_context + "\n")
    if bazi_context:
        session_lines.append("## 八字基础信息\n")
        session_lines.append(bazi_context + "\n")
    if six_context:
        session_lines.append("## 六爻上下文\n")
        session_lines.append(six_context + "\n")
    if astrology_context:
        session_lines.append("## 西方星相学关键位\n")
        session_lines.append(astrology_context + "\n")

    while True:
        user_input = input("\n您: ").strip()
        if not user_input:
            continue
        if user_input in ("/menu", "0", "exit", "quit", "q"):
            print("返回主菜单。")
            break
        if user_input.startswith("/mode"):
            active_modes, mode_msg = _apply_mode_command(user_input, active_modes)
            print(mode_msg)
            session_lines.append("## 模式切换\n" + mode_msg + "\n")
            continue
        if user_input.startswith("/six"):
            six_raw = user_input.replace("/six", "", 1).strip()
            if not six_raw:
                msg = "用法: /six 2 2 1 2 4 2"
                print(msg)
                session_lines.append("## 六爻设置\n" + msg + "\n")
                continue
            try:
                six_context, six_md_path = _build_six_context_from_params(
                    raw_params=six_raw,
                    birth_desc=birth_desc,
                )
                msg = f"六爻码已更新，排盘已保存: {six_md_path}"
                print(msg)
                session_lines.append("## 六爻设置\n" + msg + "\n")
            except Exception as e:
                msg = f"六爻码设置失败: {e}"
                print(msg)
                session_lines.append("## 六爻设置\n" + msg + "\n")
            continue
        messages.append({"role": "user", "content": user_input})
        session_lines.append("## 您\n" + user_input + "\n")
        try:
            reply, messages = chat_with_messages(messages)
        except Exception as e:
            reply = f"调用失败: {e}"
            messages.pop()  # 去掉刚加的 user，方便重试
        # 同一问题同步提交给紫微研读
        if "ziwei" in active_modes and ziwei_context:
            try:
                ziwei_prompt = format_ziwei_chat(
                    user_query=user_input,
                    ziwei_context=ziwei_context,
                    birth_context=birth_desc if birth_desc != "无" else "",
                )
                ziwei_reply = chat(ziwei_prompt, system_content=SYSTEM_ORACLE)
                reply = reply + "\n\n---\n## 紫微同题补充解读\n" + ziwei_reply
            except Exception as e:
                reply = reply + f"\n\n（紫微同题补充解读调用失败: {e}）"
        if "bazi" in active_modes and bazi_context:
            try:
                bazi_prompt = format_bazi_chat(
                    user_query=user_input,
                    bazi_context=bazi_context,
                    birth_context=birth_desc if birth_desc != "无" else "",
                )
                bazi_reply = chat(bazi_prompt, system_content=SYSTEM_ORACLE)
                reply = reply + "\n\n---\n## 八字同题补充解读\n" + bazi_reply
            except Exception as e:
                reply = reply + f"\n\n（八字同题补充解读调用失败: {e}）"
        if "six" in active_modes:
            try:
                if six_context:
                    six_prompt = format_six_chat(
                        user_query=user_input,
                        six_context=six_context,
                        birth_context=birth_desc if birth_desc != "无" else "",
                    )
                    six_reply = chat(six_prompt, system_content=SYSTEM_ORACLE)
                    reply = reply + "\n\n---\n## 六爻同题补充解读\n" + six_reply
                else:
                    reply = reply + "\n\n---\n## 六爻同题补充解读\n（未设置六爻码，请先输入 /six 2 2 1 2 4 2）"
            except Exception as e:
                reply = reply + f"\n\n（六爻同题补充解读调用失败: {e}）"
        if "meihua" in active_modes:
            try:
                meihua = calculate_meihua(user_input, datetime.now())
                meihua_context = "\n".join(
                    [
                        "【梅花易数当轮起卦】",
                        f"- 本卦: {meihua.get('base_gua', '')}",
                        f"- 互卦: {meihua.get('mutual_gua', '')}",
                        f"- 变卦: {meihua.get('changed_gua', '')}",
                        f"- 动爻: {meihua.get('moving_line_name', '')}",
                        f"- 体用: {meihua.get('relation', '')}",
                        f"- 起卦时刻: {meihua.get('occurred_at', '')}",
                    ]
                )
                meihua_prompt = format_meihua_chat(
                    user_query=user_input,
                    meihua_context=meihua_context,
                    birth_context=birth_desc if birth_desc != "无" else "",
                )
                meihua_reply = chat(meihua_prompt, system_content=SYSTEM_ORACLE)
                reply = reply + "\n\n---\n## 梅花同题补充解读\n" + meihua_reply
            except Exception as e:
                reply = reply + f"\n\n（梅花同题补充解读调用失败: {e}）"
        # 同一问题同步提交给星相学研读
        if "astro" in active_modes and astrology_context:
            try:
                astro_prompt = format_astrology_chat(
                    user_query=user_input,
                    astrology_context=astrology_context,
                    birth_context=birth_desc if birth_desc != "无" else "",
                )
                astro_reply = chat(astro_prompt, system_content=SYSTEM_ASTRO)
                reply = reply + "\n\n---\n## 星相学补充解读\n" + astro_reply
            except Exception as e:
                reply = reply + f"\n\n（星相学补充解读调用失败: {e}）"
        if messages and messages[-1]["role"] == "assistant":
            messages[-1]["content"] = reply
        session_lines.append("## Kimi\n" + reply + "\n")
        _echo_md(reply)
        path_md = _save_md("\n".join(session_lines), "oracle_chat")
        print(f"(对话已追加保存: {path_md})")


def main():
    out_abs = str(Path(OUTPUT_DIR).resolve())
    menu = """
DS-Oracle 命令行版（Kimi 最新 API，默认多轮对话）
排盘文本与图片保存到: {out}

── 排盘与解读 ──
 1. 紫微排盘（文本 + PNG 图）
 2. 梅花易数起卦
 3. 紫微长线解读（Kimi）
 4. 梅花易数解读（Kimi）
 5. 姻缘分析（婚姻道路/困难挑战/伴侣性格，Kimi）
 6. 智能体多轮咨询（Kimi，保持上下文）
 7. 六爻排盘（najia）
 8. 六爻解读（Kimi）

── 更多功能 ──
 9. 八字排盘
10. 黄历查询
11. 奇门遁甲
12. 大六壬
13. 周易筮法
14. 求签（观音/黄大仙/诸葛）
15. 周公解梦
16. 姓名五格分析
17. 八字合婚
18. 黄道吉日查询

 0. 退出
""".format(out=out_abs)
    while True:
        # 默认启动多轮对话：回车直接进入 6，输入 m 显示菜单
        choice = input("回车 = 进入智能体多轮咨询，m = 主菜单，0 = 退出: ").strip()
        if choice == "0":
            print("再见。")
            break
        if choice != "m" and choice != "M" and choice != "菜单":
            # 默认进入多轮咨询
            run_oracle_chat()
            continue
        # 显示主菜单
        while True:
            print(menu)
            choice = input("请选择 [0-18]: ").strip() or "0"
            if choice == "0":
                print("再见。")
                return
            if choice == "1":
                run_ziwei_chart()
            elif choice == "2":
                run_meihua_draw()
            elif choice == "3":
                run_ziwei_reading()
            elif choice == "4":
                run_meihua_reading()
            elif choice == "5":
                run_marriage_analysis()
            elif choice == "6":
                run_oracle_chat()
            elif choice == "7":
                run_liuyao_draw()
            elif choice == "8":
                run_liuyao_reading()
            elif choice == "9":
                run_bazi()
            elif choice == "10":
                run_almanac()
            elif choice == "11":
                run_qimen()
            elif choice == "12":
                run_liuren()
            elif choice == "13":
                run_iching()
            elif choice == "14":
                run_qianwen()
            elif choice == "15":
                run_jiemeng()
            elif choice == "16":
                run_name_analysis()
            elif choice == "17":
                run_hehun()
            elif choice == "18":
                run_jiri()
            else:
                print("无效选项。")


if __name__ == "__main__":
    main()
