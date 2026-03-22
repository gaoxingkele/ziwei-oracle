import pytest
from app.engine.registry import ChartRequest, calculate
import app.engine.bazi  # noqa: F401

def _has_lunar() -> bool:
    try:
        from lunar_python import Lunar
        return True
    except ImportError:
        return False

def test_bazi_registered():
    from app.engine.registry import ENGINES
    assert "bazi" in ENGINES

@pytest.mark.skipif(not _has_lunar(), reason="lunar_python not installed")
@pytest.mark.asyncio
async def test_bazi_calculate():
    req = ChartRequest(system="bazi", name="测试", birth_date="1990-05-15", birth_time="寅", gender="男")
    result = await calculate(req)
    assert result.system == "bazi"
    assert result.raw_data.get("year_pillar")
    assert result.raw_data.get("month_pillar")
    assert result.raw_data.get("day_pillar")
    assert result.raw_data.get("hour_pillar")
