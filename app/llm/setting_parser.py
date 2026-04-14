"""Parse fuzzy voice-transcribed text into normalized setting values.

Strategy:
1. Fast-path regex for already-clean input (saves LLM call, tokens, latency).
2. Fallback to Kimi LLM with a tight JSON-only prompt.
3. Each parser returns the normalized value or raises ParseError.
"""
from __future__ import annotations

import json
import re
from typing import Any

from kimi_client import chat


class ParseError(ValueError):
    pass


def _extract_json(text: str) -> dict:
    """Pull a JSON object out of the LLM reply (handles ```json fences)."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.DOTALL).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise


def _llm_parse(system_prompt: str, user_text: str) -> dict:
    reply = chat(user_content=user_text, system_content=system_prompt)
    return _extract_json(reply)


# ───────────────────────── birthday → YYYY-MM-DD ─────────────────────────

_RE_DATE_CLEAN = re.compile(r"^\s*(\d{4})[-/.年](\d{1,2})[-/.月](\d{1,2})日?\s*$")

_SYS_BIRTHDAY = (
    "你是一个日期规范化助手。用户会给你一段可能含语音识别误差的中文或数字描述。"
    "请提取其中表达的公历日期，输出严格 JSON：{\"value\": \"YYYY-MM-DD\"}，"
    "无任何其他解释。若年份只给了两位（如70年），按 1900+YY 或 2000+YY 选择更合理者；"
    "若无法判断，输出 {\"value\": null, \"error\": \"原因\"}。"
)


def parse_birthday(text: str) -> str:
    m = _RE_DATE_CLEAN.match(text)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mo <= 12 and 1 <= d <= 31:
            return f"{y:04d}-{mo:02d}-{d:02d}"
    data = _llm_parse(_SYS_BIRTHDAY, text)
    v = data.get("value")
    if not v or not re.match(r"^\d{4}-\d{2}-\d{2}$", str(v)):
        raise ParseError(f"无法解析生日: {text}")
    return str(v)


# ───────────────────────── birthtime → HH:MM ─────────────────────────

_RE_TIME_CLEAN = re.compile(r"^\s*(\d{1,2})[:：](\d{1,2})\s*$")

_SYS_BIRTHTIME = (
    "你是一个时间规范化助手。用户描述的是出生时间（24 小时制）。"
    "支持中文（早上七点四十、下午三点、晚上十一点）、时辰（子时=23:00，丑时=01:00，寅时=03:00，"
    "卯时=05:00，辰时=07:00，巳时=09:00，午时=11:00，未时=13:00，申时=15:00，酉时=17:00，戌时=19:00，亥时=21:00，"
    "每个时辰跨度 2 小时，默认取该时辰起始整点）和数字。"
    "输出严格 JSON：{\"value\": \"HH:MM\"}。若下午/晚上等词，转 24 小时。"
    "若无法判断，输出 {\"value\": null, \"error\": \"原因\"}。"
)


def parse_birthtime(text: str) -> str:
    m = _RE_TIME_CLEAN.match(text)
    if m:
        h, mi = int(m.group(1)), int(m.group(2))
        if 0 <= h <= 23 and 0 <= mi <= 59:
            return f"{h:02d}:{mi:02d}"
    data = _llm_parse(_SYS_BIRTHTIME, text)
    v = data.get("value")
    if not v or not re.match(r"^\d{2}:\d{2}$", str(v)):
        raise ParseError(f"无法解析时间: {text}")
    return str(v)


# ───────────────────────── city → 省份+市（中文）─────────────────────────

_SYS_CITY = (
    "你是一个中国行政区划规范化助手。用户会给出出生地点，可能是简称、英文、语音误识、"
    "只有市名或省名。请输出规范的中文『省份+市』或『直辖市』表达（如『福建省永安市』『北京市』『新疆维吾尔自治区乌鲁木齐市』）。"
    "若用户给的是外国城市，用『国家+城市』表达（如『日本东京都』『美国纽约市』）。"
    "输出严格 JSON：{\"value\": \"...\"}。若无法判断，输出 {\"value\": null, \"error\": \"原因\"}。"
)


def parse_city(text: str) -> str:
    data = _llm_parse(_SYS_CITY, text)
    v = data.get("value")
    if not v or not isinstance(v, str) or not v.strip():
        raise ParseError(f"无法解析出生地: {text}")
    return v.strip()


# ───────────────────────── name → 中文/英文姓名 ─────────────────────────

_SYS_NAME = (
    "你是一个姓名解析助手。用户会用各种方式描述自己的姓名，可能包括：\n"
    "- 直接报名字：『张三』『李平凡』\n"
    "- 拆字描述：『姓双木林、名字叫平凡的凡』→ 林凡；『耳东陈，安全的安』→ 陈安；『弓长张，三横王的王』→ 张王\n"
    "- 同音字确认：『我姓王，三横王』『草字头的苏』\n"
    "- 英文名：『My name is John Smith』→ John Smith\n"
    "默认输出中文姓名（纯汉字，无标点空格）。若用户明确用英文，输出英文（保留空格）。"
    "输出严格 JSON：{\"value\": \"...\", \"lang\": \"zh\" 或 \"en\"}。"
    "若无法判断，输出 {\"value\": null, \"error\": \"原因\"}。"
)


def parse_name(text: str, prefer_lang: str = "zh") -> tuple[str, str]:
    """Return (name, lang)."""
    sys_prompt = _SYS_NAME
    if prefer_lang == "en":
        sys_prompt += "\n用户偏好英文输出。"
    data = _llm_parse(sys_prompt, text)
    v = data.get("value")
    if not v or not isinstance(v, str) or not v.strip():
        raise ParseError(f"无法解析姓名: {text}")
    lang = data.get("lang") or prefer_lang
    return v.strip(), str(lang)


# ───────────────────────── sex → 1(男) / 0(女) ─────────────────────────

_MALE_WORDS = {"男", "男生", "男性", "male", "m", "boy", "1"}
_FEMALE_WORDS = {"女", "女生", "女性", "female", "f", "girl", "0"}

_SYS_SEX = (
    "判断用户描述的性别，男=1，女=0。输出严格 JSON：{\"value\": 1} 或 {\"value\": 0}。"
    "若无法判断，输出 {\"value\": null, \"error\": \"原因\"}。"
)


def parse_sex(text: str) -> int:
    t = text.strip().lower()
    if t in _MALE_WORDS:
        return 1
    if t in _FEMALE_WORDS:
        return 0
    data = _llm_parse(_SYS_SEX, text)
    v = data.get("value")
    if v not in (0, 1):
        raise ParseError(f"无法解析性别: {text}")
    return int(v)
