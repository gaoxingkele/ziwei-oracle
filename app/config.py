from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

def _str(key: str, default: str = "") -> str:
    return (os.getenv(key) or default).strip()

DATABASE_URL = _str("DATABASE_URL", "postgresql+asyncpg://oracle:oracle123@localhost:5432/ds_oracle")
REDIS_URL = _str("REDIS_URL", "redis://localhost:6379/0")
JWT_SECRET = _str("JWT_SECRET", "change-me-in-production")
JWT_ACCESS_EXPIRE_MINUTES = int(_str("JWT_ACCESS_EXPIRE_MINUTES", "120"))
JWT_REFRESH_EXPIRE_DAYS = int(_str("JWT_REFRESH_EXPIRE_DAYS", "7"))
LLM_PROVIDER = _str("LLM_PROVIDER", "kimi")
KIMI_API_KEY = _str("KIMI_API_KEY") or _str("MOONSHOT_API_KEY")
KIMI_BASE_URL = _str("KIMI_BASE_URL", "https://api.moonshot.cn/v1")
KIMI_MODEL = _str("KIMI_MODEL", "kimi-latest")
OPENAI_API_KEY = _str("OPENAI_API_KEY")
OPENAI_BASE_URL = _str("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = _str("OPENAI_MODEL", "gpt-4o-mini")
ASTRO_CITY = _str("ASTRO_CITY", "Beijing")
ASTRO_NATION = _str("ASTRO_NATION", "CN")
ASTRO_LNG = float(_str("ASTRO_LNG", "116.4074"))
ASTRO_LAT = float(_str("ASTRO_LAT", "39.9042"))
ASTRO_TZ_STR = _str("ASTRO_TZ_STR", "Asia/Shanghai")
OUTPUT_DIR = _str("ZIWEI_OUTPUT_DIR") or str((Path.cwd() / "output").resolve())
STORAGE_TYPE = _str("STORAGE_TYPE", "local")
CORS_ORIGINS = [o.strip() for o in _str("CORS_ORIGINS", "*").split(",") if o.strip()]

# API Token 认证（免登录模式，多个 token 逗号分隔）
API_TOKENS = [t.strip() for t in _str("API_TOKENS", "").split(",") if t.strip()]
