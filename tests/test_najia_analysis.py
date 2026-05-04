# -*- coding: utf-8 -*-
"""断卦分析层 (app.najia.analysis) 关键规则单测。"""
from __future__ import annotations

import pytest
from app.najia import Najia
from app.najia.analysis import (
    analyze, _calc_guashen, _wangshuai, _four_gods, _zhi_pair_relation,
)
from app.najia.yongshen import take_yongshen


# ── 基础工具函数 ─────────────────────────────────────────────────
def test_wangshuai_table():
    # 木在春 (寅卯月) 旺、夏 (巳午月) 休、四季 (辰戌丑未) 囚、秋 (申酉月) 死、冬 (亥子月) 相
    assert _wangshuai("木", "寅") == "旺"
    assert _wangshuai("木", "巳") == "休"
    assert _wangshuai("木", "辰") == "囚"
    assert _wangshuai("木", "申") == "死"
    assert _wangshuai("木", "亥") == "相"


def test_zhi_pair_relations():
    assert _zhi_pair_relation("子", "午") == "冲"
    assert _zhi_pair_relation("子", "丑") == "合"
    assert _zhi_pair_relation("丑", "丑") == "临"
    assert _zhi_pair_relation("子", "寅") == "无"


def test_four_gods_for_fire():
    fg = _four_gods("火")
    assert fg["yuan"] == "木"   # 木生火
    assert fg["ji"] == "水"     # 水克火
    assert fg["chou"] == "金"   # 金克木 (克元神者)


# ── 用神取法规则 ─────────────────────────────────────────────────
def test_yongshen_keyword_match():
    assert take_yongshen("今年事业能否升职") == "官鬼"
    assert take_yongshen("最近求财顺不顺") == "妻财"
    assert take_yongshen("买房合同能签吗") == "父母"
    assert take_yongshen("求子有望吗") == "子孙"
    assert take_yongshen("和合伙人闹矛盾") == "兄弟"
    assert take_yongshen("感情怎么样", gender="女") == "官鬼"
    assert take_yongshen("感情怎么样", gender="男") == "妻财"
    assert take_yongshen("生病了能不能好") is None  # 自身→世爻
    assert take_yongshen("") is None
    assert take_yongshen("随便算一下") is None


# ── 卦身 ─────────────────────────────────────────────────────────
def test_guashen_yang_shi():
    # 阳世 (世爻为阳, params 在世位为 1 或 3) 从子起
    # 世初阳=子, 世二阳=丑, 世三阳=寅, ..., 世六阳=巳
    assert _calc_guashen(1, [1, 2, 2, 2, 2, 2]) == "子"
    assert _calc_guashen(6, [2, 2, 2, 2, 2, 1]) == "巳"


def test_guashen_yin_shi():
    # 阴世 (世爻为阴, params 在世位为 2 或 4) 从午起
    assert _calc_guashen(1, [2, 2, 2, 2, 2, 2]) == "午"
    assert _calc_guashen(6, [2, 2, 2, 2, 2, 2]) == "亥"


# ── 端到端: 真实卦盘 ────────────────────────────────────────────
@pytest.mark.asyncio
async def test_analyze_full_pipeline():
    obj = Najia(verbose=2).compile(
        params=[2, 2, 1, 2, 4, 2], date="2026-05-03 12:00",
        gender="男", title="升职", guaci=False,
    )
    result = analyze(obj.data, question="今年事业能否升职", gender="男")
    assert "yao_states" in result and len(result["yao_states"]) == 6
    assert result["yongshen"]["qin6"] == "官鬼"
    assert result["four_gods"]["yuan"] == "木"
    assert result["four_gods"]["ji"] == "水"
    assert result["guashen"] in "子丑寅卯辰巳午未申酉戌亥"
    assert result["summary"]
    # summary 必须含用神字眼
    assert "用神" in result["summary"]
    assert "卦身" in result["summary"]


@pytest.mark.asyncio
async def test_analyze_default_world_yao():
    """无关键词命中时，用神应取世爻所在六亲。"""
    obj = Najia(verbose=2).compile(
        params=[2, 2, 1, 2, 4, 2], date="2026-05-03 12:00",
        gender="男", title="随便算一下", guaci=False,
    )
    result = analyze(obj.data, question="随便算一下", gender="男")
    assert result["yongshen"]["source"] == "世爻(默认)"


@pytest.mark.asyncio
async def test_yongshen_falls_to_fushen_when_qin6_absent():
    """山雷颐 (六亲不全, 缺官鬼/子孙) 求考试 → 用神官鬼应取伏神。

    回归: 早期 _select_yongshen 在 positions 空时直接 return wuxing=None,
    导致四神/verdict/tts 全部塌掉。修复后应从 hide 字段取出辛酉金作伏神。
    """
    obj = Najia(verbose=2).compile(
        params=[3, 2, 2, 2, 2, 1], date="2026-05-04 12:00",
        gender="男", title="考试", guaci=False,
    )
    result = analyze(obj.data, question="考试会不会好", gender="男")
    yong = result["yongshen"]
    assert yong["qin6"] == "官鬼"
    assert yong["positions"] == []           # 本卦无官鬼
    assert yong["wuxing"] == "金"            # 伏神是辛酉金
    assert yong["fu_zhi"] == "酉"
    assert yong["fu_position"] == 3
    assert "伏神" in yong["source"]
    # 四神基于伏神五行计算: 金的元神=土、忌神=火、仇神=木
    assert result["four_gods"] == {"yuan": "土", "ji": "火", "chou": "木"}
    # summary/tts 必须含伏神信息
    assert "伏神" in result["summary"] and "酉金" in result["summary"]
    assert "伏神" in result["tts_text"] and "酉金" in result["tts_text"]


@pytest.mark.asyncio
async def test_dong_yao_changes_detection():
    """动爻应有 changes 字段填充。"""
    obj = Najia(verbose=2).compile(
        params=[2, 2, 1, 2, 4, 2], date="2026-05-03 12:00",
        gender="男", title="t", guaci=False,
    )
    result = analyze(obj.data, question="求财", gender="男")
    dong_states = [s for s in result["yao_states"] if s["is_dong"]]
    assert len(dong_states) >= 1
    for s in dong_states:
        assert "changes" in s
        assert "bian_zhi" in s
