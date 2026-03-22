# DS-Oracle 统一 API 接口设计规格

> 日期：2026-03-22
> 状态：已批准

## 1. 概述

### 1.1 目标

将 DS-Oracle CLI 的所有玄学功能（紫微斗数、八字、梅花易数、六爻、西洋占星、奇门遁甲、大六壬、黄历择日、姓名学等）封装为统一的 RESTful API + WebSocket 服务，供智能硬件、微信小程序、App 及第三方开发者调用，实现多端玄学智能问答。

### 1.2 设计决策摘要

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 消费者 | 智能硬件 + 小程序 + App + 第三方 | 全场景覆盖 |
| 部署 | 云服务器（兼容 Serverless） | 会话持久化需外部存储，两者均满足 |
| LLM 策略 | 单一默认，架构预留切换/路由 | 初期 Kimi，后续可扩展 |
| 认证 | 微信登录 + 手机号 + API Key | 多端适配 |
| 框架 | FastAPI + WebSocket | Python 生态无缝衔接，支持流式输出 |
| 调用模式 | 排盘同步 + AI 流式异步 | 排盘毫秒级秒回，AI 解读流式推送 |
| 数据库 | PostgreSQL + Redis | PG 持久化 + JSONB，Redis 缓存 + 限流 |
| 项目结构 | 单体分层，预留微服务拆分 | 初期简单，按边界可拆 |

---

## 2. 项目结构

```
ds-oracle-api/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI 入口，挂载路由 + 中间件
│   ├── config.py                # 统一配置（.env + DB/Redis/JWT）
│   │
│   ├── api/                     # 路由层
│   │   ├── __init__.py
│   │   ├── deps.py              # 公共依赖（get_db, get_current_user, rate_limiter）
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py        # v1 总路由
│   │   │   ├── auth.py          # 登录注册（微信/手机号）
│   │   │   ├── chart.py         # 排盘接口
│   │   │   ├── reading.py       # AI 解读接口
│   │   │   ├── chat.py          # 多轮对话 WebSocket
│   │   │   ├── almanac.py       # 黄历/择日
│   │   │   ├── name.py          # 姓名学
│   │   │   └── user.py          # 用户信息、历史记录
│   │   └── v2/                  # 未来版本预留
│   │
│   ├── engine/                  # 纯计算层（零 IO 依赖）
│   │   ├── __init__.py
│   │   ├── registry.py          # 引擎注册表（统一调度）
│   │   ├── ziwei.py             # ← 现有迁入
│   │   ├── meihua.py            # ← 现有迁入
│   │   ├── liuyao.py            # ← 现有迁入
│   │   ├── astrology.py         # ← 现有迁入
│   │   ├── bazi.py              # 新增
│   │   ├── qimen.py             # 新增
│   │   ├── liuren.py            # 新增
│   │   ├── iching.py            # 新增
│   │   ├── almanac.py           # 新增
│   │   └── name_analysis.py     # 新增
│   │
│   ├── llm/                     # AI 解读层
│   │   ├── __init__.py
│   │   ├── base.py              # LLMProvider 抽象基类（chat + chat_stream）
│   │   ├── kimi.py              # ← 现有 kimi_client.py 重构
│   │   ├── openai_provider.py   # OpenAI 兼容接口
│   │   ├── anthropic_provider.py
│   │   ├── router.py            # LLM 路由（按配置/请求选 provider）
│   │   ├── orchestrator.py      # 解读编排器（多系统并行流式）
│   │   └── prompts.py           # ← 现有 prompts.py 迁入
│   │
│   ├── auth/                    # 认证层
│   │   ├── __init__.py
│   │   ├── jwt.py               # JWT 签发/验证
│   │   ├── wechat.py            # 微信 code2session
│   │   └── sms.py               # 手机号验证码
│   │
│   ├── store/                   # 数据层
│   │   ├── __init__.py
│   │   ├── database.py          # SQLAlchemy async engine + session
│   │   ├── redis.py             # Redis 连接池
│   │   ├── models/              # ORM 模型
│   │   │   ├── user.py
│   │   │   ├── session.py
│   │   │   ├── chart.py
│   │   │   └── reading.py
│   │   └── crud/                # 数据操作
│   │       ├── user.py
│   │       ├── session.py
│   │       └── chart.py
│   │
│   └── common/                  # 公共工具
│       ├── __init__.py
│       ├── exceptions.py        # 统一异常
│       ├── response.py          # 统一响应格式
│       └── utils.py             # 时辰解析、文件名处理等
│
├── cli.py                       # 保留 CLI，改为调用 app/engine/ 和 app/llm/
├── alembic/                     # 数据库迁移
├── tests/
├── .env.example
├── requirements.txt
└── docker-compose.yml
```

### 关键设计决策

- **engine/registry.py**：所有引擎通过 `@register("system_name")` 装饰器自注册，新增术数系统只需写引擎文件 + 加装饰器
- **CLI 保留**：改为调用 `app/engine/` 和 `app/llm/`，CLI 和 API 共享计算逻辑
- **API 版本化**：`v1/` 路径前缀，老客户端不受新版本影响

---

## 3. API 接口规范

### 3.1 统一响应格式

```json
// 成功
{ "code": 0, "message": "success", "data": { ... }, "timestamp": 1711100000 }

// 错误
{ "code": 40001, "message": "无效的生辰参数", "data": null, "timestamp": 1711100000 }
```

**错误码分段**：

| 范围 | 类别 | 示例 |
|------|------|------|
| 40000-40999 | 参数校验 | 40001 无效生辰、40002 不支持的术数系统 |
| 41000-41999 | 认证授权 | 41001 Token 过期、41002 无权限 |
| 42000-42999 | 限流 | 42001 请求频率超限 |
| 43000-43999 | 业务逻辑 | 43001 排盘记录不存在 |
| 50000-50999 | 服务端错误 | 50001 LLM 调用失败、50002 数据库异常 |

**输入安全**：所有用户输入字段（`name`, `question`, `content`）在进入 LLM prompt 前经过清洗（防 prompt injection），在存储/文件名使用前经过转义。

### 3.2 认证接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/wechat` | 微信登录（code → token） |
| POST | `/api/v1/auth/sms/send` | 发送验证码 |
| POST | `/api/v1/auth/sms/login` | 手机号验证码登录 |
| POST | `/api/v1/auth/refresh` | 刷新 JWT |
| POST | `/api/v1/auth/logout` | 登出（撤销当前设备 Refresh Token） |

#### API Key 管理（第三方开发者）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/developer/keys` | 创建 API Key（返回一次明文） |
| GET | `/api/v1/developer/keys` | 列出所有 Key（脱敏） |
| DELETE | `/api/v1/developer/keys/{key_id}` | 撤销 Key |
| PUT | `/api/v1/developer/keys/{key_id}` | 更新 Key 名称/权限/限流 |

### 3.3 排盘接口（同步，毫秒级）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/chart/ziwei` | 紫微排盘 |
| POST | `/api/v1/chart/bazi` | 八字排盘 |
| POST | `/api/v1/chart/meihua` | 梅花起卦 |
| POST | `/api/v1/chart/liuyao` | 六爻排卦 |
| POST | `/api/v1/chart/astrology` | 西洋星盘 |
| POST | `/api/v1/chart/qimen` | 奇门遁甲 |
| POST | `/api/v1/chart/liuren` | 大六壬 |

统一请求体：

```json
{
  "name": "张三",
  "birth_date": "1990-05-15",
  "birth_time": "寅",
  "gender": "男",
  "question": "事业发展",
  "extra": {}
}
```

统一响应：

```json
{
  "code": 0,
  "data": {
    "chart_id": "ch_abc123",
    "system": "ziwei",
    "raw_data": { },
    "text_summary": "命宫在子，紫微天府同宫...",
    "image_url": "/files/charts/ch_abc123.png"
  }
}
```

### 3.4 AI 解读接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/reading/interpret` | 单次解读（chart_id + question） |
| POST | `/api/v1/reading/marriage` | 姻缘三合一分析 |
| GET | `/api/v1/reading/{reading_id}` | 查询已完成解读 |

请求体：

```json
{
  "chart_id": "ch_abc123",
  "systems": ["ziwei", "bazi"],
  "question": "今年事业如何",
  "stream": true
}
```

- `stream: false` → 同步等待完整结果
- `stream: true` → 返回 `reading_id`，通过 WebSocket 接收流式内容

**姻缘分析请求体**（`/reading/marriage`）：

```json
{
  "chart_id": "ch_abc123",
  "types": ["path", "challenge", "partner"],
  "stream": true
}
```

`types` 可选值：`path`（姻缘路径）、`challenge`（感情挑战）、`partner`（伴侣画像）。默认全部执行，三路并行。

**多端格式适配**：所有排盘和解读接口支持 `?format=tts` 查询参数，返回精简纯文本（无 Markdown 标记），适合智能硬件语音播报：

```json
{ "code": 0, "data": { "chart_id": "ch_abc123", "tts_text": "您的命宫在子宫..." } }
```

### 3.5 WebSocket 多轮对话

连接：`ws://host/api/v1/chat/{session_id}?token={jwt_access_token}`

**认证方式**：WebSocket 通过 URL query parameter 传递 JWT（浏览器和小程序环境不支持自定义 WebSocket header）。服务端在握手阶段验证 token，无效则拒绝连接（HTTP 401）。微信小程序需在 `wx.connectSocket` 的 URL 中附带 token。

客户端发送：

```json
{
  "type": "message",
  "content": "我明年适合换工作吗",
  "modes": ["ziwei", "bazi"],
  "liuyao_code": "221242"
}
```

服务端推送（逐条）：

```json
{"type": "chunk", "source": "main", "content": "从紫微来看..."}
{"type": "chunk", "source": "ziwei", "content": "命宫化忌..."}
{"type": "chunk", "source": "bazi", "content": "流年偏印..."}
{"type": "done", "reading_id": "rd_xyz789"}
```

控制指令：

```json
{"type": "mode", "action": "set", "modes": ["full"]}
{"type": "liuyao", "code": "221242"}
```

### 3.6 黄历 & 姓名接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/almanac/today` | 今日黄历 |
| GET | `/api/v1/almanac/{date}` | 指定日期黄历 |
| POST | `/api/v1/almanac/pick-date` | 择日 |
| POST | `/api/v1/name/analyze` | 姓名五格评分 |
| POST | `/api/v1/name/generate` | 起名推荐 |

### 3.7 用户 & 历史接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/user/profile` | 用户信息 |
| PUT | `/api/v1/user/profile` | 更新出生信息 |
| GET | `/api/v1/user/charts` | 排盘历史（分页） |
| GET | `/api/v1/user/readings` | 解读历史（分页） |
| GET | `/api/v1/user/sessions` | 对话历史（分页） |
| GET | `/api/v1/health` | 健康检查（DB + Redis 连通性） |

**分页规范**（所有列表接口统一）：

请求参数：`?cursor={last_id}&limit=20`（游标分页，默认 20 条）

响应：
```json
{
  "code": 0,
  "data": {
    "items": [...],
    "has_more": true,
    "next_cursor": "uuid_of_last_item"
  }
}
```

---

## 4. Engine 注册表

### 4.1 核心机制

```python
# engine/registry.py
class ChartRequest(BaseModel):
    system: str
    name: str
    birth_date: str           # YYYY-MM-DD
    birth_time: str           # 接受时辰名（"寅"）或序号字符串（"2"），内部统一转为 int 0-12
    gender: str               # "男" / "女"
    question: str = ""
    extra: dict = {}          # 系统特有参数（如 liuyao_code）

class ChartResult(BaseModel):
    chart_id: str
    system: str
    raw_data: dict
    text_summary: str
    image_path: str | None

ENGINES: dict[str, Callable[[ChartRequest], ChartResult]] = {}

def register(system: str):
    def wrapper(func):
        ENGINES[system] = func
        return func
    return wrapper

async def calculate(request: ChartRequest) -> ChartResult:
    """统一入口：同步引擎通过 asyncio.to_thread 包装，async 引擎直接 await"""
    engine = ENGINES.get(request.system)
    if not engine:
        raise UnsupportedSystemError(request.system)
    if asyncio.iscoroutinefunction(engine):
        return await engine(request)
    return await asyncio.to_thread(engine, request)
```

### 4.2 引擎自注册

```python
# engine/ziwei.py
@register("ziwei")
def calculate_ziwei(req: ChartRequest) -> ChartResult:
    data = get_astrolabe_data(req.birth_date, req.birth_time_index, req.gender)
    text = build_text_description(data)
    image = render_chart_image(data)
    return ChartResult(system="ziwei", raw_data=data, text_summary=text, image_path=image)
```

新增术数系统只需：写引擎文件 + 加 `@register` 装饰器，无需改路由层。

---

## 5. LLM 抽象层

### 5.1 Provider 基类

```python
class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: list[dict], model: str | None = None) -> str:
        """单轮，返回完整文本"""

    @abstractmethod
    async def chat_stream(self, messages: list[dict], model: str | None = None) -> AsyncIterator[str]:
        """流式，逐 chunk yield"""
```

### 5.2 LLM 路由

```python
def get_provider(name: str | None = None) -> LLMProvider:
    provider_name = name or config.LLM_PROVIDER
    return PROVIDERS[provider_name]
```

优先级：请求指定 → 配置默认 → 未来可按术数系统路由。

### 5.3 解读编排器

```python
async def interpret_stream(chart, question, systems, history, provider) -> AsyncIterator[ReadingChunk]:
    # 1. 主回答流式输出
    async for chunk in provider.chat_stream(main_prompt):
        yield ReadingChunk(source="main", content=chunk)
    # 2. 补充解读并行启动
    async for chunk in merge_streams(system_tasks):
        yield chunk
```

主回答先输出，补充解读并行跟随。CLI 和 API 共享此编排器。

---

## 6. 数据库模型

### 6.1 PostgreSQL

**users 表**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | |
| phone | VARCHAR(20) UNIQUE NULL | 手机号 |
| wechat_openid | VARCHAR(64) UNIQUE NULL | 微信小程序 |
| wechat_unionid | VARCHAR(64) NULL | 多端打通 |
| nickname | VARCHAR(50) | |
| avatar_url | VARCHAR(500) | |
| birth_date | DATE NULL | 绑定后复用 |
| birth_time | SMALLINT NULL | 时辰序号 0-12 |
| gender | VARCHAR(4) NULL | |
| birth_city | VARCHAR(50) NULL | 出生地 |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

**charts 表**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | |
| user_id | UUID FK → users | |
| system | VARCHAR(20) | ziwei/bazi/meihua... |
| params | JSONB | 输入参数快照 |
| result | JSONB | 排盘结构化结果 |
| text_summary | TEXT | 文本描述 |
| image_path | VARCHAR(500) | |
| created_at | TIMESTAMPTZ | |

**sessions 表**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | |
| user_id | UUID FK → users | |
| title | VARCHAR(200) | |
| birth_context | JSONB | 会话绑定的生辰 |
| active_modes | TEXT[] | {"ziwei","bazi","meihua"} |
| liuyao_code | VARCHAR(10) | |
| chart_ids | UUID[] | 关联排盘 |
| status | VARCHAR(10) | active/archived |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

**messages 表**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | |
| session_id | UUID FK → sessions | |
| role | VARCHAR(10) | user/assistant/system |
| source | VARCHAR(20) | main/ziwei/bazi... |
| content | TEXT | |
| tokens_used | INTEGER | |
| llm_provider | VARCHAR(20) | |
| created_at | TIMESTAMPTZ | |

**readings 表**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | |
| user_id | UUID FK → users | |
| chart_id | UUID FK → charts | |
| reading_type | VARCHAR(20) | interpret/marriage_* |
| question | TEXT | |
| systems | VARCHAR(100) | |
| content | TEXT | 解读全文 |
| llm_provider | VARCHAR(20) | |
| tokens_used | INTEGER | |
| created_at | TIMESTAMPTZ | |

**api_keys 表**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | |
| user_id | UUID FK → users | |
| key_hash | VARCHAR(64) | SHA256，不存明文 |
| name | VARCHAR(50) | |
| permissions | VARCHAR(200) | "chart,reading,almanac" |
| rate_limit | INTEGER | 次/分钟 |
| status | VARCHAR(10) | active/revoked |
| last_used_at | TIMESTAMPTZ | |
| created_at | TIMESTAMPTZ | |

### 6.2 Redis 用途

| Key 模式 | 类型 | TTL | 用途 |
|----------|------|-----|------|
| `session:{id}:ctx` | String JSON | 2h | 对话上下文缓存 |
| `user:{id}:token:{device_id}` | String | 7d | Refresh Token（多设备并存） |
| `rate:{user_id}:{endpoint}` | Counter | 1min | API 限流 |
| `sms:{phone}:code` | String | 5min | 验证码 |
| `almanac:{date}` | String JSON | 24h | 黄历缓存 |
| `chart:{id}` | String JSON | 1h | 热排盘缓存 |

---

## 7. 认证与安全

### 7.1 三通道认证

- **微信小程序**：`wx.login()` → `POST /auth/wechat` → JWT
- **App / 智能硬件**：手机号 + 验证码 → `POST /auth/sms/login` → JWT
- **第三方开发者**：`X-API-Key` header → 查 api_keys 表 → 内部转 JWT

### 7.2 JWT 结构

```json
{
  "sub": "user_uuid",
  "platform": "wechat|app|api",
  "device_id": "hw_abc123",
  "exp": 1711200000,
  "iat": 1711100000
}
```

- Access Token：2 小时
- Refresh Token：7 天，存 Redis

### 7.3 限流策略

| 身份 | 排盘 | AI 解读 | WebSocket | 黄历 |
|------|------|---------|-----------|------|
| 匿名 | 5次/天 | 不可用 | 不可用 | 10次/天 |
| 普通用户 | 30次/天 | 10次/天 | 5会话/天 | 无限 |
| API Key 基础 | 60次/分 | 20次/分 | 10并发 | 无限 |
| API Key 高级 | 300次/分 | 100次/分 | 50并发 | 无限 |

### 7.4 中间件管线

```
请求 → CORS → RateLimit → Auth → RequestLog → 路由 → ResponseFormat
```

---

## 8. 多端适配

| 端 | 适配要点 |
|---|---------|
| 微信小程序 | `code2session` 换 openid；图片返回 URL；WebSocket 走 `wss://` |
| App | 手机号登录；支持推送通知；大图走 CDN |
| 智能硬件 | 长期 Token（30天 refresh）；`?format=tts` 返回纯文本供语音播报 |
| 第三方 | API Key 鉴权；OpenAPI 文档；Webhook 回调 |

---

## 9. 部署

### 9.1 Docker Compose

```yaml
services:
  api:
    build: .
    ports: ["8000:8000"]
    command: uvicorn app.main:app --host 0.0.0.0 --workers 4
    depends_on: [postgres, redis]
  postgres:
    image: postgres:16-alpine
    volumes: ["pg_data:/var/lib/postgresql/data"]
  redis:
    image: redis:7-alpine
  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
```

### 9.2 拓扑

```
Nginx (SSL + 反代) → Uvicorn Workers × 4 → PostgreSQL + Redis
```

### 9.3 监控

| 组件 | 方案 |
|------|------|
| 日志 | structlog → JSON |
| 追踪 | X-Request-ID 全链路 |
| 监控 | Prometheus + Grafana |
| LLM 用量 | tokens_used 按用户/系统统计 |
| 告警 | Grafana / 钉钉 Webhook |

---

## 10. 依赖汇总

```txt
# Web
fastapi>=0.110, uvicorn[standard]>=0.27, websockets>=12.0

# DB
sqlalchemy[asyncio]>=2.0, asyncpg>=0.29, alembic>=1.13, redis[hiredis]>=5.0

# Auth
pyjwt>=2.8, passlib>=1.7, httpx>=0.27

# 现有
py-iztro>=0.1.5, kerykeion>=5.7.0, najia, openai>=1.0, Pillow>=10.0, python-dotenv>=1.0

# 新引擎（按 ROADMAP.md Phase 逐步加入）
lunar_python>=1.7, kinqimen, kinliuren, ichingshifa, kintaiyi
```

---

## 11. 迁移注意事项

- **liuyao.py 硬编码路径**：现有 `Path(r"D:\BaiduSyncdisk\aicoding\najia")` 回退路径需移除，改为纯 pip 依赖
- **image_path vs image_url**：数据库存 `image_path`（相对路径），API 返回 `image_url`（完整 URL），转换在路由层完成
- **LLM Provider 迁移**：Phase 1 实现 Kimi + OpenAI；Grok/Perplexity/Gemini 按需在后续 Phase 补充
- **CORS 配置**：通过环境变量 `CORS_ORIGINS` 配置允许的域名列表，默认允许小程序域名

---

## 12. 实施路线

与 ROADMAP.md 对齐，分 4 个 Phase：

1. **Phase 1**：搭建 API 框架 + 迁移现有 4 引擎 + 认证 + PG/Redis + 八字/黄历
2. **Phase 2**：奇门/六壬/周易引擎 + LLM 多 Provider + WebSocket 对话
3. **Phase 3**：姓名学 + 面相 AI + 第三方 API Key 体系
4. **Phase 4**：太乙/风水 + 多端推送 + 监控告警 + 性能优化
