import pytest

def _has_lunar() -> bool:
    try:
        from lunar_python import Lunar
        return True
    except ImportError:
        return False

@pytest.mark.skipif(not _has_lunar(), reason="lunar_python not installed")
def test_almanac_today():
    from app.engine.almanac import get_almanac_for_date
    result = get_almanac_for_date("2026-03-22")
    assert result["lunar_date"]
    assert result["yi"]
    assert result["ji"]
    assert result["gan_zhi"]
