import pytest
from app.engine.registry import ChartRequest, calculate
import app.engine.bazi  # noqa: F401

def test_bazi_registered():
    from app.engine.registry import ENGINES
    assert "bazi" in ENGINES

@pytest.mark.asyncio
async def test_bazi_calculate():
    req = ChartRequest(system="bazi", name="测试", birth_date="1990-05-15", birth_time="寅", gender="男")
    result = await calculate(req)
    assert result.system == "bazi"
    assert result.raw_data.get("pillars")
    p = result.raw_data["pillars"]
    assert p["year"]["gan_zhi"]
    assert p["month"]["gan_zhi"]
    assert p["day"]["gan_zhi"]
    assert p["hour"]["gan_zhi"]
    # 十神
    assert result.raw_data.get("shi_shen")
    # 藏干
    assert result.raw_data.get("hide_gan")
    # 地势
    assert result.raw_data.get("di_shi")
    # 命宫/身宫
    assert result.raw_data["gong"]["ming_gong"]
    assert result.raw_data["gong"]["shen_gong"]
    # 大运
    assert result.raw_data["da_yun"]["steps"]
    assert len(result.raw_data["da_yun"]["steps"]) > 0
    # 文本
    assert "四柱" in result.text_summary
    assert "十神" in result.text_summary
    assert "大运" in result.text_summary
