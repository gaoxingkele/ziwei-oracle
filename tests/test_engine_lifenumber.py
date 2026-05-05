# -*- coding: utf-8 -*-
"""生命密码引擎测试。"""
import pytest
from app.engine.registry import ChartRequest, calculate
import app.engine.lifenumber  # noqa: F401
from app.engine.lifenumber import _reduce_to_digit, _calc


def test_reduce_basic():
    assert _reduce_to_digit(30) == 3
    assert _reduce_to_digit(7) == 7
    assert _reduce_to_digit(99) == 9   # 99 → 18 → 9


def test_reduce_keeps_master():
    assert _reduce_to_digit(11) == 11
    assert _reduce_to_digit(22) == 22
    assert _reduce_to_digit(33) == 33


def test_reduce_force_single():
    assert _reduce_to_digit(11, keep_master=False) == 2
    assert _reduce_to_digit(22, keep_master=False) == 4


def test_calc_three_numbers():
    """1990-05-15: 1+9+9+0+5+1+5 = 30 → 3; 出生日 15→6"""
    d = _calc("1990-05-15")
    assert d["talent_number"] == 30
    assert d["life_number"] == 3
    assert d["birthday_number"] == 6


def test_calc_master_birthday():
    """出生 22 日 → 大师数 22 不还原"""
    d = _calc("1995-08-22")
    assert d["birthday_number"] == 22
    assert d["talent_number"] == 36
    assert d["life_number"] == 9


def test_calc_master_birthday_11():
    """出生 29 日 → 2+9 = 11, 大师数"""
    d = _calc("1988-11-29")
    assert d["birthday_number"] == 11


def test_calc_single_digit_talent():
    """2000-01-01: 2+0+0+0+0+1+0+1 = 4, 天赋=生命=4"""
    d = _calc("2000-01-01")
    assert d["talent_number"] == 4
    assert d["life_number"] == 4
    assert d["birthday_number"] == 1


@pytest.mark.asyncio
async def test_engine_full_pipeline():
    r = await calculate(ChartRequest(
        system="lifenumber", name="", birth_date="1990-05-15",
        birth_time="", gender="",
    ))
    assert r.system == "lifenumber"
    assert r.raw_data["life_number"] == 3
    assert "生命密码" in r.text_summary
    assert "生命数 3" in r.text_summary
    assert "天赋数 30" in r.text_summary
    assert "生日数 6" in r.text_summary
    assert r.raw_data["interpretations"]["life"]["title"]


@pytest.mark.asyncio
async def test_engine_invalid_date():
    with pytest.raises(ValueError):
        await calculate(ChartRequest(
            system="lifenumber", name="", birth_date="",
            birth_time="", gender="",
        ))
