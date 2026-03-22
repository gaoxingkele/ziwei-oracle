from app.common.utils import parse_shichen, safe_filename

def test_parse_shichen_name():
    assert parse_shichen("寅") == 2

def test_parse_shichen_early_zi():
    assert parse_shichen("早子") == 0

def test_parse_shichen_late_zi():
    assert parse_shichen("晚子") == 12

def test_parse_shichen_index_string():
    assert parse_shichen("5") == 5

def test_parse_shichen_invalid():
    assert parse_shichen("无效") is None

def test_safe_filename_removes_illegal():
    assert "/" not in safe_filename("a/b:c")
    assert ":" not in safe_filename("a/b:c")

def test_safe_filename_limits_length():
    assert len(safe_filename("x" * 200, max_len=50)) == 50
