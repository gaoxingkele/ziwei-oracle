from __future__ import annotations
import time
from typing import Any

def success(data: Any = None, message: str = "success") -> dict:
    return {"code": 0, "message": message, "data": data, "timestamp": int(time.time())}

def error(code: int, message: str) -> dict:
    return {"code": code, "message": message, "data": None, "timestamp": int(time.time())}
