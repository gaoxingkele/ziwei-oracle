import pytest
from app.auth.jwt import create_access_token, decode_token
from app.common.exceptions import AuthError

def test_create_and_decode():
    token = create_access_token(user_id="test-uuid", platform="app", device_id="dev1")
    payload = decode_token(token)
    assert payload["sub"] == "test-uuid"
    assert payload["platform"] == "app"

def test_expired_token():
    token = create_access_token(user_id="test-uuid", platform="app", expire_minutes=-1)
    with pytest.raises(AuthError):
        decode_token(token)
