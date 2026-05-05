# -*- coding: utf-8 -*-
"""生命密码流年时运测试。"""
import pytest
from app.engine.lifenumber_period import (
    calculate_lifenumber_period,
    _personal_year, _personal_month, _personal_day, _reduce,
)


# ── 基础算法 ──
def test_reduce():
    assert _reduce(21) == 3
    assert _reduce(11) == 2     # 流年场景不保留大师数
    assert _reduce(99) == 9


def test_personal_year_1990_05_15_in_2026():
    # 5+15+2026 = 5+1+5+2+0+2+6 = 21 → 3
    assert _personal_year(5, 15, 2026) == 3


def test_personal_year_full_cycle():
    # 同一人不同年, 应是 9 年循环
    pys = [_personal_year(5, 15, y) for y in range(2020, 2029)]
    # 周期循环, 第 10 年应等于第 1 年
    assert _personal_year(5, 15, 2020) == _personal_year(5, 15, 2029)


def test_personal_month():
    # 个人年 3 + 5 月 = 8
    assert _personal_month(3, 5) == 8
    # 个人年 9 + 4 月 = 13 → 4
    assert _personal_month(9, 4) == 4


def test_personal_day():
    assert _personal_day(8, 6) == 5   # 8+6=14 → 5
    assert _personal_day(3, 9) == 3   # 3+9=12 → 3


# ── 端到端 ──
def test_full_pipeline_year():
    r = calculate_lifenumber_period(
        profile={"birthday": "1990-05-15"},
        expr="今年", base_date="2026-05-06", granularity="auto",
    )
    assert "error" not in r
    assert r["personal_year"] == 3
    assert r["personal_month"] is None  # 年粒度不算月
    assert r["interpretations"]["year"]["title"]
    assert "summary" in r and "3 年" in r["summary"]


def test_full_pipeline_today():
    r = calculate_lifenumber_period(
        profile={"birthday": "1990-05-15"},
        expr="今天", base_date="2026-05-06", granularity="auto",
    )
    assert "error" not in r
    assert r["personal_year"] == 3
    assert r["personal_month"] == 8
    assert r["personal_day"] == 5
    assert r["period"]["granularity"] == "day"


def test_full_pipeline_next_month():
    r = calculate_lifenumber_period(
        profile={"birthday": "1990-05-15"},
        expr="下个月", base_date="2026-05-06", granularity="auto",
    )
    assert "error" not in r
    assert r["personal_year"] == 3
    assert r["personal_month"] is not None
    assert r["personal_day"] is None  # 月粒度不算日


def test_missing_birthday():
    r = calculate_lifenumber_period(
        profile={}, expr="今年", base_date="2026-05-06",
    )
    assert r.get("error") == "profile_incomplete"


def test_recommendations_present():
    r = calculate_lifenumber_period(
        profile={"birthday": "1990-05-15"},
        expr="今年", base_date="2026-05-06",
    )
    assert "recommendations" in r
    assert len(r["recommendations"]["do"]) >= 3
    assert len(r["recommendations"]["avoid"]) >= 3
