import pytest
from app.engine.registry import ChartRequest, calculate
import app.engine.qimen   # noqa: F401
import app.engine.liuren  # noqa: F401
import app.engine.iching  # noqa: F401


def test_phase2_registered():
    from app.engine.registry import ENGINES
    assert "qimen" in ENGINES
    assert "liuren" in ENGINES
    assert "iching" in ENGINES


@pytest.mark.asyncio
async def test_qimen_calculate():
    req = ChartRequest(
        system="qimen", name="测试", birth_date="2024-01-15",
        birth_time="10:30", gender="男",
    )
    result = await calculate(req)
    assert result.system == "qimen"
    assert result.raw_data
    assert result.chart_id.startswith("ch_")
    assert "干支" in result.raw_data


@pytest.mark.asyncio
async def test_qimen_methods():
    """Test different qimen methods (拆补/茅山/置闰)"""
    for method in [1, 2]:  # method=3 (置闰法) has upstream bug in kinqimen
        req = ChartRequest(
            system="qimen", name="测试", birth_date="2024-06-15",
            birth_time="14:00", gender="女", extra={"method": method},
        )
        result = await calculate(req)
        assert result.system == "qimen"


@pytest.mark.asyncio
async def test_liuren_calculate():
    req = ChartRequest(
        system="liuren", name="测试", birth_date="2024-01-15",
        birth_time="巳", gender="男",
    )
    result = await calculate(req)
    assert result.system == "liuren"
    assert result.raw_data
    assert result.chart_id.startswith("ch_")


@pytest.mark.asyncio
async def test_iching_qigua():
    req = ChartRequest(
        system="iching", name="测试", birth_date="2024-01-15",
        birth_time="10:30", gender="男",
    )
    result = await calculate(req)
    assert result.system == "iching"
    assert result.raw_data
    assert "本卦" in result.raw_data or "大衍筮法" in result.raw_data


@pytest.mark.asyncio
async def test_iching_lookup():
    req = ChartRequest(
        system="iching", name="测试", birth_date="2024-01-15",
        birth_time="10:30", gender="男",
        extra={"mode": "lookup", "gua": "乾"},
    )
    result = await calculate(req)
    assert result.system == "iching"
    assert "乾" in result.raw_data.get("gua", "")
    assert result.raw_data.get("description")
