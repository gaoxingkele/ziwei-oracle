from __future__ import annotations
from fastapi import Header
from app.auth.jwt import decode_token
from app.common.exceptions import AuthError

async def get_current_user(authorization: str = Header(default="")) -> dict:
    if not authorization.startswith("Bearer "):
        raise AuthError("缺少认证 Token", code=41003)
    token = authorization[7:]
    return decode_token(token)
