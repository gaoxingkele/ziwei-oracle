import sys
import pytest
from app.engine.registry import ChartRequest, calculate
import app.engine.ziwei  # noqa: F401

def _has_iztro() -> bool:
    try:
        from py_iztro import Astro  # noqa: F401
        return True
    except ImportError:
        return False

def test_ziwei_registered():
    from app.engine.registry import ENGINES
    assert "ziwei" in ENGINES

@pytest.mark.skipif(not _has_iztro(), reason="py-iztro not installed")
@pytest.mark.skipif(sys.platform == "win32", reason="py-iztro/pythonmonkey crashes in threads on Windows")
@pytest.mark.asyncio
async def test_ziwei_calculate():
    req = ChartRequest(system="ziwei", name="测试", birth_date="1990-05-15", birth_time="寅", gender="男")
    result = await calculate(req)
    assert result.system == "ziwei"
    assert result.raw_data
