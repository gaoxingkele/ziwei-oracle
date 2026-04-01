from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

MOCK_RAW_DATA = {
    "base": {"solar_date": "2026-03-22", "lunar_date": "二月初四", "gan_zhi_year": "丙午", "gan_zhi_month": "辛卯", "gan_zhi_day": "壬申", "na_yin_year": "", "na_yin_month": "", "na_yin_day": "", "zodiac": "马"},
    "yi_ji": {"yi": ["祈福"], "ji": ["动土"], "peng_zu_gan": "", "peng_zu_zhi": ""},
    "chong_sha": {"chong": "寅", "chong_desc": "", "chong_sheng_xiao": "", "sha": "南"},
    "shen_sha": {"ji_shen": [], "xiong_sha": [], "tian_shen": "", "tian_shen_type": "", "tian_shen_luck": ""},
    "xiu": {"xiu": "", "xiu_luck": "", "xiu_song": "", "zheng": "", "gong": "", "shou": ""},
    "nine_star": {"day": "", "month": "", "year": ""},
    "zhi_xing": "",
    "positions": {"xi": "", "cai": "", "fu": "", "yang_gui": "", "yin_gui": "", "tai_sui": ""},
    "misc": {"wu_hou": "", "hou": "", "liu_yao": "", "yue_xiang": "", "day_lu": "", "jie_qi": None},
    "times": [],
}


@patch("app.api.v1.almanac._query", return_value=MOCK_RAW_DATA)
def test_almanac_today(mock):
    resp = client.get("/api/v1/almanac/today")
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


@patch("app.api.v1.almanac._query", return_value=MOCK_RAW_DATA)
def test_almanac_by_date(mock):
    resp = client.get("/api/v1/almanac/2026-03-22")
    assert resp.status_code == 200
