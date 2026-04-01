# DS-Oracle

中华术数综合平台 — FastAPI 后端 + CLI 客户端，集成 13 个命理/卜筮/相术引擎。

## 功能总览

### 命理引擎（13 个）

| 引擎 | 系统名 | 说明 | 依赖 |
|------|--------|------|------|
| 紫微斗数 | `ziwei` | 排盘、十二宫、星曜亮度、四化、运限推算 | app/pureziwei（本地） |
| 八字命理 | `bazi` | 四柱、十神、纳音、藏干、地势、命宫/身宫、旬空、大运 | app/lunar（本地） |
| 黄历择日 | `almanac` | 宜忌、吉凶神煞、天神值日、星宿、九星、时辰宜忌 | app/lunar（本地） |
| 梅花易数 | `meihua` | 时间起卦、互卦/变卦、体用关系、五行生克 | 无 |
| 六爻占卜 | `liuyao` | 纳甲装卦、世应/六神/六亲 | app/najia（本地） |
| 西洋占星 | `astrology` | 本命盘、行星宫位、SVG 星盘图 | kerykeion |
| 奇门遁甲 | `qimen` | 时家/日家排盘、天地盘、八门九星八神 | kinqimen |
| 大六壬 | `liuren` | 四课三传、天地盘、格局分类 | kinliuren |
| 周易筮法 | `iching` | 大衍筮法起卦、六十四卦辞查询、本卦/之卦解析 | ichingshifa |
| 灵签抽签 | `qianwen` | 观音灵签(98签)、黄大仙灵签(100签)、诸葛神算(384签) | 纯数据 |
| 周公解梦 | `jiemeng` | 33,808 条解梦条目、关键词搜索匹配 | 纯数据 |
| 姓名五格 | `name_analysis` | 康熙字典笔画(7,074字)、天/人/地/外/总格、81 数理、三才配置 | 纯数据 |
| 八字合婚 | `hehun` | 日干天合/相生相克、日支六合六冲、纳音配对、评分(0-100) | app/lunar（本地） |

### 本地化包

| 包 | 来源 | 替代的外部依赖 |
|----|------|----------------|
| `app/pureziwei/` | 自研纯 Python 紫微引擎 | py-iztro + pythonmonkey |
| `app/lunar/` | 6tail/lunar-python (MIT) | lunar_python |
| `app/najia/` | bopo/najia (MIT) | najia + arrow + jinja2 |

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/health` | 健康检查 |
| POST | `/api/v1/chart/{system}` | 通用排盘（system = 上述 13 个引擎名） |
| GET | `/api/v1/almanac/today` | 今日黄历 |
| GET | `/api/v1/almanac/{date}` | 指定日期黄历 |
| POST | `/api/v1/auth/sms/send` | 发送短信验证码 |
| POST | `/api/v1/auth/sms/login` | 短信验证码登录 |

### CLI 模式

运行 `python cli.py` 进入交互式菜单，支持：

1. 紫微排盘 + PNG 宫格图
2. 梅花易数起卦
3. 六爻占卜
4. 西洋占星
5. 八字排盘
6. 黄历查询
7. Kimi AI 多轮解读咨询

所有结果保存到 `output/` 目录（Markdown + PNG）。

## 快速开始

### 环境要求

- Python 3.10+
- Windows / macOS / Linux

### 安装

```bash
git clone https://github.com/gaoxingkele/ziwei-oracle.git
cd ziwei-oracle
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，填入 API Key 等配置
```

### 启动 API 服务

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 启动 CLI

```bash
python cli.py
```

### Docker

```bash
docker compose up -d
# API 默认监听 http://localhost:8000
```

### 调用示例

```bash
# 八字排盘
curl -X POST http://localhost:8000/api/v1/chart/bazi \
  -H "Content-Type: application/json" \
  -d '{"name":"张三","birth_date":"1990-05-15","birth_time":"寅","gender":"男"}'

# 紫微斗数
curl -X POST http://localhost:8000/api/v1/chart/ziwei \
  -H "Content-Type: application/json" \
  -d '{"name":"李四","birth_date":"2000-08-16","birth_time":"2","gender":"女"}'

# 抽签（观音灵签）
curl -X POST http://localhost:8000/api/v1/chart/qianwen \
  -H "Content-Type: application/json" \
  -d '{"name":"测试","birth_date":"2024-01-01","birth_time":"0","gender":"男","extra":{"type":"guanyin"}}'

# 解梦
curl -X POST http://localhost:8000/api/v1/chart/jiemeng \
  -H "Content-Type: application/json" \
  -d '{"name":"测试","birth_date":"2024-01-01","birth_time":"0","gender":"男","question":"梦见蛇"}'

# 姓名分析
curl -X POST http://localhost:8000/api/v1/chart/name_analysis \
  -H "Content-Type: application/json" \
  -d '{"name":"王伟","birth_date":"1990-01-01","birth_time":"0","gender":"男"}'

# 八字合婚
curl -X POST http://localhost:8000/api/v1/chart/hehun \
  -H "Content-Type: application/json" \
  -d '{"name":"张三","birth_date":"1990-05-15","birth_time":"寅","gender":"男","extra":{"spouse_birth_date":"1992-08-20","spouse_birth_time":"午","spouse_gender":"女"}}'

# 今日黄历
curl http://localhost:8000/api/v1/almanac/today
```

## 配置（.env）

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_PROVIDER` | LLM 提供商 | kimi |
| `KIMI_API_KEY` | Kimi API Key | -- |
| `DATABASE_URL` | PostgreSQL 连接串 | postgresql+asyncpg://... |
| `REDIS_URL` | Redis 连接串 | redis://localhost:6379/0 |
| `JWT_SECRET` | JWT 签名密钥 | -- |
| `CORS_ORIGINS` | CORS 允许的域名 | * |
| `ASTRO_CITY` | 占星默认城市 | Shanghai |
| `OUTPUT_DIR` | 文件输出目录 | output |

完整变量列表见 `.env.example`。

## 项目结构

```
ds-oracle-cli/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── config.py             # 环境配置
│   ├── api/v1/               # API 路由
│   │   ├── chart.py          #   POST /chart/{system}
│   │   ├── almanac.py        #   GET /almanac/today|{date}
│   │   └── auth.py           #   SMS 登录
│   ├── engine/               # 命理引擎（13 个）
│   │   ├── registry.py       #   引擎注册器 + ChartRequest/ChartResult
│   │   ├── ziwei.py          #   紫微斗数
│   │   ├── bazi.py           #   八字命理
│   │   ├── almanac.py        #   黄历择日
│   │   ├── meihua.py         #   梅花易数
│   │   ├── liuyao.py         #   六爻占卜
│   │   ├── astrology.py      #   西洋占星
│   │   ├── qimen.py          #   奇门遁甲
│   │   ├── liuren.py         #   大六壬
│   │   ├── iching.py         #   周易筮法
│   │   ├── qianwen.py        #   灵签抽签
│   │   ├── jiemeng.py        #   周公解梦
│   │   ├── name_analysis.py  #   姓名五格
│   │   └── hehun.py          #   八字合婚
│   ├── pureziwei/            # 紫微斗数纯 Python 引擎
│   ├── lunar/                # 农历/八字/黄历计算库
│   ├── najia/                # 六爻纳甲装卦库
│   ├── data/                 # 静态数据
│   │   ├── qianwen/          #   灵签数据 (JSON)
│   │   ├── jiemeng/          #   解梦数据 (JSON)
│   │   └── namedict/         #   笔画/三才数据
│   ├── auth/                 # JWT + SMS 认证
│   ├── common/               # 异常、响应、工具函数
│   └── llm/                  # LLM 客户端（预留）
├── cli.py                    # CLI 交互入口
├── config.py                 # CLI 配置
├── prompts.py                # LLM 提示词模板
├── tests/                    # 测试（53 个）
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── ROADMAP.md                # 功能路线图
```

## 测试

```bash
pip install pytest pytest-asyncio
python -m pytest tests/ -v
# 53 passed
```

## 技术栈

- **后端**: FastAPI + Pydantic + SQLAlchemy (async)
- **认证**: JWT + SMS
- **引擎模式**: 装饰器注册 `@register("system_name")`，统一 `ChartRequest` -> `ChartResult`
- **LLM**: 预留 Kimi / OpenAI / Claude / Gemini 多厂商接口
- **部署**: Docker Compose (API + PostgreSQL + Redis)

## 许可证

MIT
