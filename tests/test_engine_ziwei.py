import pytest
from app.engine.registry import ChartRequest, calculate
import app.engine.ziwei  # noqa: F401

def test_ziwei_registered():
    from app.engine.registry import ENGINES
    assert "ziwei" in ENGINES

@pytest.mark.asyncio
async def test_ziwei_calculate():
    req = ChartRequest(system="ziwei", name="测试", birth_date="1990-05-15", birth_time="寅", gender="男")
    result = await calculate(req)
    assert result.system == "ziwei"
    assert result.raw_data
    assert "palaces" in result.raw_data
    assert result.text_summary
    assert result.chart_id.startswith("ch_")
