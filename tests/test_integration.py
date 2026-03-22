from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.engine.registry import ChartResult

client = TestClient(app)

def test_full_flow():
    # 1. Send SMS code
    with patch("app.api.v1.auth.send_sms_code", return_value=True):
        resp = client.post("/api/v1/auth/sms/send", json={"phone": "13800138000"})
        assert resp.status_code == 200

    # 2. Login
    with patch("app.api.v1.auth.verify_sms_code", return_value=True):
        resp = client.post("/api/v1/auth/sms/login", json={"phone": "13800138000", "code": "123456"})
        assert resp.status_code == 200
        token = resp.json()["data"]["access_token"]
        assert token

    # 3. Chart with auth
    mock_result = ChartResult(chart_id="ch_test", system="ziwei", raw_data={"test": True}, text_summary="测试")
    with patch("app.api.v1.chart.engine_calculate", new_callable=AsyncMock, return_value=mock_result):
        resp = client.post(
            "/api/v1/chart/ziwei",
            json={"name": "张三", "birth_date": "1990-01-01", "birth_time": "寅", "gender": "男"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["chart_id"] == "ch_test"
