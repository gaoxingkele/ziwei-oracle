from __future__ import annotations
from fastapi import Header, Query
from app.auth.jwt import decode_token
from app.common.exceptions import AuthError
from app.config import API_TOKENS


async def get_current_user(authorization: str = Header(default="")) -> dict:
    """JWT 认证（保留原有逻辑）。"""
    if not authorization.startswith("Bearer "):
        raise AuthError("缺少认证 Token", code=41003)
    token = authorization[7:]
    return decode_token(token)


async def verify_api_token(
    authorization: str = Header(default=""),
    token: str = Query(default=""),
) -> str:
    """API Token 校验（免登录模式）。
    支持两种传递方式:
    1. Header: Authorization: Bearer <token>
    2. Query:  ?token=<token>
    如果未配置 API_TOKENS（为空），则跳过校验（开发模式）。
    """
    if not API_TOKENS:
        return "dev"

    # 从 Header 取
    api_token = ""
    if authorization.startswith("Bearer "):
        api_token = authorization[7:]
    # 从 Query 取（优先级低于 Header）
    if not api_token and token:
        api_token = token

    if not api_token:
        raise AuthError("缺少 API Token，请在 Header 或 Query 参数中传入", code=41003)
    if api_token not in API_TOKENS:
        raise AuthError("无效的 API Token", code=41002)
    return api_token
