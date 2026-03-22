import pytest
from app.engine.registry import ChartRequest, calculate
import app.engine.meihua  # noqa: F401

def test_meihua_registered():
    from app.engine.registry import ENGINES
    assert "meihua" in ENGINES

@pytest.mark.asyncio
async def test_meihua_calculate():
    req = ChartRequest(system="meihua", name="测试", birth_date="2026-03-22", birth_time="午", gender="男", question="事业")
    result = await calculate(req)
    assert result.system == "meihua"
    assert result.raw_data.get("base_gua")
    assert result.raw_data.get("ti_gua")
    assert result.raw_data.get("yong_gua")
