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


def _parse_shichen(s: str) -> int:
    """解析时辰：数字 0~12 或 时辰名（早子/丑/寅/卯/辰/巳/午/未/申/酉/戌/亥/晚子）。"""
    s = (s or "").strip()
    if s.isdigit():
        return max(0, min(12, int(s)))
    for i, n in enumerate(_SHICHEN_ORDER):
        if n == s:
            return i
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
    prompt = "请输入：姓名 生日 时辰 性别（空格分隔，例：张三 1978-4-14 6 男）"
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
    print(f"  已解析：姓名 {name}，生日 {date_str}，时辰 {_SHICHEN_ORDER[time_index]}，性别 {gender}")
    return date_str, time_index, gender, name


def _save_md(content: str, prefix: str) -> str:
    path = os.path.join(OUTPUT_DIR, f"{prefix}_{_timestamp()}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def _echo_md(content: str) -> None:
    """在终端回显 Markdown 文本。"""
    print("\n" + "=" * 60 + "\n")
    print(content)
    print("\n" + "=" * 60 + "\n")


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
    path_md, path_png = output_chart_text_and_image(data, str(Path(OUTPUT_DIR).resolve()), file_base, timestamp=None)
    print(f"紫微盘面文本已保存: {path_md}")
    if path_png:
        print(f"紫微排盘盘面图片 PNG 已保存: {path_png}")
    chart = build_text_description(data)
    results = {}
    for name, prompt_tpl in [
        ("婚姻道路", PROMPT_MARRIAGE_PATH),
        ("困难挑战", PROMPT_CHALLENGES),
        ("伴侣性格", PROMPT_PARTNER_CHARACTER),
    ]:
        print(f"  正在分析：{name}…")
        try:
            results[name] = chat(prompt_tpl.format(chart=chart), system_content=SYSTEM_ORACLE)
        except Exception as e:
            results[name] = f"调用失败: {e}"
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
    from kimi_client import chat_with_messages
    from prompts import SYSTEM_ORACLE

    print("【智能体多轮咨询】结合紫微/梅花思路，可连续提问。输入 /menu 或 0 或 exit 返回主菜单。")
    date_str, time_index, gender, name = _parse_ziwei_inputs(skip_if_empty=True)
    system = SYSTEM_ORACLE
    birth_desc = "无"
    if date_str is not None and name is not None:
        shichen_name = _SHICHEN_ORDER[time_index] if time_index is not None and 0 <= time_index < len(_SHICHEN_ORDER) else str(time_index or "")
        birth_desc = f"姓名 {name}，生日 {date_str}，时辰 {shichen_name}，性别 {gender or '女'}"
        system = system + "\n\n用户提供的出生信息（可用于紫微思路）：" + birth_desc
    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    session_lines = ["# 智能体多轮咨询", "", f"姓名 生日 时辰 性别: {birth_desc}", ""]
    while True:
        user_input = input("\n您: ").strip()
        if not user_input:
            continue
        if user_input in ("/menu", "0", "exit", "quit", "q"):
            print("返回主菜单。")
            break
        messages.append({"role": "user", "content": user_input})
        session_lines.append("## 您\n" + user_input + "\n")
        try:
            reply, messages = chat_with_messages(messages)
        except Exception as e:
            reply = f"调用失败: {e}"
            messages.pop()  # 去掉刚加的 user，方便重试
        session_lines.append("## Kimi\n" + reply + "\n")
        _echo_md(reply)
        path_md = _save_md("\n".join(session_lines), "oracle_chat")
        print(f"(对话已追加保存: {path_md})")


def main():
    out_abs = str(Path(OUTPUT_DIR).resolve())
    menu = """
DS-Oracle 命令行版（Kimi 最新 API，默认多轮对话）
排盘文本与图片保存到: {out}
1. 紫微排盘（文本 + PNG 图）
2. 梅花易数起卦
3. 紫微长线解读（Kimi）
4. 梅花易数解读（Kimi）
5. 姻缘分析（婚姻道路/困难挑战/伴侣性格，Kimi）
6. 智能体多轮咨询（Kimi，保持上下文）
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
            choice = input("请选择 [0-6]: ").strip() or "0"
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
            else:
                print("无效选项。")


if __name__ == "__main__":
    main()
