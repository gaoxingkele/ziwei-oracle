# DS-Oracle

中华术数综合平台 — FastAPI 后端 + MCP Server + CLI 客户端，集成 14 个命理/卜筮/相术引擎。

## 功能总览

### 命理引擎（14 个）

| 引擎 | 系统名 | 说明 | 依赖 |
|------|--------|------|------|
| 紫微斗数 | `ziwei` | 排盘、十二宫、星曜亮度、四化、运限推算 | app/pureziwei（本地） |
| 八字命理 | `bazi` | 四柱、十神、纳音、藏干、地势、命宫/身宫、旬空、大运 | app/lunar（本地） |
| 黄历择日 | `almanac` | 宜忌、吉凶神煞、天神值日、星宿、九星、时辰宜忌 | app/lunar（本地） |
| 黄道吉日 | `jiri` | 按事项+日期范围检索吉日，支持口语别名(结婚→嫁娶等) | app/lunar（本地） |
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

## 三种访问方式

### 1. REST API（小程序 / H5 / 后端调用）

Token 认证，免登录。适合微信小程序、H5 页面、后端服务集成。

### 2. MCP Server（大模型工具调用）

通过 MCP 协议暴露 14 个 Tools，大模型（Claude Desktop / 小龙虾等客户端）可直接调用精准计算。

### 3. CLI 命令行（本地使用）

交互式菜单，18 个功能项，每个引擎计算后可选调用大模型解读。

---

## REST API

### 认证

所有 API 接口均需 Token 认证（`/api/v1/health` 除外），支持两种方式：

```
# 方式一：Header
Authorization: Bearer <your-token>

# 方式二：Query 参数
?token=<your-token>
```

Token 在 `.env` 中配置 `API_TOKENS`（多个逗号分隔），留空则跳过校验（开发模式）。

### 接口列表

#### 系统接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/health` | 健康检查（无需Token） |
| GET | `/api/v1/chart/systems` | 获取所有引擎列表 |

#### 通用排盘接口

```
POST /api/v1/chart/{system}
```

`{system}` 为引擎名（如 `ziwei`、`bazi`、`jiri` 等 14 个），Body 示例：

```json
{
  "name": "张三",
  "birth_date": "1990-05-15",
  "birth_time": "14:00",
  "gender": "男",
  "question": "",
  "extra": {}
}
```

#### 便捷接口（参数语义化，推荐使用）

| 方法 | 路径 | 说明 | 主要参数 |
|------|------|------|----------|
| POST | `/api/v1/chart/ziwei/calc` | 紫微斗数 | name, birth_date, birth_time, gender |
| POST | `/api/v1/chart/bazi/calc` | 八字排盘 | name, birth_date, birth_time, gender |
| POST | `/api/v1/chart/astrology/calc` | 西方星盘 | name, birth_date, birth_time, gender |
| POST | `/api/v1/chart/meihua/calc` | 梅花易数 | question, birth_date?, birth_time? |
| POST | `/api/v1/chart/liuyao/calc` | 六爻排盘 | yao_codes(6个1~4), question? |
| POST | `/api/v1/chart/qimen/calc` | 奇门遁甲 | question?, birth_date?, birth_time? |
| POST | `/api/v1/chart/liuren/calc` | 大六壬 | question?, birth_date?, birth_time?, guiren?(1/2) |
| POST | `/api/v1/chart/iching/calc` | 周易筮法 | question, birth_date?, birth_time? |
| POST | `/api/v1/chart/qianwen/calc` | 求签 | sign_type?(guanyin/huangdaxian/zhuge), question? |
| POST | `/api/v1/chart/jiemeng/calc` | 周公解梦 | keyword |
| POST | `/api/v1/chart/name/calc` | 姓名五格 | name |
| POST | `/api/v1/chart/hehun/calc` | 八字合婚 | name_a, birth_date_a, birth_time_a, gender_a, name_b, birth_date_b, birth_time_b, gender_b |
| POST | `/api/v1/chart/almanac/calc` | 黄历查询 | date? |
| POST | `/api/v1/chart/jiri/calc` | 黄道吉日 | activity, start_date?, end_date? |
| GET | `/api/v1/almanac/today` | 今日黄历 | - |
| GET | `/api/v1/almanac/{date}` | 指定日期黄历 | - |

参数带 `?` 表示可选，留空自动取当天/当前时间。

`birth_time` 支持多种格式：`14:00`、`下午2点`、`午`、`6`（时辰序号）。

#### 响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "chart_id": "ch_xxxx",
    "system": "bazi",
    "raw_data": { ... },
    "text_summary": "══════════ 八字排盘 ══════════\n..."
  },
  "timestamp": 1700000000
}
```

错误响应：`code` 非 0，`message` 含错误描述。

### 调用示例

```bash
TOKEN="your-token"

# 八字排盘
curl -X POST http://localhost:8000/api/v1/chart/bazi/calc \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"张三","birth_date":"1990-05-15","birth_time":"14:00","gender":"男"}'

# 黄道吉日查询
curl -X POST http://localhost:8000/api/v1/chart/jiri/calc \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"activity":"结婚","start_date":"2026-05-01","end_date":"2026-06-01"}'

# 求签
curl -X POST http://localhost:8000/api/v1/chart/qianwen/calc \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sign_type":"guanyin","question":"事业发展"}'

# 八字合婚
curl -X POST http://localhost:8000/api/v1/chart/hehun/calc \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name_a":"张三","birth_date_a":"1990-05-15","birth_time_a":"14:00","gender_a":"男","name_b":"李四","birth_date_b":"1992-08-20","birth_time_b":"9:00","gender_b":"女"}'

# 今日黄历（Query Token）
curl "http://localhost:8000/api/v1/almanac/today?token=$TOKEN"
```

Swagger 文档：`http://localhost:8000/docs`

---

## MCP Server

将 14 个引擎作为 MCP Tools 暴露，大模型可直接调用获取精准计算结果。

### 启动

```bash
# 默认 streamable-http，0.0.0.0:8811
python mcp_server.py

# 自定义端口
python mcp_server.py --port 9000

# SSE 模式
python mcp_server.py --transport sse

# stdio 模式（本地调试）
python mcp_server.py --transport stdio
```

### 客户端配置

Claude Desktop / 小龙虾等 MCP 客户端：

```json
{
  "mcpServers": {
    "ds-oracle": {
      "url": "http://your-server:8811/mcp"
    }
  }
}
```

stdio 模式（本地）：

```json
{
  "mcpServers": {
    "ds-oracle": {
      "command": "python",
      "args": ["mcp_server.py", "--transport", "stdio"]
    }
  }
}
```

### 可用 Tools

| Tool | 说明 | 必填参数 |
|------|------|----------|
| `ziwei` | 紫微斗数排盘 | name, birth_date, birth_time, gender |
| `bazi` | 八字排盘 | name, birth_date, birth_time, gender |
| `astrology` | 西方星盘 | name, birth_date, birth_time, gender |
| `meihua` | 梅花易数 | question |
| `liuyao` | 六爻排盘 | yao_codes |
| `qimen` | 奇门遁甲 | - |
| `liuren` | 大六壬 | - |
| `iching` | 周易筮法 | question |
| `qianwen` | 求签 | - |
| `jiemeng` | 周公解梦 | keyword |
| `name_analysis` | 姓名五格 | name |
| `hehun` | 八字合婚 | 甲乙双方出生信息 |
| `almanac` | 黄历查询 | - |
| `jiri` | 黄道吉日 | activity |

### 部署到服务器

```bash
# 1. 拉代码
git clone https://github.com/gaoxingkele/ziwei-oracle.git && cd ziwei-oracle

# 2. 安装依赖
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. 配置 .env

# 4. systemd 守护进程
sudo tee /etc/systemd/system/ds-oracle-mcp.service << 'EOF'
[Unit]
Description=DS-Oracle MCP Server
After=network.target
[Service]
Type=simple
WorkingDirectory=/path/to/ziwei-oracle
ExecStart=/path/to/ziwei-oracle/venv/bin/python mcp_server.py --port 8811
Restart=always
Environment=PYTHONIOENCODING=utf-8
[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable --now ds-oracle-mcp
```

---

## CLI 命令行

```bash
python cli.py
```

18 个功能菜单：

| # | 功能 | 说明 |
|---|------|------|
| 1 | 紫微排盘 | 文本 + PNG 图 |
| 2 | 梅花易数起卦 | 时间起卦 |
| 3 | 紫微长线解读 | 排盘 + Kimi AI 解读 |
| 4 | 梅花易数解读 | 起卦 + Kimi AI 解读 |
| 5 | 姻缘分析 | 婚姻道路/困难挑战/伴侣性格 |
| 6 | 智能体多轮咨询 | Kimi 多轮对话 |
| 7 | 六爻排盘 | 纳甲装卦 |
| 8 | 六爻解读 | 排盘 + Kimi AI 解读 |
| 9 | 八字排盘 | 四柱八字 |
| 10 | 黄历查询 | 当日宜忌 |
| 11 | 奇门遁甲 | 时家排盘 |
| 12 | 大六壬 | 四课三传 |
| 13 | 周易筮法 | 大衍起卦 |
| 14 | 求签 | 观音/黄大仙/诸葛 |
| 15 | 周公解梦 | 关键词搜索 |
| 16 | 姓名五格 | 笔画/数理分析 |
| 17 | 八字合婚 | 双人八字对比 |
| 18 | 黄道吉日 | 按事项检索吉日 |

所有引擎计算完成后可选调用大模型进行深度解读，结果保存到 `output/` 目录。

时间输入支持多种格式：`14:00`、`下午2点`、`午`、`6`。

---

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
# 编辑 .env，配置 API_TOKENS 和 LLM API Key
```

### 启动

```bash
# API 服务（小程序/H5）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# MCP 服务（大模型工具调用）
python mcp_server.py --port 8811

# CLI（本地交互）
python cli.py
```

### Docker

```bash
docker compose up -d
# API: http://localhost:8000
```

### 引擎测试

```bash
# 快速验证所有 14 个引擎
python test_all_engines.py
```

## 配置（.env）

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `API_TOKENS` | API 认证 Token（逗号分隔，留空跳过校验） | -- |
| `LLM_PROVIDER` | LLM 提供商 | kimi |
| `KIMI_API_KEY` | Kimi API Key | -- |
| `DATABASE_URL` | PostgreSQL 连接串 | postgresql+asyncpg://... |
| `REDIS_URL` | Redis 连接串 | redis://localhost:6379/0 |
| `JWT_SECRET` | JWT 签名密钥 | -- |
| `CORS_ORIGINS` | CORS 允许的域名 | * |
| `ASTRO_CITY` | 占星默认城市 | Beijing |
| `OUTPUT_DIR` | 文件输出目录 | output |

完整变量列表见 `.env.example`。

## 项目结构

```
ds-oracle-cli/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── config.py             # 环境配置
│   ├── api/v1/               # API 路由
│   │   ├── chart.py          #   排盘接口（通用 + 14个便捷接口）
│   │   ├── almanac.py        #   GET /almanac/today|{date}
│   │   └── auth.py           #   SMS 登录
│   ├── engine/               # 命理引擎（14 个）
│   │   ├── registry.py       #   引擎注册器 + ChartRequest/ChartResult
│   │   ├── ziwei.py ~ hehun.py
│   │   └── jiri.py           #   黄道吉日查询
│   ├── pureziwei/            # 紫微斗数纯 Python 引擎
│   ├── lunar/                # 农历/八字/黄历计算库
│   ├── najia/                # 六爻纳甲装卦库
│   ├── data/                 # 静态数据（签文/解梦/笔画）
│   ├── auth/                 # JWT + SMS 认证
│   └── common/               # 异常、响应、工具函数
├── mcp_server.py             # MCP Server（14 Tools）
├── cli.py                    # CLI 交互入口（18项菜单）
├── config.py                 # CLI 配置
├── prompts.py                # LLM 提示词模板
├── test_all_engines.py       # 引擎快速验证脚本
├── mcp_config_example.json   # MCP 客户端配置示例
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## 测试

```bash
pip install pytest pytest-asyncio
python -m pytest tests/ -v

# 快速验证所有引擎
python test_all_engines.py
# 14/14 passed
```

## 技术栈

- **后端**: FastAPI + Pydantic + SQLAlchemy (async)
- **MCP**: mcp SDK (streamable-http / SSE / stdio)
- **认证**: Token（免登录） + JWT + SMS
- **引擎模式**: 装饰器注册 `@register("system_name")`，统一 `ChartRequest` -> `ChartResult`
- **LLM**: Kimi / OpenAI / Claude / Gemini 多厂商接口
- **部署**: Docker Compose / systemd

## 语音/对话指令示例

接入大模型（小智语音助手、Claude、ChatGPT 等）后，用户无需说出工具名，大模型根据语义自动匹配调用。

### 命理排盘

| Tool | 语音/文字指令示例 |
|------|-----------------|
| `ziwei` | "帮我排个紫微命盘"、"看看我的紫微斗数"、"我1990年5月15日下午2点出生的，排个盘" |
| `bazi` | "算算我的八字"、"帮我排个四柱八字"、"看看我的命理" |
| `astrology` | "帮我看看星盘"、"我是什么星座上升"、"排一下我的西方星盘" |

### 占卜问事

| Tool | 语音/文字指令示例 |
|------|-----------------|
| `meihua` | "帮我起一卦"、"梅花易数测一下面试能不能过"、"占一卦看看最近运势" |
| `liuyao` | "帮我排个六爻"、"用六爻看看这件事"、"纳甲起卦问财运" |
| `iching` | "用周易帮我算一卦"、"帮我占个卦问问工作"、"起一卦看看前程" |
| `qimen` | "排个奇门遁甲"、"奇门看看今天时局"、"帮我起个奇门局" |
| `liuren` | "起个大六壬"、"六壬看看这件事"、"帮我排个六壬课" |

### 日常查询

| Tool | 语音/文字指令示例 |
|------|-----------------|
| `almanac` | "今天黄历怎么样"、"看看今天宜什么忌什么"、"今天适合出行吗" |
| `jiri` | "下个月哪天适合搬家"、"最近有什么好日子可以结婚"、"帮我选个开业的黄道吉日" |
| `qianwen` | "帮我抽个签"、"求一支观音灵签"、"抽个黄大仙签看看" |
| `jiemeng` | "昨晚梦到蛇了什么意思"、"梦见飞是怎么回事"、"解个梦，梦到水" |

### 姓名/合婚

| Tool | 语音/文字指令示例 |
|------|-----------------|
| `name_analysis` | "张伟这个名字好不好"、"帮我分析一下这个名字"、"给孩子起名叫王子轩，测一下" |
| `hehun` | "我和女朋友合不合适"、"帮我们算算合婚"、"看看我俩八字配不配" |

---

## 许可证

MIT
