# Phase 1: API 基础框架 + 引擎迁移 实施计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建 FastAPI 统一 API 框架，迁移现有 4 个术数引擎（紫微/梅花/六爻/占星）+ 新增八字和黄历引擎，实现认证系统、数据持久化和基础排盘接口。

**Architecture:** FastAPI 单体分层架构（api → engine → llm → store），引擎通过 registry 模式统一调度，PG + Redis 做持久化和缓存，JWT 做认证。

**Tech Stack:** FastAPI, SQLAlchemy (async), asyncpg, Redis, Alembic, PyJWT, pytest, httpx

**Spec:** `docs/superpowers/specs/2026-03-22-unified-api-design.md`

---

## Chunk 1: 项目骨架与配置

### Task 1: 初始化项目目录结构

**Files:**
- Create: `app/__init__.py`
- Create: `app/main.py`
- Create: `app/config.py`
- Create: `app/common/__init__.py`
- Create: `app/common/exceptions.py`
- Create: `app/common/response.py`
- Create: `app/common/utils.py`

- [ ] **Step 1: 创建 app 包和 common 子包**

```bash
mkdir -p app/common app/api/v1 app/engine app/llm app/auth app/store/models app/store/crud
touch app/__init__.py app/common/__init__.py app/api/__init__.py app/api/v1/__init__.py
touch app/engine/__init__.py app/llm/__init__.py app/auth/__init__.py
touch app/store/__init__.py app/store/models/__init__.py app/store/crud/__init__.py
```

- [ ] **Step 2: 写 app/common/utils.py 的 test**

```python
# tests/test_common_utils.py
from app.common.utils import parse_shichen, safe_filename


def test_parse_shichen_name():
    assert parse_shichen("寅") == 2


def test_parse_shichen_early_zi():
    assert parse_shichen("早子") == 0


def test_parse_shichen_late_zi():
    assert parse_shichen("晚子") == 12


def test_parse_shichen_index_string():
    assert parse_shichen("5") == 5


def test_parse_shichen_invalid():
    assert parse_shichen("无效") is None


def test_safe_filename_removes_illegal():
    assert "/" not in safe_filename("a/b:c")
    assert ":" not in safe_filename("a/b:c")


def test_safe_filename_limits_length():
    assert len(safe_filename("x" * 200, max_len=50)) == 50
```

- [ ] **Step 3: 运行测试确认失败**

Run: `pytest tests/test_common_utils.py -v`
Expected: FAIL — module not found

- [ ] **Step 4: 实现 app/common/utils.py**

```python
# app/common/utils.py
"""公共工具：时辰解析、文件名处理等（从现有 cli.py 提取）。"""
from __future__ import annotations

SHICHEN_NAMES = "早子 丑 寅 卯 辰 巳 午 未 申 酉 戌 亥 晚子".split()

# 时辰序号 → 太阳时 (hour, minute)
TIME_MAP: dict[int, tuple[int, int]] = {
    0: (0, 30), 1: (1, 30), 2: (3, 30), 3: (5, 30),
    4: (7, 30), 5: (9, 30), 6: (11, 30), 7: (13, 30),
    8: (15, 30), 9: (17, 30), 10: (19, 30), 11: (21, 30),
    12: (23, 30),
}


def parse_shichen(raw: str) -> int | None:
    """将时辰名（'寅'）或序号字符串（'2'）转为 int 0-12，无效返回 None。"""
    raw = (raw or "").strip()
    if not raw:
        return None
    # 直接匹配名称
    if raw in SHICHEN_NAMES:
        return SHICHEN_NAMES.index(raw)
    # 尝试数字
    try:
        idx = int(raw)
        if 0 <= idx <= 12:
            return idx
    except ValueError:
        pass
    return None


def safe_filename(s: str, max_len: int = 120) -> str:
    """将字符串整理为可作文件名的形式。"""
    s = (s or "").strip()
    for c in r'\/:*?"<>|':
        s = s.replace(c, "_")
    s = s.strip(".") or "unnamed"
    return s[:max_len] if len(s) > max_len else s
```

- [ ] **Step 5: 运行测试确认通过**

Run: `pytest tests/test_common_utils.py -v`
Expected: all PASS

- [ ] **Step 6: 实现 app/common/exceptions.py**

```python
# app/common/exceptions.py
"""统一异常定义。"""


class OracleError(Exception):
    """基类。"""
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class ValidationError(OracleError):
    """40000-40999: 参数校验。"""
    def __init__(self, message: str, code: int = 40001):
        super().__init__(code, message)


class AuthError(OracleError):
    """41000-41999: 认证授权。"""
    def __init__(self, message: str, code: int = 41001):
        super().__init__(code, message)


class RateLimitError(OracleError):
    """42000-42999: 限流。"""
    def __init__(self, message: str = "请求频率超限", code: int = 42001):
        super().__init__(code, message)


class BusinessError(OracleError):
    """43000-43999: 业务逻辑。"""
    def __init__(self, message: str, code: int = 43001):
        super().__init__(code, message)


class UnsupportedSystemError(ValidationError):
    """不支持的术数系统。"""
    def __init__(self, system: str):
        super().__init__(f"不支持的术数系统: {system}", code=40002)
```

- [ ] **Step 7: 实现 app/common/response.py**

```python
# app/common/response.py
"""统一响应格式。"""
from __future__ import annotations

import time
from typing import Any


def success(data: Any = None, message: str = "success") -> dict:
    return {"code": 0, "message": message, "data": data, "timestamp": int(time.time())}


def error(code: int, message: str) -> dict:
    return {"code": code, "message": message, "data": None, "timestamp": int(time.time())}
```

- [ ] **Step 8: 实现 app/config.py**

```python
# app/config.py
"""统一配置：从 .env 读取，涵盖 DB/Redis/JWT/LLM。"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


def _str(key: str, default: str = "") -> str:
    return (os.getenv(key) or default).strip()


# ---- 数据库 ----
DATABASE_URL = _str("DATABASE_URL", "postgresql+asyncpg://oracle:oracle123@localhost:5432/ds_oracle")
REDIS_URL = _str("REDIS_URL", "redis://localhost:6379/0")

# ---- JWT ----
JWT_SECRET = _str("JWT_SECRET", "change-me-in-production")
JWT_ACCESS_EXPIRE_MINUTES = int(_str("JWT_ACCESS_EXPIRE_MINUTES", "120"))
JWT_REFRESH_EXPIRE_DAYS = int(_str("JWT_REFRESH_EXPIRE_DAYS", "7"))

# ---- LLM ----
LLM_PROVIDER = _str("LLM_PROVIDER", "kimi")
KIMI_API_KEY = _str("KIMI_API_KEY") or _str("MOONSHOT_API_KEY")
KIMI_BASE_URL = _str("KIMI_BASE_URL", "https://api.moonshot.cn/v1")
KIMI_MODEL = _str("KIMI_MODEL", "kimi-latest")

OPENAI_API_KEY = _str("OPENAI_API_KEY")
OPENAI_BASE_URL = _str("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = _str("OPENAI_MODEL", "gpt-4o-mini")

# ---- 西方占星 ----
ASTRO_CITY = _str("ASTRO_CITY", "Beijing")
ASTRO_NATION = _str("ASTRO_NATION", "CN")
ASTRO_LNG = float(_str("ASTRO_LNG", "116.4074"))
ASTRO_LAT = float(_str("ASTRO_LAT", "39.9042"))
ASTRO_TZ_STR = _str("ASTRO_TZ_STR", "Asia/Shanghai")

# ---- 输出 / 存储 ----
OUTPUT_DIR = _str("ZIWEI_OUTPUT_DIR") or str((Path.cwd() / "output").resolve())
STORAGE_TYPE = _str("STORAGE_TYPE", "local")

# ---- CORS ----
CORS_ORIGINS = [o.strip() for o in _str("CORS_ORIGINS", "*").split(",") if o.strip()]
```

- [ ] **Step 9: 实现 app/main.py 最小 FastAPI 入口**

```python
# app/main.py
"""FastAPI 应用入口。"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import CORS_ORIGINS
from app.common.exceptions import OracleError
from app.common.response import error, success

app = FastAPI(title="DS-Oracle API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(OracleError)
async def oracle_error_handler(request: Request, exc: OracleError):
    status = 400 if exc.code < 50000 else 500
    return JSONResponse(status_code=status, content=error(exc.code, exc.message))


@app.get("/api/v1/health")
async def health():
    return success({"status": "ok"})
```

- [ ] **Step 10: 写 health 端点的集成测试**

```python
# tests/test_health.py
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["status"] == "ok"
```

- [ ] **Step 11: 运行测试确认通过**

Run: `pytest tests/test_health.py -v`
Expected: PASS

- [ ] **Step 12: Commit**

```bash
git add app/ tests/test_common_utils.py tests/test_health.py
git commit -m "feat: project skeleton with FastAPI, config, common utils, health endpoint"
```

---

### Task 2: Engine Registry 引擎注册表

**Files:**
- Create: `app/engine/registry.py`
- Test: `tests/test_engine_registry.py`

- [ ] **Step 1: 写 registry 测试**

```python
# tests/test_engine_registry.py
import pytest
from app.engine.registry import (
    ChartRequest, ChartResult, register, calculate, list_systems, ENGINES,
)
from app.common.exceptions import UnsupportedSystemError


@register("mock_system")
def mock_engine(req: ChartRequest) -> ChartResult:
    return ChartResult(
        chart_id="test_id",
        system="mock_system",
        raw_data={"key": "value"},
        text_summary="mock summary",
        image_path=None,
    )


def test_register_adds_to_engines():
    assert "mock_system" in ENGINES


def test_list_systems():
    systems = list_systems()
    assert "mock_system" in systems


@pytest.mark.asyncio
async def test_calculate_returns_result():
    req = ChartRequest(
        system="mock_system", name="测试", birth_date="2000-01-01",
        birth_time="寅", gender="男",
    )
    result = await calculate(req)
    assert result.system == "mock_system"
    assert result.chart_id == "test_id"


@pytest.mark.asyncio
async def test_calculate_unsupported_system():
    req = ChartRequest(
        system="nonexistent", name="测试", birth_date="2000-01-01",
        birth_time="寅", gender="男",
    )
    with pytest.raises(UnsupportedSystemError):
        await calculate(req)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_engine_registry.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 app/engine/registry.py**

```python
# app/engine/registry.py
"""引擎注册表：统一调度所有术数系统。"""
from __future__ import annotations

import asyncio
from typing import Any, Callable

from pydantic import BaseModel

from app.common.exceptions import UnsupportedSystemError


class ChartRequest(BaseModel):
    system: str
    name: str
    birth_date: str           # YYYY-MM-DD
    birth_time: str           # 时辰名或序号字符串，内部转 int 0-12
    gender: str               # "男" / "女"
    question: str = ""
    extra: dict[str, Any] = {}


class ChartResult(BaseModel):
    chart_id: str
    system: str
    raw_data: dict[str, Any]
    text_summary: str
    image_path: str | None = None


ENGINES: dict[str, Callable] = {}


def register(system: str):
    """装饰器：注册引擎。"""
    def wrapper(func: Callable) -> Callable:
        ENGINES[system] = func
        return func
    return wrapper


async def calculate(request: ChartRequest) -> ChartResult:
    """统一入口：同步引擎通过 asyncio.to_thread 包装。"""
    engine = ENGINES.get(request.system)
    if not engine:
        raise UnsupportedSystemError(request.system)
    if asyncio.iscoroutinefunction(engine):
        return await engine(request)
    return await asyncio.to_thread(engine, request)


def list_systems() -> list[str]:
    return list(ENGINES.keys())
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_engine_registry.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add app/engine/registry.py tests/test_engine_registry.py
git commit -m "feat: engine registry with @register decorator and async calculate"
```

---

## Chunk 2: 迁移现有 4 引擎

### Task 3: 迁移紫微斗数引擎

**Files:**
- Create: `app/engine/ziwei.py`
- Reference: `ziwei.py` (现有文件)
- Test: `tests/test_engine_ziwei.py`

- [ ] **Step 1: 写紫微引擎测试**

```python
# tests/test_engine_ziwei.py
"""紫微引擎测试 — 需要 py-iztro 已安装。"""
import pytest
from app.engine.registry import ChartRequest, calculate

# 确保引擎已注册
import app.engine.ziwei  # noqa: F401


def _has_iztro() -> bool:
    try:
        from py_iztro import Astro
        return True
    except ImportError:
        return False


def test_ziwei_registered():
    from app.engine.registry import ENGINES
    assert "ziwei" in ENGINES


@pytest.mark.skipif(not _has_iztro(), reason="py-iztro not installed")
@pytest.mark.asyncio
async def test_ziwei_calculate():
    req = ChartRequest(
        system="ziwei", name="测试", birth_date="1990-05-15",
        birth_time="寅", gender="男",
    )
    result = await calculate(req)
    assert result.system == "ziwei"
    assert result.raw_data  # 非空
    assert "命宫" in result.text_summary or "宫位" in result.text_summary
```

- [ ] **Step 2: 实现 app/engine/ziwei.py**

从现有 `ziwei.py` 迁移核心函数，用 `@register("ziwei")` 包装：

```python
# app/engine/ziwei.py
"""紫微斗数引擎：基于 py-iztro。"""
from __future__ import annotations

import uuid
from typing import Any

from app.common.utils import parse_shichen
from app.engine.registry import ChartRequest, ChartResult, register

try:
    from py_iztro import Astro
except ImportError:
    Astro = None  # type: ignore

SHICHEN_NAMES = "早子 丑 寅 卯 辰 巳 午 未 申 酉 戌 亥 晚子".split()


@register("ziwei")
def calculate_ziwei(req: ChartRequest) -> ChartResult:
    if Astro is None:
        raise RuntimeError("请先安装 py-iztro: pip install py-iztro")
    astro = Astro()
    time_idx = parse_shichen(req.birth_time)
    if time_idx is None:
        time_idx = 6  # 默认午时
    gender_cn = "男" if req.gender.strip().lower() in ("male", "m", "男") else "女"
    raw = astro.by_solar(req.birth_date, time_idx, gender_cn)
    data = raw.model_dump(by_alias=True, mode="json")
    text = _build_text(data)
    return ChartResult(
        chart_id=f"ch_{uuid.uuid4().hex[:12]}",
        system="ziwei",
        raw_data=data,
        text_summary=text,
    )


def _build_text(d: dict[str, Any]) -> str:
    """从现有 ziwei.py:build_text_description 迁移。"""
    lines = [
        "----------基本信息----------",
        f"命主性别：{d.get('gender', '未知')}",
        f"阳历生日：{d.get('solarDate', '未知')}",
        f"阴历生日：{d.get('lunarDate', '未知')}",
        f"八字：{d.get('chineseDate', '未知')}",
        f"生辰时辰：{d.get('time', '未知')} ({d.get('timeRange', '未知')})",
        f"星座：{d.get('sign', '未知')}",
        f"生肖：{d.get('zodiac', '未知')}",
        f"命宫地支：{d.get('earthlyBranchOfSoulPalace', '未知')}",
        f"五行局：{d.get('fiveElementsClass', '未知')}",
        "----------宫位信息----------",
    ]
    for p in d.get("palaces") or []:
        name = p.get("name", "?")
        major = p.get("majorStars") or []
        stars = ", ".join(f"{s.get('name', '')}({s.get('brightness', '')})" for s in major)
        lines.append(f"[{name}] 主星: {stars or '无'}")
    return "\n".join(lines)
```

- [ ] **Step 3: 运行测试**

Run: `pytest tests/test_engine_ziwei.py -v`
Expected: PASS (or skip if py-iztro not installed)

- [ ] **Step 4: Commit**

```bash
git add app/engine/ziwei.py tests/test_engine_ziwei.py
git commit -m "feat: migrate ziwei engine to app/engine with registry"
```

---

### Task 4: 迁移梅花易数引擎

**Files:**
- Create: `app/engine/meihua.py`
- Reference: `meihua.py` (现有)
- Test: `tests/test_engine_meihua.py`

- [ ] **Step 1: 写测试**

```python
# tests/test_engine_meihua.py
import pytest
from app.engine.registry import ChartRequest, calculate

import app.engine.meihua  # noqa: F401


def test_meihua_registered():
    from app.engine.registry import ENGINES
    assert "meihua" in ENGINES


@pytest.mark.asyncio
async def test_meihua_calculate():
    req = ChartRequest(
        system="meihua", name="测试", birth_date="2026-03-22",
        birth_time="午", gender="男", question="事业",
    )
    result = await calculate(req)
    assert result.system == "meihua"
    assert result.raw_data.get("base_gua")  # 非空字符串
    assert result.raw_data.get("ti_gua")
    assert result.raw_data.get("yong_gua")
```

- [ ] **Step 2: 实现 app/engine/meihua.py**

```python
# app/engine/meihua.py
"""梅花易数引擎：内联计算逻辑（从根目录 meihua.py 迁移，避免跨包导入问题）。"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.engine.registry import ChartRequest, ChartResult, register


@dataclass(frozen=True)
class Trigram:
    idx: int; name: str; symbol: str; element: str; lines: tuple[int, int, int]


TRIGRAMS: dict[int, Trigram] = {
    1: Trigram(1, "乾", "☰", "金", (1, 1, 1)), 2: Trigram(2, "兑", "☱", "金", (1, 1, 0)),
    3: Trigram(3, "离", "☲", "火", (1, 0, 1)), 4: Trigram(4, "震", "☳", "木", (1, 0, 0)),
    5: Trigram(5, "巽", "☴", "木", (0, 1, 1)), 6: Trigram(6, "坎", "☵", "水", (0, 1, 0)),
    7: Trigram(7, "艮", "☶", "土", (0, 0, 1)), 8: Trigram(8, "坤", "☷", "土", (0, 0, 0)),
}
_BY_LINES = {t.lines: t for t in TRIGRAMS.values()}
_MOVING_NAMES = {1: "初爻", 2: "二爻", 3: "三爻", 4: "四爻", 5: "五爻", 6: "上爻"}
_WUXING = {
    "金": {"金": "比和", "木": "体克用", "水": "体生用", "火": "用克体", "土": "用生体"},
    "木": {"木": "比和", "土": "体克用", "火": "体生用", "金": "用克体", "水": "用生体"},
    "水": {"水": "比和", "火": "体克用", "木": "体生用", "土": "用克体", "金": "用生体"},
    "火": {"火": "比和", "金": "体克用", "土": "体生用", "水": "用克体", "木": "用生体"},
    "土": {"土": "比和", "水": "体克用", "金": "体生用", "木": "用克体", "火": "用生体"},
}


def _calc(topic: str, t: datetime) -> dict[str, Any]:
    y, m, d, h = t.year, t.month, t.day, t.hour
    up_idx = (y + m + d) % 8 or 8
    lo_idx = (y + m + d + h) % 8 or 8
    mv = (y + m + d + h) % 6 or 6
    up, lo = TRIGRAMS[up_idx], TRIGRAMS[lo_idx]
    base = list(lo.lines + up.lines)
    hu_lo = _BY_LINES[tuple(base[1:4])]; hu_up = _BY_LINES[tuple(base[2:5])]
    chg = base.copy(); chg[mv - 1] = 1 - chg[mv - 1]
    chg_lo = _BY_LINES[tuple(chg[:3])]; chg_up = _BY_LINES[tuple(chg[3:])]
    ti = up if mv > 3 else lo; yong = lo if mv > 3 else up
    return {
        "upper_trigram": up.name, "lower_trigram": lo.name,
        "base_gua": f"上{up.name}下{lo.name}", "mutual_gua": f"上{hu_up.name}下{hu_lo.name}",
        "changed_gua": f"上{chg_up.name}下{chg_lo.name}",
        "moving_line": mv, "moving_line_name": _MOVING_NAMES[mv],
        "ti_gua": ti.name, "yong_gua": yong.name,
        "relation": _WUXING.get(ti.element, {}).get(yong.element, "比和"),
        "occurred_at": t.isoformat(),
    }


@register("meihua")
def calculate_meihua_engine(req: ChartRequest) -> ChartResult:
    now = datetime.now()
    data = _calc(topic=req.question or "综合", t=now)
    text = (
        f"本卦: {data['base_gua']}, 互卦: {data['mutual_gua']}, "
        f"变卦: {data['changed_gua']}, 动爻: {data['moving_line_name']}, "
        f"体卦: {data['ti_gua']}, 用卦: {data['yong_gua']}, 关系: {data['relation']}"
    )
    return ChartResult(
        chart_id=f"ch_{uuid.uuid4().hex[:12]}",
        system="meihua",
        raw_data=data,
        text_summary=text,
    )
```

- [ ] **Step 3: 运行测试**

Run: `pytest tests/test_engine_meihua.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add app/engine/meihua.py tests/test_engine_meihua.py
git commit -m "feat: migrate meihua engine to app/engine with registry"
```

---

### Task 5: 迁移六爻引擎

**Files:**
- Create: `app/engine/liuyao.py`
- Reference: `liuyao.py` (现有)
- Test: `tests/test_engine_liuyao.py`

- [ ] **Step 1: 写测试**

```python
# tests/test_engine_liuyao.py
import asyncio
import pytest
from app.engine.registry import ChartRequest, calculate

import app.engine.liuyao  # noqa: F401


def test_liuyao_registered():
    from app.engine.registry import ENGINES
    assert "liuyao" in ENGINES


def _has_najia() -> bool:
    try:
        from najia import Najia
        return True
    except ImportError:
        return False


@pytest.mark.skipif(not _has_najia(), reason="najia not installed")
@pytest.mark.asyncio
async def test_liuyao_calculate():
    req = ChartRequest(
        system="liuyao", name="测试", birth_date="2026-03-22",
        birth_time="午", gender="男", question="事业",
        extra={"liuyao_code": "2 2 1 2 4 2"},
    )
    result = await calculate(req)
    assert result.system == "liuyao"
    assert result.raw_data.get("params") == [2, 2, 1, 2, 4, 2]
```

- [ ] **Step 2: 实现 app/engine/liuyao.py**

```python
# app/engine/liuyao.py
"""六爻引擎：基于 najia，移除硬编码路径。"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from app.engine.registry import ChartRequest, ChartResult, register

try:
    from najia import Najia  # type: ignore
except ImportError:
    Najia = None


def _normalize_params(raw: str) -> list[int]:
    items = (raw or "").strip().split()
    vals: list[int] = []
    for token in items[:6]:
        try:
            v = int(token)
        except ValueError:
            v = 2
        vals.append(max(1, min(4, v)))
    while len(vals) < 6:
        vals.append(2)
    return vals


@register("liuyao")
def calculate_liuyao_engine(req: ChartRequest) -> ChartResult:
    if Najia is None:
        raise RuntimeError("请先安装 najia: pip install najia")
    code = req.extra.get("liuyao_code", "2 2 2 2 2 2")
    params = _normalize_params(code)
    use_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    obj = Najia(verbose=2).compile(
        params=params, date=use_date,
        gender=req.gender or "", title=req.question or "", guaci=False,
    )
    rendered = obj.render()
    data: dict[str, Any] = obj.data or {}
    return ChartResult(
        chart_id=f"ch_{uuid.uuid4().hex[:12]}",
        system="liuyao",
        raw_data={"rendered_text": rendered, "params": params, "date": use_date, "data": data},
        text_summary=rendered[:500] if rendered else "",
    )
```

- [ ] **Step 3: 运行测试**

Run: `pytest tests/test_engine_liuyao.py -v`
Expected: PASS or skip

- [ ] **Step 4: Commit**

```bash
git add app/engine/liuyao.py tests/test_engine_liuyao.py
git commit -m "feat: migrate liuyao engine, remove hardcoded path fallback"
```

---

### Task 6: 迁移西洋占星引擎

**Files:**
- Create: `app/engine/astrology.py`
- Reference: `astrology.py` (现有)
- Test: `tests/test_engine_astrology.py`

- [ ] **Step 1: 写测试**

```python
# tests/test_engine_astrology.py
import asyncio
import pytest
from app.engine.registry import ChartRequest, calculate

import app.engine.astrology  # noqa: F401


def test_astrology_registered():
    from app.engine.registry import ENGINES
    assert "astrology" in ENGINES


def _has_kerykeion() -> bool:
    try:
        from kerykeion import AstrologicalSubjectFactory
        return True
    except ImportError:
        return False


@pytest.mark.skipif(not _has_kerykeion(), reason="kerykeion not installed")
@pytest.mark.asyncio
async def test_astrology_calculate():
    req = ChartRequest(
        system="astrology", name="测试", birth_date="1990-05-15",
        birth_time="午", gender="男",
    )
    result = await calculate(req)
    assert result.system == "astrology"
    assert "太阳" in result.text_summary
```

- [ ] **Step 2: 实现 app/engine/astrology.py**

```python
# app/engine/astrology.py
"""西洋占星引擎：基于 kerykeion。"""
from __future__ import annotations

import uuid

from app.common.utils import TIME_MAP, parse_shichen
from app.config import ASTRO_CITY, ASTRO_LAT, ASTRO_LNG, ASTRO_NATION, ASTRO_TZ_STR
from app.engine.registry import ChartRequest, ChartResult, register

try:
    from kerykeion import AstrologicalSubjectFactory
except ImportError:
    AstrologicalSubjectFactory = None  # type: ignore


def _point_summary(subject: object, attr_name: str, label: str) -> str:
    point = getattr(subject, attr_name, None)
    if point is None:
        return f"- {label}: 无"
    sign = getattr(point, "sign", "") or ""
    house = getattr(point, "house", "") or ""
    position = getattr(point, "position", None)
    pos_text = f"{position:.2f}°" if isinstance(position, (int, float)) else ""
    if house:
        return f"- {label}: {sign} {pos_text}（{house}）".strip()
    return f"- {label}: {sign} {pos_text}".strip()


@register("astrology")
def calculate_astrology_engine(req: ChartRequest) -> ChartResult:
    if AstrologicalSubjectFactory is None:
        raise RuntimeError("请先安装 kerykeion: pip install kerykeion")
    time_idx = parse_shichen(req.birth_time) or 6
    hour, minute = TIME_MAP.get(time_idx, (11, 30))
    parts = req.birth_date.split("-")
    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
    subject = AstrologicalSubjectFactory.from_birth_data(
        name=req.name, year=year, month=month, day=day,
        hour=hour, minute=minute,
        city=ASTRO_CITY, nation=ASTRO_NATION,
        lng=ASTRO_LNG, lat=ASTRO_LAT, tz_str=ASTRO_TZ_STR, online=False,
    )
    lines = ["【西方星相学关键位】"]
    for attr, label in [
        ("sun", "太阳"), ("moon", "月亮"), ("ascendant", "上升"),
        ("mercury", "水星"), ("venus", "金星"), ("mars", "火星"),
        ("jupiter", "木星"), ("saturn", "土星"),
    ]:
        lines.append(_point_summary(subject, attr, label))
    text = "\n".join(lines)
    raw = {}
    try:
        raw = subject.model_dump(mode="json")
    except Exception:
        pass
    return ChartResult(
        chart_id=f"ch_{uuid.uuid4().hex[:12]}",
        system="astrology",
        raw_data=raw,
        text_summary=text,
    )
```

- [ ] **Step 3: 运行测试**

Run: `pytest tests/test_engine_astrology.py -v`
Expected: PASS or skip

- [ ] **Step 4: Commit**

```bash
git add app/engine/astrology.py tests/test_engine_astrology.py
git commit -m "feat: migrate astrology engine to app/engine with registry"
```

---

## Chunk 3: 排盘 API 路由

### Task 7: Chart API 路由

**Files:**
- Create: `app/api/v1/router.py`
- Create: `app/api/v1/chart.py`
- Modify: `app/main.py`
- Test: `tests/test_api_chart.py`

- [ ] **Step 1: 写 chart API 测试**

```python
# tests/test_api_chart.py
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.engine.registry import ChartResult

client = TestClient(app)

MOCK_RESULT = ChartResult(
    chart_id="ch_test123",
    system="ziwei",
    raw_data={"key": "value"},
    text_summary="测试摘要",
    image_path=None,
)


@patch("app.api.v1.chart.engine_calculate", new_callable=AsyncMock, return_value=MOCK_RESULT)
def test_chart_ziwei(mock_calc):
    resp = client.post("/api/v1/chart/ziwei", json={
        "name": "张三", "birth_date": "1990-05-15",
        "birth_time": "寅", "gender": "男",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["chart_id"] == "ch_test123"
    assert data["data"]["system"] == "ziwei"


@patch("app.api.v1.chart.engine_calculate", new_callable=AsyncMock, return_value=MOCK_RESULT)
def test_chart_tts_format(mock_calc):
    resp = client.post("/api/v1/chart/ziwei?format=tts", json={
        "name": "张三", "birth_date": "1990-05-15",
        "birth_time": "寅", "gender": "男",
    })
    data = resp.json()
    assert "tts_text" in data["data"]


def test_chart_unsupported_system():
    resp = client.post("/api/v1/chart/nonexistent", json={
        "name": "张三", "birth_date": "1990-05-15",
        "birth_time": "寅", "gender": "男",
    })
    assert resp.status_code == 400
    assert resp.json()["code"] == 40002
```

- [ ] **Step 2: 实现 app/api/v1/chart.py**

```python
# app/api/v1/chart.py
"""排盘接口：同步计算，毫秒级返回。"""
from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.common.response import success
from app.engine.registry import ChartRequest, calculate as engine_calculate

router = APIRouter(prefix="/chart", tags=["chart"])


class ChartBody(BaseModel):
    name: str
    birth_date: str
    birth_time: str
    gender: str
    question: str = ""
    extra: dict = {}


@router.post("/{system}")
async def create_chart(system: str, body: ChartBody, format: str = Query(default="")):
    req = ChartRequest(system=system, **body.model_dump())
    result = await engine_calculate(req)
    data = {
        "chart_id": result.chart_id,
        "system": result.system,
        "raw_data": result.raw_data,
        "text_summary": result.text_summary,
        "image_url": f"/files/charts/{result.chart_id}.png" if result.image_path else None,
    }
    if format == "tts":
        data = {"chart_id": result.chart_id, "tts_text": result.text_summary}
    return success(data)
```

- [ ] **Step 3: 实现 app/api/v1/router.py**

```python
# app/api/v1/router.py
"""V1 总路由。"""
from fastapi import APIRouter

from app.api.v1.chart import router as chart_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(chart_router)
```

- [ ] **Step 4: 修改 app/main.py 挂载 v1 路由**

在 `app/main.py` 的 `app = FastAPI(...)` 之后添加：

```python
from app.api.v1.router import v1_router
app.include_router(v1_router)
```

同时确保所有引擎被导入注册：

```python
# 导入引擎以触发 @register
import app.engine.ziwei  # noqa: F401
import app.engine.meihua  # noqa: F401
import app.engine.liuyao  # noqa: F401
import app.engine.astrology  # noqa: F401
```

- [ ] **Step 5: 运行测试**

Run: `pytest tests/test_api_chart.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add app/api/ app/main.py tests/test_api_chart.py
git commit -m "feat: chart API routes with /chart/{system} endpoint and tts format"
```

---

## Chunk 4: 数据库与认证

### Task 8: 数据库 ORM 模型 + Alembic

**Files:**
- Create: `app/store/database.py`
- Create: `app/store/models/user.py`
- Create: `app/store/models/chart.py`
- Create: `app/store/models/session.py`
- Create: `app/store/models/reading.py`
- Create: `app/store/models/api_key.py`

- [ ] **Step 1: 实现 app/store/database.py**

```python
# app/store/database.py
"""SQLAlchemy async engine + session。"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session
```

- [ ] **Step 2: 实现 user 模型**

```python
# app/store/models/user.py
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, SmallInteger, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.store.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    wechat_openid: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    wechat_unionid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    nickname: Mapped[str] = mapped_column(String(50), default="")
    avatar_url: Mapped[str] = mapped_column(String(500), default="")
    birth_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    birth_time: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(4), nullable=True)
    birth_city: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
```

- [ ] **Step 3: 实现 chart 模型**

```python
# app/store/models/chart.py
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.store.database import Base


class Chart(Base):
    __tablename__ = "charts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    system: Mapped[str] = mapped_column(String(20))
    params: Mapped[dict] = mapped_column(JSONB)
    result: Mapped[dict] = mapped_column(JSONB)
    text_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 4: 初始化 Alembic**

```bash
pip install alembic
alembic init alembic
```

修改 `alembic/env.py` 的 `target_metadata` 指向 `Base.metadata`，`sqlalchemy.url` 从 config 读取。

- [ ] **Step 5: 生成初始迁移**

```bash
alembic revision --autogenerate -m "initial tables"
alembic upgrade head
```

- [ ] **Step 6: Commit**

```bash
git add app/store/ alembic/ alembic.ini
git commit -m "feat: database models (users, charts, sessions, messages, readings, api_keys) with Alembic"
```

---

### Task 9: JWT 认证

**Files:**
- Create: `app/auth/jwt.py`
- Create: `app/api/deps.py`
- Test: `tests/test_auth_jwt.py`

- [ ] **Step 1: 写 JWT 测试**

```python
# tests/test_auth_jwt.py
import pytest
from app.auth.jwt import create_access_token, decode_token


def test_create_and_decode():
    token = create_access_token(user_id="test-uuid", platform="app", device_id="dev1")
    payload = decode_token(token)
    assert payload["sub"] == "test-uuid"
    assert payload["platform"] == "app"


def test_expired_token():
    from app.common.exceptions import AuthError
    token = create_access_token(user_id="test-uuid", platform="app", expire_minutes=-1)
    with pytest.raises(AuthError):
        decode_token(token)
```

- [ ] **Step 2: 实现 app/auth/jwt.py**

```python
# app/auth/jwt.py
"""JWT 签发与验证。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt

from app.config import JWT_SECRET, JWT_ACCESS_EXPIRE_MINUTES
from app.common.exceptions import AuthError


def create_access_token(
    user_id: str,
    platform: str = "app",
    device_id: str = "",
    expire_minutes: int | None = None,
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expire_minutes if expire_minutes is not None else JWT_ACCESS_EXPIRE_MINUTES
    )
    payload = {
        "sub": user_id,
        "platform": platform,
        "device_id": device_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise AuthError("Token 已过期", code=41001)
    except jwt.InvalidTokenError:
        raise AuthError("无效 Token", code=41002)
```

- [ ] **Step 3: 实现 app/api/deps.py**

```python
# app/api/deps.py
"""公共依赖注入。"""
from __future__ import annotations

from fastapi import Depends, Header

from app.auth.jwt import decode_token
from app.common.exceptions import AuthError


async def get_current_user(authorization: str = Header(default="")) -> dict:
    """从 Authorization: Bearer <token> 解析用户。"""
    if not authorization.startswith("Bearer "):
        raise AuthError("缺少认证 Token", code=41003)
    token = authorization[7:]
    return decode_token(token)
```

- [ ] **Step 4: 运行测试**

Run: `pytest tests/test_auth_jwt.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add app/auth/jwt.py app/api/deps.py tests/test_auth_jwt.py
git commit -m "feat: JWT auth with create/decode token and FastAPI dependency"
```

---

### Task 10: SMS 登录接口（骨架）

**Files:**
- Create: `app/auth/sms.py`
- Create: `app/api/v1/auth.py`
- Modify: `app/api/v1/router.py`
- Test: `tests/test_api_auth.py`

- [ ] **Step 1: 写登录接口测试**

```python
# tests/test_api_auth.py
from unittest.mock import patch, AsyncMock
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
        resp = client.post("/api/v1/auth/sms/login", json={
            "phone": "13800138000", "code": "000000",
        })
        assert resp.status_code == 400
```

- [ ] **Step 2: 实现 app/auth/sms.py**

```python
# app/auth/sms.py
"""短信验证码：骨架实现，生产环境替换为阿里云 SMS。"""
from __future__ import annotations

import random

# 内存存储（开发用），生产用 Redis
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
```

- [ ] **Step 3: 实现 app/api/v1/auth.py**

```python
# app/api/v1/auth.py
"""认证接口。"""
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
    # TODO: 查询或创建用户（需要数据库接入后完善）
    user_id = f"user_{body.phone[-4:]}"
    token = create_access_token(user_id=user_id, platform="app")
    return success({"access_token": token, "token_type": "bearer"})
```

- [ ] **Step 4: 挂载 auth 路由到 v1_router**

在 `app/api/v1/router.py` 添加：

```python
from app.api.v1.auth import router as auth_router
v1_router.include_router(auth_router)
```

- [ ] **Step 5: 运行测试**

Run: `pytest tests/test_api_auth.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add app/auth/sms.py app/api/v1/auth.py app/api/v1/router.py tests/test_api_auth.py
git commit -m "feat: SMS auth endpoints with dev-mode verification"
```

---

## Chunk 5: Docker 与集成验证

### Task 11: Docker Compose + 环境配置

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Modify: `.env.example`

- [ ] **Step 1: 创建 Dockerfile**

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

- [ ] **Step 2: 创建 docker-compose.yml**

```yaml
# docker-compose.yml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      - postgres
      - redis
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ds_oracle
      POSTGRES_USER: oracle
      POSTGRES_PASSWORD: oracle123
    ports:
      - "5432:5432"
    volumes:
      - pg_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  pg_data:
  redis_data:
```

- [ ] **Step 3: 更新 .env.example**

在现有 `.env.example` 末尾追加：

```bash
# ---- Database ----
DATABASE_URL=postgresql+asyncpg://oracle:oracle123@localhost:5432/ds_oracle
REDIS_URL=redis://localhost:6379/0

# ---- JWT ----
JWT_SECRET=change-me-in-production
JWT_ACCESS_EXPIRE_MINUTES=120
JWT_REFRESH_EXPIRE_DAYS=7

# ---- CORS ----
CORS_ORIGINS=*
```

- [ ] **Step 4: 更新 requirements.txt**

追加：

```txt
fastapi>=0.110
uvicorn[standard]>=0.27
websockets>=12.0
pydantic>=2.0
sqlalchemy[asyncio]>=2.0
asyncpg>=0.29
alembic>=1.13
redis[hiredis]>=5.0
pyjwt>=2.8
httpx>=0.27
pytest>=8.0
pytest-asyncio>=0.23
lunar_python>=1.7
```

- [ ] **Step 5: 验证 docker-compose 启动**

```bash
docker-compose up -d postgres redis
# 等待 PG 就绪后：
alembic upgrade head
uvicorn app.main:app --reload
# 在另一终端：
curl http://localhost:8000/api/v1/health
```

Expected: `{"code": 0, "data": {"status": "ok"}, ...}`

- [ ] **Step 6: Commit**

```bash
git add Dockerfile docker-compose.yml .env.example requirements.txt
git commit -m "feat: Docker Compose with PG + Redis, updated requirements and env"
```

---

### Task 12: 端到端集成测试

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: 写端到端测试**

```python
# tests/test_integration.py
"""端到端集成测试：健康检查 + 排盘（mock 引擎）+ 认证流程。"""
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.engine.registry import ChartResult

client = TestClient(app)


def test_full_flow():
    """模拟完整流程：登录 → 排盘。"""
    # 1. 发送验证码
    with patch("app.api.v1.auth.send_sms_code", return_value=True):
        resp = client.post("/api/v1/auth/sms/send", json={"phone": "13800138000"})
        assert resp.status_code == 200

    # 2. 登录获取 token
    with patch("app.api.v1.auth.verify_sms_code", return_value=True):
        resp = client.post("/api/v1/auth/sms/login", json={
            "phone": "13800138000", "code": "123456",
        })
        assert resp.status_code == 200
        token = resp.json()["data"]["access_token"]
        assert token

    # 3. 排盘
    mock_result = ChartResult(
        chart_id="ch_test", system="ziwei",
        raw_data={"test": True}, text_summary="测试",
    )
    with patch("app.api.v1.chart.engine_calculate", new_callable=AsyncMock, return_value=mock_result):
        resp = client.post(
            "/api/v1/chart/ziwei",
            json={"name": "张三", "birth_date": "1990-01-01", "birth_time": "寅", "gender": "男"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["chart_id"] == "ch_test"
```

- [ ] **Step 2: 运行全部测试**

Run: `pytest tests/ -v --tb=short`
Expected: all PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: end-to-end integration test for auth + chart flow"
```

---

## Chunk 6: 八字 + 黄历引擎 + 项目配置补全

### Task 13: pytest 配置与 conftest

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `pyproject.toml`

- [ ] **Step 1: 创建 pytest 配置**

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

```python
# tests/__init__.py
# (empty)
```

```python
# tests/conftest.py
"""共享 fixtures。"""
```

- [ ] **Step 2: 安装 pytest-asyncio**

```bash
pip install pytest-asyncio
```

在 `requirements.txt` 追加 `pytest-asyncio>=0.23`。

- [ ] **Step 3: Commit**

```bash
git add tests/__init__.py tests/conftest.py pyproject.toml requirements.txt
git commit -m "chore: add pytest config with asyncio auto mode and conftest"
```

---

### Task 14: 八字引擎（新增）

**Files:**
- Create: `app/engine/bazi.py`
- Test: `tests/test_engine_bazi.py`

- [ ] **Step 1: 写测试**

```python
# tests/test_engine_bazi.py
import pytest
from app.engine.registry import ChartRequest, calculate

import app.engine.bazi  # noqa: F401


def _has_lunar() -> bool:
    try:
        from lunar_python import Lunar
        return True
    except ImportError:
        return False


def test_bazi_registered():
    from app.engine.registry import ENGINES
    assert "bazi" in ENGINES


@pytest.mark.skipif(not _has_lunar(), reason="lunar_python not installed")
@pytest.mark.asyncio
async def test_bazi_calculate():
    req = ChartRequest(
        system="bazi", name="测试", birth_date="1990-05-15",
        birth_time="寅", gender="男",
    )
    result = await calculate(req)
    assert result.system == "bazi"
    assert result.raw_data.get("year_pillar")
    assert result.raw_data.get("month_pillar")
    assert result.raw_data.get("day_pillar")
    assert result.raw_data.get("hour_pillar")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_engine_bazi.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 app/engine/bazi.py**

```python
# app/engine/bazi.py
"""八字（四柱）引擎：基于 lunar_python。"""
from __future__ import annotations

import uuid
from typing import Any

from app.common.utils import TIME_MAP, parse_shichen
from app.engine.registry import ChartRequest, ChartResult, register

try:
    from lunar_python import Lunar, Solar
except ImportError:
    Lunar = None  # type: ignore
    Solar = None  # type: ignore


@register("bazi")
def calculate_bazi_engine(req: ChartRequest) -> ChartResult:
    if Lunar is None:
        raise RuntimeError("请先安装 lunar_python: pip install lunar_python")
    parts = req.birth_date.split("-")
    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
    time_idx = parse_shichen(req.birth_time) or 6
    hour, minute = TIME_MAP.get(time_idx, (11, 30))
    solar = Solar.fromYmdHms(year, month, day, hour, minute, 0)
    lunar = solar.getLunar()
    ba_zi = lunar.getEightChar()
    data: dict[str, Any] = {
        "year_pillar": ba_zi.getYear(),
        "month_pillar": ba_zi.getMonth(),
        "day_pillar": ba_zi.getDay(),
        "hour_pillar": ba_zi.getTime(),
        "year_gan": ba_zi.getYearGan(),
        "year_zhi": ba_zi.getYearZhi(),
        "day_gan": ba_zi.getDayGan(),
        "day_zhi": ba_zi.getDayZhi(),
        "solar_date": str(solar),
        "lunar_date": str(lunar),
        "zodiac": lunar.getYearShengXiao(),
    }
    text = (
        f"四柱: {data['year_pillar']} {data['month_pillar']} "
        f"{data['day_pillar']} {data['hour_pillar']}\n"
        f"阳历: {data['solar_date']}, 阴历: {data['lunar_date']}\n"
        f"生肖: {data['zodiac']}"
    )
    return ChartResult(
        chart_id=f"ch_{uuid.uuid4().hex[:12]}",
        system="bazi",
        raw_data=data,
        text_summary=text,
    )
```

- [ ] **Step 4: 运行测试**

Run: `pytest tests/test_engine_bazi.py -v`
Expected: PASS or skip

- [ ] **Step 5: Commit**

```bash
git add app/engine/bazi.py tests/test_engine_bazi.py
git commit -m "feat: add bazi (four pillars) engine with lunar_python"
```

---

### Task 15: 黄历/择日引擎（新增）

**Files:**
- Create: `app/engine/almanac.py`
- Create: `app/api/v1/almanac.py`
- Modify: `app/api/v1/router.py`
- Test: `tests/test_engine_almanac.py`

- [ ] **Step 1: 写测试**

```python
# tests/test_engine_almanac.py
import pytest

def _has_lunar() -> bool:
    try:
        from lunar_python import Lunar
        return True
    except ImportError:
        return False


@pytest.mark.skipif(not _has_lunar(), reason="lunar_python not installed")
def test_almanac_today():
    from app.engine.almanac import get_almanac_for_date
    result = get_almanac_for_date("2026-03-22")
    assert result["lunar_date"]
    assert result["yi"]       # 宜
    assert result["ji"]       # 忌
    assert result["gan_zhi"]  # 干支
```

- [ ] **Step 2: 实现 app/engine/almanac.py**

```python
# app/engine/almanac.py
"""黄历/择日引擎：基于 lunar_python。"""
from __future__ import annotations

from typing import Any

try:
    from lunar_python import Solar
except ImportError:
    Solar = None  # type: ignore


def get_almanac_for_date(date_str: str) -> dict[str, Any]:
    """查询指定日期的黄历信息。"""
    if Solar is None:
        raise RuntimeError("请先安装 lunar_python: pip install lunar_python")
    parts = date_str.split("-")
    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
    solar = Solar.fromYmd(year, month, day)
    lunar = solar.getLunar()
    return {
        "solar_date": str(solar),
        "lunar_date": str(lunar),
        "gan_zhi": f"{lunar.getYearInGanZhi()}年 {lunar.getMonthInGanZhi()}月 {lunar.getDayInGanZhi()}日",
        "yi": lunar.getDayYi(),    # 宜
        "ji": lunar.getDayJi(),    # 忌
        "zodiac": lunar.getYearShengXiao(),
        "jie_qi": lunar.getCurrentJieQi() or lunar.getPrevJieQi(),
        "peng_zu": lunar.getPengZuGan() + " " + lunar.getPengZuZhi(),
        "chong": lunar.getDayChong(),
        "sha": lunar.getDaySha(),
    }
```

- [ ] **Step 3: 实现 app/api/v1/almanac.py**

```python
# app/api/v1/almanac.py
"""黄历接口。"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter

from app.common.response import success
from app.engine.almanac import get_almanac_for_date

router = APIRouter(prefix="/almanac", tags=["almanac"])


@router.get("/today")
async def almanac_today():
    return success(get_almanac_for_date(date.today().isoformat()))


@router.get("/{date_str}")
async def almanac_by_date(date_str: str):
    return success(get_almanac_for_date(date_str))
```

- [ ] **Step 4: 挂载 almanac 路由**

在 `app/api/v1/router.py` 添加：

```python
from app.api.v1.almanac import router as almanac_router
v1_router.include_router(almanac_router)
```

- [ ] **Step 5: 在 app/main.py 注册 bazi 引擎**

追加：

```python
import app.engine.bazi  # noqa: F401
```

- [ ] **Step 6: 运行测试**

Run: `pytest tests/test_engine_almanac.py -v`
Expected: PASS or skip

- [ ] **Step 7: Commit**

```bash
git add app/engine/almanac.py app/engine/bazi.py app/api/v1/almanac.py app/api/v1/router.py app/main.py tests/test_engine_almanac.py
git commit -m "feat: add bazi engine + almanac engine with lunar_python, almanac API routes"
```

---

### Task 16: 添加 .dockerignore

**Files:**
- Create: `.dockerignore`

- [ ] **Step 1: 创建 .dockerignore**

```
.git
.env
__pycache__
*.pyc
output/
tests/
docs/
*.md
.dockerignore
```

- [ ] **Step 2: Commit**

```bash
git add .dockerignore
git commit -m "chore: add .dockerignore to exclude secrets and dev files"
```

---

## Phase 1 完成标准

- [ ] `GET /api/v1/health` 返回 200
- [ ] `POST /api/v1/chart/{system}` 支持 ziwei, meihua, liuyao, astrology, bazi 五个系统
- [ ] `GET /api/v1/almanac/today` 和 `/almanac/{date}` 返回黄历数据
- [ ] `?format=tts` 参数返回精简文本
- [ ] `POST /api/v1/auth/sms/send` 和 `/sms/login` 工作正常
- [ ] JWT 签发和验证工作正常
- [ ] Docker Compose 可一键启动 PG + Redis + API
- [ ] 所有测试通过（`pytest tests/ -v`）
- [ ] Engine Registry 模式可通过 `@register` 扩展新引擎
