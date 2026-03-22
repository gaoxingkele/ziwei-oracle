from __future__ import annotations
import random

_codes: dict[str, str] = {}

async def send_sms_code(phone: str) -> bool:
    code = f"{random.randint(100000, 999999)}"
    _codes[phone] = code
    print(f"[DEV SMS] {phone} -> {code}")
    return True

async def verify_sms_code(phone: str, code: str) -> bool:
    expected = _codes.get(phone)
    if expected and expected == code:
        _codes.pop(phone, None)
        return True
    return False
