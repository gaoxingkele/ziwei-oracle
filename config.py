# 配置：从 .env 读取各模型 API，未设置时使用默认值
from pathlib import Path

from dotenv import load_dotenv

# 从项目根目录加载 .env：本机调试若存在 .env.local 则优先用它（云端无此文件，回落 .env）
_root = Path(__file__).resolve().parent
_env_path = _root / ".env.local" if (_root / ".env.local").exists() else _root / ".env"
load_dotenv(_env_path)

# 避免循环导入，在 load_dotenv 之后再用 os.getenv
import os


def _str(key: str, default: str = "") -> str:
    return (os.getenv(key) or default).strip()


def _str_default(key: str, default: str) -> str:
    return (os.getenv(key) or default).strip()


# ----- 当前 CLI 使用的 LLM：由 LLM_PROVIDER 决定，目前仅实现 kimi -----
LLM_PROVIDER = _str_default("LLM_PROVIDER", "kimi")

# ----- Kimi（月之暗面 Moonshot） -----
# API Key：支持 KIMI_API_KEY 或 MOONSHOT_API_KEY
KIMI_API_KEY = _str("KIMI_API_KEY") or _str("MOONSHOT_API_KEY")
KIMI_BASE_URL = _str_default("KIMI_BASE_URL", "https://api.moonshot.cn/v1")
KIMI_MODEL = _str_default("KIMI_MODEL", "kimi-latest")
KIMI_VISION_MODEL = _str_default("KIMI_VISION_MODEL", "moonshot-v1-32k-vision-preview")

# ----- OpenAI -----
OPENAI_API_KEY = _str("OPENAI_API_KEY")
OPENAI_BASE_URL = _str_default("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = _str_default("OPENAI_MODEL", "gpt-4o-mini")

# ----- xAI (Grok) -----
GROK_API_KEY = _str("GROK_API_KEY")
GROK_BASE_URL = _str_default("GROK_BASE_URL", "https://api.x.ai/v1")
GROK_MODEL = _str_default("GROK_MODEL", "grok-2")

# ----- Perplexity -----
PERPLEXITY_API_KEY = _str("PERPLEXITY_API_KEY")
PERPLEXITY_BASE_URL = _str_default("PERPLEXITY_BASE_URL", "https://api.perplexity.ai")
PERPLEXITY_MODEL = _str_default("PERPLEXITY_MODEL", "sonar")

# ----- Anthropic (Claude) -----
ANTHROPIC_API_KEY = _str("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = _str_default("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

# ----- Google (Gemini) -----
GEMINI_API_KEY = _str("GEMINI_API_KEY")
GEMINI_MODEL = _str_default("GEMINI_MODEL", "gemini-2.5-pro")

# ----- API Token（免登录模式，多个逗号分隔） -----
# API_TOKENS=token1,token2

# ----- 输出目录：默认用「当前工作目录/output」，便于在运行处直接看到文件；可用 ZIWEI_OUTPUT_DIR 覆盖 -----
OUTPUT_DIR = _str("ZIWEI_OUTPUT_DIR") or str((Path.cwd() / "output").resolve())

# ----- 西方星相学（kerykeion）默认出生地参数，可在 .env 覆盖 -----
# 说明：kerykeion 离线排盘需要经纬度和时区。默认使用北京参数。
ASTRO_CITY = _str_default("ASTRO_CITY", "Beijing")
ASTRO_NATION = _str_default("ASTRO_NATION", "CN")
ASTRO_LNG = float(_str_default("ASTRO_LNG", "116.4074"))
ASTRO_LAT = float(_str_default("ASTRO_LAT", "39.9042"))
ASTRO_TZ_STR = _str_default("ASTRO_TZ_STR", "Asia/Shanghai")
