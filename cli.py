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
    """1. 紫微排盘：输入生日时辰，输出排盘文本 + 排盘图 PNG。"""
    from ziwei import get_astrolabe_data, build_text_description, render_chart_image

    print("【紫微排盘】")
    date_str = input("阳历生日 (YYYY-MM-DD，如 2000-08-16): ").strip() or "2000-08-16"
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        date_str = "2000-08-16"
    shichen = input("时辰序号 0~12 (0早子 1丑 2寅 3卯 4辰 5巳 6午 7未 8申 9酉 10戌 11亥 12晚子) [6]: ").strip() or "6"
    time_index = int(shichen) if shichen.isdigit() else 6
    gender = input("性别 (男/女) [女]: ").strip() or "女"
    data = get_astrolabe_data(date_str, time_index, gender, "solar")
    text = build_text_description(data)
    path_md = _save_md("# 紫微排盘\n\n" + text, "ziwei_chart")
    print(f"已保存排盘文本: {path_md}")
    try:
        path_img = os.path.join(OUTPUT_DIR, f"ziwei_chart_{_timestamp()}.png")
        render_chart_image(data, path_img)
        print(f"已保存排盘图: {path_img}")
    except Exception as e:
        print(f"排盘图生成跳过: {e}")
    _echo_md(text)


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
    """3. 紫微长线解读：排盘 + 问题，调用 Kimi 解读，输出 MD。"""
    from ziwei import get_astrolabe_data, build_text_description
    from kimi_client import chat
    from prompts import SYSTEM_ORACLE, format_ziwei_reading

    print("【紫微长线解读】")
    date_str = input("阳历生日 (YYYY-MM-DD) [2000-08-16]: ").strip() or "2000-08-16"
    shichen = input("时辰序号 0~12 [6]: ").strip() or "6"
    time_index = int(shichen) if shichen.isdigit() else 6
    gender = input("性别 (男/女) [女]: ").strip() or "女"
    question = input("您想问的问题 (如：未来半年事业与感情): ").strip() or "未来半年整体运势与行动建议"
    data = get_astrolabe_data(date_str, time_index, gender, "solar")
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
    """5. 姻缘分析：排盘 + 三类分析（婚姻道路、困难挑战、伴侣性格），调用 Kimi，输出 MD。"""
    from ziwei import get_astrolabe_data, build_text_description
    from kimi_client import chat
    from prompts import (
        SYSTEM_ORACLE,
        PROMPT_MARRIAGE_PATH,
        PROMPT_CHALLENGES,
        PROMPT_PARTNER_CHARACTER,
    )

    print("【姻缘分析】将依次进行：婚姻道路、困难挑战、伴侣性格 三项解读，请稍候。")
    date_str = input("阳历生日 (YYYY-MM-DD) [2000-08-16]: ").strip() or "2000-08-16"
    shichen = input("时辰序号 0~12 [6]: ").strip() or "6"
    time_index = int(shichen) if shichen.isdigit() else 6
    gender = input("性别 (男/女) [女]: ").strip() or "女"
    data = get_astrolabe_data(date_str, time_index, gender, "solar")
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
    lines = ["# 姻缘分析", "", f"生日 {date_str}，时辰 {shichen}，性别 {gender}", ""]
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
    birth = input("出生信息 (留空跳过，格式如 2000-08-16 午时 女): ").strip()
    system = SYSTEM_ORACLE
    if birth:
        system = system + "\n\n用户提供的出生信息（可用于紫微思路）：" + birth
    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    session_lines = ["# 智能体多轮咨询", "", f"出生信息: {birth or '无'}", ""]
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
    menu = """
DS-Oracle 命令行版（Kimi 最新 API，默认多轮对话）
输出目录: {out}
1. 紫微排盘（文本 + PNG 图）
2. 梅花易数起卦
3. 紫微长线解读（Kimi）
4. 梅花易数解读（Kimi）
5. 姻缘分析（婚姻道路/困难挑战/伴侣性格，Kimi）
6. 智能体多轮咨询（Kimi，保持上下文）
0. 退出
""".format(out=OUTPUT_DIR)
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
