from __future__ import annotations
from datetime import datetime, timedelta, timezone
import jwt
from app.config import JWT_SECRET, JWT_ACCESS_EXPIRE_MINUTES
from app.common.exceptions import AuthError

def create_access_token(user_id: str, platform: str = "app", device_id: str = "", expire_minutes: int | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes if expire_minutes is not None else JWT_ACCESS_EXPIRE_MINUTES)
    payload = {"sub": user_id, "platform": platform, "device_id": device_id, "exp": expire, "iat": datetime.now(timezone.utc)}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise AuthError("Token 已过期", code=41001)
    except jwt.InvalidTokenError:
        raise AuthError("无效 Token", code=41002)
