import pytest
from app.engine.registry import ChartRequest, calculate
import app.engine.qianwen  # noqa: F401
import app.engine.jiemeng  # noqa: F401


def test_phase3_registered():
    from app.engine.registry import ENGINES
    assert "qianwen" in ENGINES
    assert "jiemeng" in ENGINES


@pytest.mark.asyncio
async def test_qianwen_guanyin():
    req = ChartRequest(
        system="qianwen", name="测试", birth_date="2024-01-15",
        birth_time="10:00", gender="男", extra={"type": "guanyin"},
    )
    result = await calculate(req)
    assert result.system == "qianwen"
    assert result.raw_data["type"] == "guanyin"
    sign = result.raw_data["sign"]
    assert "number" in sign
    assert "poem" in sign


@pytest.mark.asyncio
async def test_qianwen_huangdaxian():
    req = ChartRequest(
        system="qianwen", name="测试", birth_date="2024-01-15",
        birth_time="10:00", gender="男", extra={"type": "huangdaxian"},
    )
    result = await calculate(req)
    assert result.system == "qianwen"
    assert result.raw_data["type"] == "huangdaxian"


@pytest.mark.asyncio
async def test_qianwen_zhuge():
    req = ChartRequest(
        system="qianwen", name="测试", birth_date="2024-01-15",
        birth_time="10:00", gender="男", extra={"type": "zhuge"},
    )
    result = await calculate(req)
    assert result.system == "qianwen"
    assert result.raw_data["total"] == 384


@pytest.mark.asyncio
async def test_jiemeng_search():
    req = ChartRequest(
        system="jiemeng", name="测试", birth_date="2024-01-15",
        birth_time="10:00", gender="男", question="梦见蛇",
    )
    result = await calculate(req)
    assert result.system == "jiemeng"
    assert result.raw_data["query"] == "梦见蛇"
    assert len(result.raw_data["matches"]) > 0


@pytest.mark.asyncio
async def test_jiemeng_no_match():
    req = ChartRequest(
        system="jiemeng", name="测试", birth_date="2024-01-15",
        birth_time="10:00", gender="男", question="xyzabc不存在",
    )
    result = await calculate(req)
    assert result.system == "jiemeng"
    assert len(result.raw_data["matches"]) == 0
