import pytest
from app.engine.registry import ChartRequest, calculate
import app.engine.astrology  # noqa: F401

def _has_kerykeion() -> bool:
    try:
        from kerykeion import AstrologicalSubjectFactory
        return True
    except ImportError:
        return False

def test_astrology_registered():
    from app.engine.registry import ENGINES
    assert "astrology" in ENGINES

@pytest.mark.skipif(not _has_kerykeion(), reason="kerykeion not installed")
@pytest.mark.asyncio
async def test_astrology_calculate():
    req = ChartRequest(system="astrology", name="测试", birth_date="1990-05-15", birth_time="午", gender="男")
    result = await calculate(req)
    assert result.system == "astrology"
    assert "太阳" in result.text_summary
