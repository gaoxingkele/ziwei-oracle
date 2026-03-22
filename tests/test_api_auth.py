from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_sms_send():
    with patch("app.api.v1.auth.send_sms_code", return_value=True):
        resp = client.post("/api/v1/auth/sms/send", json={"phone": "13800138000"})
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

def test_sms_login_wrong_code():
    with patch("app.api.v1.auth.verify_sms_code", return_value=False):
        resp = client.post("/api/v1/auth/sms/login", json={"phone": "13800138000", "code": "000000"})
        assert resp.status_code == 400
