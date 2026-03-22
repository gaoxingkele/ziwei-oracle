import pytest
from app.engine.registry import ChartRequest, calculate
import app.engine.liuyao  # noqa: F401

def _has_najia() -> bool:
    try:
        from najia import Najia
        return True
    except ImportError:
        return False

def test_liuyao_registered():
    from app.engine.registry import ENGINES
    assert "liuyao" in ENGINES

@pytest.mark.skipif(not _has_najia(), reason="najia not installed")
@pytest.mark.asyncio
async def test_liuyao_calculate():
    req = ChartRequest(system="liuyao", name="测试", birth_date="2026-03-22", birth_time="午", gender="男", question="事业", extra={"liuyao_code": "2 2 1 2 4 2"})
    result = await calculate(req)
    assert result.system == "liuyao"
    assert result.raw_data.get("params") == [2, 2, 1, 2, 4, 2]
