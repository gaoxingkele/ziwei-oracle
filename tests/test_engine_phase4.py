import pytest
from app.engine.registry import ChartRequest, calculate
import app.engine.name_analysis  # noqa: F401


def test_name_analysis_registered():
    from app.engine.registry import ENGINES
    assert "name_analysis" in ENGINES


@pytest.mark.asyncio
async def test_name_single_surname():
    req = ChartRequest(
        system="name_analysis", name="王伟", birth_date="1990-01-01",
        birth_time="10:00", gender="男",
    )
    result = await calculate(req)
    assert result.system == "name_analysis"
    wuge = result.raw_data["wuge"]
    assert "天格" in wuge
    assert "人格" in wuge
    assert "地格" in wuge
    assert "外格" in wuge
    assert "总格" in wuge
    assert result.raw_data["sancai"]["config"]


@pytest.mark.asyncio
async def test_name_compound_surname():
    req = ChartRequest(
        system="name_analysis", name="诸葛亮", birth_date="1990-01-01",
        birth_time="10:00", gender="男", extra={"surname_len": "2"},
    )
    result = await calculate(req)
    assert result.raw_data["surname"] == "诸葛"
    assert result.raw_data["given_name"] == "亮"


@pytest.mark.asyncio
async def test_name_three_char_given():
    req = ChartRequest(
        system="name_analysis", name="张三丰", birth_date="1990-01-01",
        birth_time="10:00", gender="男",
    )
    result = await calculate(req)
    assert result.raw_data["surname"] == "张"
    assert result.raw_data["given_name"] == "三丰"
    assert len(result.raw_data["strokes"]["given_name"]) == 2
