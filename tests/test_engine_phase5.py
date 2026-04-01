import pytest
from app.engine.registry import ChartRequest, calculate
import app.engine.hehun  # noqa: F401


def test_hehun_registered():
    from app.engine.registry import ENGINES
    assert "hehun" in ENGINES


@pytest.mark.asyncio
async def test_hehun_basic():
    req = ChartRequest(
        system="hehun", name="张三", birth_date="1990-05-15",
        birth_time="寅", gender="男",
        extra={
            "spouse_birth_date": "1992-08-20",
            "spouse_birth_time": "午",
            "spouse_gender": "女",
        },
    )
    result = await calculate(req)
    assert result.system == "hehun"
    assert 0 <= result.raw_data["score"] <= 100
    assert result.raw_data["person_a"]["zodiac"]
    assert result.raw_data["person_b"]["zodiac"]
    assert len(result.raw_data["details"]) > 0


@pytest.mark.asyncio
async def test_hehun_tianhe():
    """甲己天合 pair"""
    req = ChartRequest(
        system="hehun", name="测试", birth_date="1994-03-10",
        birth_time="子", gender="男",
        extra={
            "spouse_birth_date": "1995-07-22",
            "spouse_birth_time": "子",
            "spouse_gender": "女",
        },
    )
    result = await calculate(req)
    assert result.system == "hehun"
    assert result.raw_data["score"] >= 0
