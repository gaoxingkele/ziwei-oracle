from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

MOCK_ALMANAC = {
    "solar_date": "2026-03-22", "lunar_date": "二月初四",
    "gan_zhi": "丙午年 辛卯月 壬申日", "yi": ["祈福"], "ji": ["动土"],
    "zodiac": "马", "jie_qi": None, "peng_zu": "壬不汲水 申不安床",
    "chong": "寅", "sha": "南",
}

@patch("app.api.v1.almanac.get_almanac_for_date", return_value=MOCK_ALMANAC)
def test_almanac_today(mock):
    resp = client.get("/api/v1/almanac/today")
    assert resp.status_code == 200
    assert resp.json()["code"] == 0

@patch("app.api.v1.almanac.get_almanac_for_date", return_value=MOCK_ALMANAC)
def test_almanac_by_date(mock):
    resp = client.get("/api/v1/almanac/2026-03-22")
    assert resp.status_code == 200
