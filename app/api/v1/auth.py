from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel
from app.auth.jwt import create_access_token
from app.auth.sms import send_sms_code, verify_sms_code
from app.common.exceptions import AuthError
from app.common.response import success

router = APIRouter(prefix="/auth", tags=["auth"])

class SmsSendRequest(BaseModel):
    phone: str

class SmsLoginRequest(BaseModel):
    phone: str
    code: str

@router.post("/sms/send")
async def sms_send(body: SmsSendRequest):
    await send_sms_code(body.phone)
    return success(message="验证码已发送")

@router.post("/sms/login")
async def sms_login(body: SmsLoginRequest):
    ok = await verify_sms_code(body.phone, body.code)
    if not ok:
        raise AuthError("验证码错误", code=41004)
    user_id = f"user_{body.phone[-4:]}"
    token = create_access_token(user_id=user_id, platform="app")
    return success({"access_token": token, "token_type": "bearer"})
