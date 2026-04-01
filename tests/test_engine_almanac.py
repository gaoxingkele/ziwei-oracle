import pytest
from app.engine.registry import ChartRequest, calculate
import app.engine.almanac  # noqa: F401

def test_almanac_registered():
    from app.engine.registry import ENGINES
    assert "almanac" in ENGINES

@pytest.mark.asyncio
async def test_almanac_calculate():
    req = ChartRequest(
        system="almanac", name="", birth_date="2026-03-22",
        birth_time="", gender="",
    )
    result = await calculate(req)
    assert result.system == "almanac"
    d = result.raw_data
    # 基本信息
    assert d["base"]["lunar_date"]
    assert d["base"]["gan_zhi_year"]
    # 宜忌
    assert d["yi_ji"]["yi"]
    assert d["yi_ji"]["ji"]
    # 吉神凶煞
    assert d["shen_sha"]["ji_shen"]
    assert d["shen_sha"]["tian_shen"]
    # 星宿
    assert d["xiu"]["xiu"]
    # 方位
    assert d["positions"]["xi"]
    assert d["positions"]["cai"]
    # 时辰
    assert len(d["times"]) > 0
    # 文本
    assert "黄历" in result.text_summary
    assert "宜" in result.text_summary
    assert "忌" in result.text_summary
