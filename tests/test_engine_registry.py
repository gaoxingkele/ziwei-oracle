import pytest
from app.engine.registry import (
    ChartRequest, ChartResult, register, calculate, list_systems, ENGINES,
)
from app.common.exceptions import UnsupportedSystemError

@register("mock_system")
def mock_engine(req: ChartRequest) -> ChartResult:
    return ChartResult(
        chart_id="test_id", system="mock_system",
        raw_data={"key": "value"}, text_summary="mock summary", image_path=None,
    )

def test_register_adds_to_engines():
    assert "mock_system" in ENGINES

def test_list_systems():
    assert "mock_system" in list_systems()

@pytest.mark.asyncio
async def test_calculate_returns_result():
    req = ChartRequest(
        system="mock_system", name="测试", birth_date="2000-01-01",
        birth_time="寅", gender="男",
    )
    result = await calculate(req)
    assert result.system == "mock_system"
    assert result.chart_id == "test_id"

@pytest.mark.asyncio
async def test_calculate_unsupported_system():
    req = ChartRequest(
        system="nonexistent", name="测试", birth_date="2000-01-01",
        birth_time="寅", gender="男",
    )
    with pytest.raises(UnsupportedSystemError):
        await calculate(req)
