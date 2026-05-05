# DS-Oracle

中华术数综合平台 — FastAPI 后端 + MCP Server + CLI 客户端，集成 15 个命理/卜筮/相术引擎，并通过 4 个时段类工具（v3）支撑批量运限/流月/吉时分析。共暴露 **24 个 MCP Tools**：15 命理 + 4 签文专用 + 4 时段/解析。

> **最新进展（v3，2026-04）**：新增 `calendar_resolve` 自然语言时间解析 + `ziwei_period` / `bazi_period` / `astrology_period` 三个时段批量工具，并在 MCP instructions 与 system-prompt 中加入路由规则——含时间词的命理提问统一走 *_period 工具，禁止 LLM 自行做农历换算/月柱推算/刑冲合害。修复了 `calendar_resolve("今年")` 在立春前误判 ganzhi_year 的 bug（区间中点法）。详见底部「修改日志」。

## 本地 / 云端双环境切换

服务端代码无需任何修改即可在本机调试或部署到云端，区别只在配置文件：

| 环境 | 加载文件 | 启动命令 | 设备端 base URL |
|------|----------|----------|------------------|
| **本机调试** | `.env.local`（存在则优先） | `python mcp_server.py --host 0.0.0.0 --port 8811` | `http://<本机内网IP>:8812` |
| **云端线上** | `.env`（无 `.env.local` 时回落） | 同上 | `http://117.50.48.22:8812` |

加载逻辑统一在三处入口（`mcp_server.py` / `config.py` / `app/config.py`）：
**存在 `.env.local` → 用它；否则 → 用 `.env`**。云端机器只要不放 `.env.local`，行为完全不变。

**本机起步**：
```bash
cp .env.local.example .env.local   # 按需填 KIMI_API_KEY 等
uvicorn app.main:app --host 0.0.0.0 --port 8812     # REST API（设备端 setting 调用）
python mcp_server.py --host 0.0.0.0 --port 8811     # MCP Server（LLM 调用）
```
设备端把 base URL 改到本机内网 IP（用 `ipconfig` / `ifconfig` 查），即可联调。
切回云端模式：删除或重命名 `.env.local` 即可。

## 功能总览

### 命理引擎（15 个）

| 引擎 | 系统名 | 说明 | 依赖 |
|------|--------|------|------|
| 紫微斗数 | `ziwei` | 排盘、十二宫、星曜亮度、四化、运限推算 | app/pureziwei（本地） |
| 八字命理 | `bazi` | 四柱、十神、纳音、藏干、地势、命宫/身宫、旬空、大运 | app/lunar（本地） |
| 黄历择日 | `almanac` | 宜忌、吉凶神煞、天神值日、星宿、九星、时辰宜忌 | app/lunar（本地） |
| 黄道吉日 | `jiri` | 按事项+日期范围检索吉日，支持口语别名(结婚→嫁娶等) | app/lunar（本地） |
| 梅花易数 | `meihua` | 时间起卦、互卦/变卦、体用关系、五行生克 | 无 |
| 六爻占卜 | `liuyao` | 纳甲装卦、世应/六神/六亲 | app/najia（本地） |
| 六爻自动起卦 | `liuyao_qigua` | 系统自动摇卦生成爻码，调用六爻引擎解读 | app/najia（本地） |
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

通过 MCP 协议暴露 24 个 Tools（15 命理 + 4 签文专用 + 4 时段/解析），大模型（Claude Desktop / 小龙虾 / 小智 ESP32 等客户端）可直接调用精准计算。

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
| POST | `/api/v1/chart/qianwen/calc` | 求签 | sign_type?(guanyin/huangdaxian/zhuge/mazu), question? |
| POST | `/api/v1/chart/jiemeng/calc` | 周公解梦 | keyword |
| POST | `/api/v1/chart/name/calc` | 姓名五格 | name |
| POST | `/api/v1/chart/hehun/calc` | 八字合婚 | name_a, birth_date_a, birth_time_a, gender_a, name_b, birth_date_b, birth_time_b, gender_b |
| POST | `/api/v1/chart/almanac/calc` | 黄历查询 | date? |
| POST | `/api/v1/chart/jiri/calc` | 黄道吉日 | activity, start_date?, end_date? |
| GET | `/api/v1/almanac/today` | 今日黄历 | - |
| GET | `/api/v1/almanac/{date}` | 指定日期黄历 | - |

#### 设备设置接口（直接存储，不调 LLM）

设备端把用户已规范化的值 POST 上来（滚轮/表单/映射），服务器做格式校验后写入 SQLite（按 `device_id` 键），并回传给设备端缓存。全部使用 `device_id` 作为用户主键。

| 方法 | 路径 | 说明 | 输入示例 → 存储 |
|------|------|------|----------------|
| POST | `/api/v1/setting/birthday` | 生日 | `"1995-03-03"` → `"1995-03-03"`（必须 YYYY-MM-DD） |
| POST | `/api/v1/setting/birthtime` | 出生时间（24h） | `"07:40"` / `"7:40"` → `"07:40"` |
| POST | `/api/v1/setting/city` | 出生地点 | 任意字符串 → 原样保存 |
| POST | `/api/v1/setting/name` | 姓名 | 任意字符串 → 原样保存，`lang` 透传 |
| POST | `/api/v1/setting/sex` | 性别 | `男`/`male`/`1` → `1`；`女`/`female`/`0` → `0` |
| GET | `/api/v1/setting?device_id=xxx` | 读取全部设置 | - |

请求体：`{"device_id": "dev_xxx", "text": "<已规范化的值>"}`（name 额外支持 `lang: "zh"` / `"en"`，默认 `zh`）。

设计要点：
- **直接存储**：不调 LLM，客户端负责规范化（滚轮 picker 保证生日/时间格式）
- **格式校验**：`birthday` 必须 `YYYY-MM-DD`，`birthtime` 必须 `HH:MM`（允许 `7:40` 补位），`sex` 用映射表；不匹配返回 `40001`
- **数据库**：默认 SQLite（`ds_oracle.db`，零配置），通过 `SETTINGS_DB_URL` 可切换到 PostgreSQL
- **审计日志**：`setting_update` 事件记录原始输入、落库值、错误原因，归到该 `device_id` 目录下

详细协议和集成示例见 `docs/setting-api.md`。

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
curl -X POST http://localhost:8812/api/v1/chart/bazi/calc \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"张三","birth_date":"1990-05-15","birth_time":"14:00","gender":"男"}'

# 黄道吉日查询
curl -X POST http://localhost:8812/api/v1/chart/jiri/calc \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"activity":"结婚","start_date":"2026-05-01","end_date":"2026-06-01"}'

# 求签
curl -X POST http://localhost:8812/api/v1/chart/qianwen/calc \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sign_type":"guanyin","question":"事业发展"}'

# 八字合婚
curl -X POST http://localhost:8812/api/v1/chart/hehun/calc \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name_a":"张三","birth_date_a":"1990-05-15","birth_time_a":"14:00","gender_a":"男","name_b":"李四","birth_date_b":"1992-08-20","birth_time_b":"9:00","gender_b":"女"}'

# 今日黄历（Query Token）
curl "http://localhost:8812/api/v1/almanac/today?token=$TOKEN"
```

Swagger 文档：`http://localhost:8812/docs`

---

## MCP Server

将 15 个引擎作为 MCP Tools 暴露，大模型可直接调用获取精准计算结果。

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
| `meihua` | 梅花易数（"算一卦"默认） | question, numbers?(3个数字) |
| `liuyao` | 六爻排盘 | yao_codes |
| `liuyao_qigua` | 六爻自动起卦 | question? |
| `qimen` | 奇门遁甲 | - |
| `liuren` | 大六壬 | - |
| `iching` | 周易筮法 | question |
| `qianwen` | 求签（通用入口，可切签种） | sign_type?(guanyin/huangdaxian/zhuge/mazu) |
| `qianwen_guanyin` | 观音灵签（100 签） | question? |
| `qianwen_huangdaxian` | 黄大仙灵签（100 签） | question? |
| `qianwen_zhuge` | 诸葛神算（384 签） | question? |
| `qianwen_mazu` | 妈祖六十甲子签（60 签） | question? |
| `jiemeng` | 周公解梦 | keyword |
| `name_analysis` | 姓名五格 | name |
| `hehun` | 八字合婚 | 甲乙双方出生信息 |
| `almanac` | 黄历查询 | - |
| `jiri` | 黄道吉日 | activity |
| `calendar_resolve` | 自然语言时间解析（"今年/下个月/2027 春节"→ 起止日 + 干支字段） | text |
| `ziwei_period` | 紫微运限批量分析（指定时段内多盘） | birth*, period |
| `bazi_period` | 八字流月批量 + 对命主关系 | birth*, period |
| `astrology_period` | 占星时段相位/容许度批量 | birth*, period |

> **路由约定**：含时间词的命理提问（"今年八字怎么样"、"下个月紫微运限"）必须先走 `calendar_resolve` 拿到精确起止日和干支，再调用 `*_period`；禁止 LLM 自行推算月柱/刑冲合害——这些算术由引擎权威给出。详见 `docs/mcp-system-prompt.md`。

### 运行时部署（与小智 ESP32 协同的 4 服务架构）

实测稳定运行的本机布署 4 件套（端口经过编排，**互不冲突**）：

| # | 服务 | 进程命令 | 监听 | 日志 |
|---|------|----------|------|------|
| 1 | DS-Oracle 设定服务器（FastAPI） | `uvicorn app.main:app --host 0.0.0.0 --port 8812` | `0.0.0.0:8812` | `logs_api.log` |
| 2 | DS-Oracle MCP Server | `python mcp_server.py --port 8811` | `0.0.0.0:8811` | `logs_mcp.log` |
| 3 | 小智 xiaozhi-server | `.venv/Scripts/python.exe app.py`（cwd `xiaozhi-esp32-server/main/xiaozhi-server/`） | `127.0.0.1:8765` ws + `127.0.0.1:8003` http | `logs_xz_server.log` / `logs_xz_err.log` |
| 4 | ngrok 隧道 | `ngrok.exe http 8811` | 公网 `https://uncover-earflap-unspoken.ngrok-free.dev` → 本机 `:8811` | `logs_ngrok.log` |

**启动注意事项**：

- **小智 xiaozhi-server 必须用 `.venv/Scripts/python.exe`，不能用系统 `python`**——系统 Python（如 3.14）跑 `app.py` 会因 `opuslib_next` 找不到 opus.dll 启动失败；`.venv` 内置 pyogg 已带 `opus.dll`/`opusenc.dll`/`opusfile.dll`。
- **端口规划**：DS-Oracle FastAPI 用 `8812`（避让 8000 给小智或其他常用服务）；xiaozhi-server 默认 ws 端口本是 8000，已在 `xiaozhi-esp32-server/main/xiaozhi-server/data/.config.yaml` 永久改为 8765；MCP Server 固定 8811；ngrok 公网隧道转发到 8811。
- **ngrok 单 endpoint 限制**：免费版 `uncover-earflap-unspoken.ngrok-free.dev` 同一时刻只能由一个进程占用；重复启动会被拒（`ERR_NGROK_334`），先 `Get-Process ngrok` 看看是否已有进程在跑。
- **ngrok 用途**：把本机 `:8811` MCP 服务暴露到公网，供云端小智或外部 LLM 客户端调用，对应仓库支持「本地/云端双环境切换」（commit `9904dce`）。

**整套启停**（PowerShell 示意，开 4 个终端）：

```powershell
# 终端 1 — 设定服务器
cd D:\aicoding\ds-oracle-cli
uvicorn app.main:app --host 0.0.0.0 --port 8812

# 终端 2 — MCP
cd D:\aicoding\ds-oracle-cli
python mcp_server.py --port 8811

# 终端 3 — 小智（注意是 .venv 解释器）
cd D:\aicoding\xiaozhi-esp32-server\main\xiaozhi-server
.\.venv\Scripts\python.exe app.py

# 终端 4 — ngrok
cd D:\aicoding\ds-oracle-cli
.\ngrok.exe http 8811
```

### 部署到服务器（线上 systemd）

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
uvicorn app.main:app --reload --host 0.0.0.0 --port 8812

# MCP 服务（大模型工具调用）
python mcp_server.py --port 8811

# CLI（本地交互）
python cli.py
```

### Docker

```bash
docker compose up -d
# API: http://localhost:8812
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
| `AUDIT_LOG_ROOT` | 审计日志根目录 | logs |
| `AUDIT_LOG_RETAIN_DAYS` | 每用户日志保留天数 | 30 |
| `MCP_USER_ID` | MCP 调用默认用户标识（未设则 mcp_anonymous） | -- |
| `SETTINGS_DB_URL` | 设置表数据库连接（默认 SQLite） | sqlite+aiosqlite:///./ds_oracle.db |

完整变量列表见 `.env.example`。

## 审计日志

所有设备请求、LLM 请求/响应、引擎调用、错误/警告，按 **用户 ID + 日期** 分片写入 JSONL，方便调试和追溯。

- **路径**：`logs/{user_id}/{YYYY-MM-DD}.jsonl`（目录由 `AUDIT_LOG_ROOT` 配置，默认 `logs/`）
- **保留**：每个用户保留最近 `AUDIT_LOG_RETAIN_DAYS` 天（默认 30 天），自动清理
- **格式**：每行一个 JSON 对象，含 `ts` / `level` / `event` / `user_id` / `trace_id` 及事件相关字段

### 用户 ID 识别策略
- **REST API**：JWT `sub` 优先 → API Token 末 8 位 → `X-Device-Id` / `X-User-Id` 头 → query `token` → `anonymous`
- **MCP**：`MCP_USER_ID` 环境变量，默认 `mcp_anonymous`（不同客户端可用不同值隔离日志）
- **CLI**：当前不写入审计日志（交互本地日志）

### 事件类型
| Event | 来源 | 说明 |
|-------|------|------|
| `request_in` / `response_out` | FastAPI 中间件 | 入站请求及响应状态/耗时 |
| `request_error` / `oracle_error` | FastAPI 中间件/异常处理 | 未捕获异常 / 业务异常 |
| `mcp_tool_in` / `mcp_tool_out` / `mcp_tool_error` | `_call_engine` | 工具调用参数、摘要预览、耗时 |
| `llm_request` / `llm_response` / `llm_error` | `kimi_client` | 模型、消息数、token 消耗、耗时、预览 |

同一次请求的所有事件共享 `trace_id`（FastAPI 请求或 MCP 工具调用开始时生成），LLM 调用通过 `contextvars` 自动继承。

### 查看示例
```bash
# 查看某用户今天所有事件
cat logs/user_8888/$(date +%F).jsonl | jq .

# 只看 LLM 请求和响应
grep -E '"event":"llm_' logs/user_8888/$(date +%F).jsonl | jq .

# 按 trace_id 串联一次完整链路
grep '"trace_id":"abc123def456"' logs/user_8888/$(date +%F).jsonl | jq .
```

## 项目结构

```
ds-oracle-cli/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── config.py             # 环境配置
│   ├── api/v1/               # API 路由
│   │   ├── chart.py          #   排盘接口（通用 + 14个便捷接口）
│   │   ├── almanac.py        #   GET /almanac/today|{date}
│   │   ├── setting.py        #   设备设置接口（参数校验 + 直接入库）
│   │   └── auth.py           #   SMS 登录
│   ├── engine/               # 命理引擎（15 个）
│   │   ├── registry.py       #   引擎注册器 + ChartRequest/ChartResult
│   │   ├── ziwei.py ~ hehun.py
│   │   └── jiri.py           #   黄道吉日查询
│   ├── pureziwei/            # 紫微斗数纯 Python 引擎
│   ├── lunar/                # 农历/八字/黄历计算库
│   ├── najia/                # 六爻纳甲装卦库
│   ├── data/                 # 静态数据（签文/解梦/笔画）
│   ├── auth/                 # JWT + SMS 认证
│   ├── store/                # 持久化：db.py / models / crud（默认 SQLite）
│   └── common/               # 异常、响应、工具函数、审计日志（audit_log.py）
├── mcp_server.py             # MCP Server（15 Tools）
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
| `meihua` | "帮我算一卦"（默认）、"报三个数字 5、3、2 算一卦"、"梅花易数测一下面试能不能过"、"我说三个数 7 2 4 帮我起卦" |
| `liuyao` | "帮我排个六爻"、"我摇了铜钱结果是 1 2 1 3 2 1"、"纳甲起卦问财运" |
| `liuyao_qigua` | "帮我起六爻卦"、"六爻卦"、"帮我摇一卦"、"我没铜钱帮我起个卦"、"系统帮我摇卦" |
| `iching` | "用周易帮我算一卦"、"帮我占个卦问问工作"、"大衍筮法起一卦" |
| `qimen` | "排个奇门遁甲"、"奇门看看今天时局"、"帮我起个奇门局" |
| `liuren` | "起个大六壬"、"六壬看看这件事"、"帮我排个六壬课" |

> **路由说明**：用户说"帮我算一卦"且未特指六爻时，默认走 `meihua`（梅花易数），提示用户报 3 个数字（上卦/下卦/动爻）；说"帮我起六爻卦"或"六爻卦"则走 `liuyao_qigua` 自动摇卦；用户已有爻码（如铜钱结果）则走 `liuyao`。

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

## 修改日志（Changelog）

按 commit 倒序列出主线变更。详细 diff 见 `git log`。

### 2026-04（本月）

| Commit | 类型 | 说明 |
|--------|------|------|
| `575621b` | docs | 刷新项目级 CLAUDE.md，把当前进度/关键决策/已知问题填实，反映 24 个 MCP 工具与 8000 端口编排 |
| `1266abc` | chore | gitignore `.omx/` 与 `as.log` 本地工具产物 |
| `e17dfc4` | fix(calendar) | `calendar_resolve("今年")` 改用区间中点算 ganzhi_year_solar，对齐 by_period.ganzhi_month。根因: 1/1 落在立春前会算成上一年干支，导致 LLM 把 2026 错说成"乙巳" |
| `f2ba5c5` | feat(mcp) v3 phase 5 | mcp_server instructions + `docs/mcp-system-prompt.md` 加 `*_period` 路由规则；含时间词强制走 *_period，禁止 LLM 自行推算月柱/刑冲合害 |
| `ac7a01c` | feat(mcp) v3 phase 1-4 | 注册 `calendar_resolve`、`ziwei_period`、`bazi_period`、`astrology_period` 为 MCP 工具 |
| `1b6550f` | feat(bazi) v3 phase 3 | `bazi_period` 八字流月批量 + 对命主关系完整实现 |
| `72bb8e2` | feat(ziwei) v3 phase 2 | `ziwei_period` 紫微运限批量分析 |
| `2dd961d` | feat(calendar) v3 phase 1 | `calendar_resolve` 自然语言时间解析（含 6 字段时段输出） |
| `64564ec` | docs | v3 设计稿（calendar_resolve + 3 period 工具） |
| `9904dce` | feat | 本地/云端双环境切换 + ngrok 隧道；`.env.local` 优先 `.env` 回落 |
| `f731915` | fix(mcp) | ziwei/bazi/astrology 三类工具统一 profile-first |
| `2aff538` | fix(mcp) | profile-aware 工具显式接受 device_id |
| `7a83d77` | feat | ziwei/bazi/astrology 自动从用户 profile 解析生辰 |
| `4f75bc9` | refactor | setting API 改为直存（不再调 LLM） |
| `8cf0aba` | docs | 设备端 setting API 集成指南 |
| `d195f35` | feat | 设备 setting API（LLM 模糊输入归一化版本，已被 4f75bc9 替换） |
| `8bbd18d` | feat | 按 user_id 日期分片的 JSONL 审计日志 |

### 2026-04 早期 — 工具扩展

| Commit | 类型 | 说明 |
|--------|------|------|
| — | feat | 新增妈祖六十甲子签 60 签数据（`app/data/qianwen/mazu.json`） |
| — | feat | 新增 4 个签文专用 MCP 工具：`qianwen_guanyin` / `qianwen_huangdaxian` / `qianwen_zhuge` / `qianwen_mazu`（绕过 sign_type 参数，便于直接调用） |

### 关键决策记录

- **2026-04-27** — `calendar_resolve.ganzhi_year_solar` 使用 `(start+end)/2` 中点计算干支。**Why**: 1/1 在立春前归属上一年干支（农历），与 `by_period.ganzhi_month` 字段算法不一致会让 LLM 抄错。**实际触发**: MazuKit v1.69 测试中 LLM 把 2026 说成「乙巳」。
- **2026-04-26** — 时段类提问统一走 `*_period` 工具，禁止 LLM 自行做农历换算/月柱推算/刑冲合害。**Why**: LLM 算术不可靠，必须由引擎权威给出；instructions 与 system-prompt 同步约束。
- **2026-04-25** — 引入 `calendar_resolve` + 3 个 period 工具作为时段类提问的标准前置/批量出口（v3 设计稿）。

---

## 许可证

MIT
