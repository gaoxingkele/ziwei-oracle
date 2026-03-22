from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.engine.registry import ChartResult

client = TestClient(app)

MOCK_RESULT = ChartResult(chart_id="ch_test123", system="ziwei", raw_data={"key": "value"}, text_summary="测试摘要", image_path=None)

@patch("app.api.v1.chart.engine_calculate", new_callable=AsyncMock, return_value=MOCK_RESULT)
def test_chart_ziwei(mock_calc):
    resp = client.post("/api/v1/chart/ziwei", json={"name": "张三", "birth_date": "1990-05-15", "birth_time": "寅", "gender": "男"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["chart_id"] == "ch_test123"

@patch("app.api.v1.chart.engine_calculate", new_callable=AsyncMock, return_value=MOCK_RESULT)
def test_chart_tts_format(mock_calc):
    resp = client.post("/api/v1/chart/ziwei?format=tts", json={"name": "张三", "birth_date": "1990-05-15", "birth_time": "寅", "gender": "男"})
    data = resp.json()
    assert "tts_text" in data["data"]

def test_chart_unsupported_system():
    resp = client.post("/api/v1/chart/nonexistent", json={"name": "张三", "birth_date": "1990-05-15", "birth_time": "寅", "gender": "男"})
    assert resp.status_code == 400
    assert resp.json()["code"] == 40002
