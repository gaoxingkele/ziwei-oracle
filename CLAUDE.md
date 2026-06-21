# DS-Oracle 项目指南
## 工作守则
- 每完成一个有意义的步骤(改完一个函数、解决一个 bug、做出一个决定),
  立即把摘要追加到 `.claude/sessions/[今天日期].md`
- 每次 session 结束前,更新本文件的"当前进度"和"最近一次中断时的状态"
- 遇到不确定的设计决策,先记录到"关键决策记录",再继续

## 项目概述
中华术数综合平台，FastAPI 后端 + MCP Server + CLI 客户端，集成 15 个命理/卜筮引擎。

# 项目工作记忆

## 项目背景
- 目标: 中华术数综合平台 — 紫微/八字/占星/六壬/奇门/梅花/六爻/签文/解梦/合婚/起名/黄历/择日/生命灵数 一体化引擎
- 技术栈: Python 3.10+, FastAPI, MCP SDK (FastMCP), SQLite/PostgreSQL, Kimi/OpenAI/Claude LLM
- 关键约束: 引擎统一 `ChartRequest → ChartResult`，时间一律 `_parse_time()`，禁止 LLM 自行做命理算术

## 当前进度（截至 2026-06-21）
- 已完成:
  - 27 个 MCP 工具（16 命理含 lifenumber + 1 算法断卦 + 4 签文专用 + 5 时段/解析；详见下方 MCP Tools 清单）
  - 设备 setting API（5 POST + 1 GET，LLM 语义校准 + SQLite 持久化）
  - 按 user_id 分片的 JSONL 审计日志
  - 本地/云端双环境切换 + ngrok 隧道
  - profile-first：ziwei/bazi/astrology 自动从 device_id 取生辰
  - **v3 时段工具（5 个 phase 全部入库）**：
    - calendar_resolve（自然语言时间解析）
    - ziwei_period / bazi_period / astrology_period（运限/流月/时段批量分析）
    - mcp_server instructions + system-prompt 加 *_period 路由规则，禁止 LLM 自行推算
  - 修了 calendar_resolve("今年") 立春前误判 ganzhi_year 的 bug（改用区间中点）
- 进行中: —
- 待办:
  1. 硬件 SmartRing-Plus mazu_display.cc:1890 把 addon 里 `liuyao(...)` 改 `liuyao_verdict(...)`，下次 OTA 顺带

## 关键决策记录
- 2026-06-21: 玄学库（kerykeion/kinqimen/kinliuren/ichingshifa/najia）在 requirements.txt 由 `>=` 改 `==` pin 死已验证版本。原因: 排盘算法库小版本可能改变输出，云端重装漂移会导致命理结果不一致。当前 pin: kerykeion 5.12.8 / kinqimen 0.0.6.6 / kinliuren 0.1.2.9 / ichingshifa 3.1.9 / najia 2.0.1。lunar/pureziwei/najia 算法本体已内联在 app/ 下不随 pip 变。
- 2026-04-27: calendar_resolve 的 ganzhi_year_solar 改用 (start+end)/2 中点算干支，对齐 by_period.ganzhi_month。原因: 1/1 在立春前会算到上一年干支，与 by_period 字段打架，LLM 抄错导致 MazuKit v1.69 把 2026 说成"乙巳"。
- 2026-04-26: 时段类提问统一走 *_period 工具，禁止 LLM 自行做农历换算/月柱推算/刑冲合害。原因: LLM 算术不可靠，必须由引擎权威给出。
- 2026-04-25: 新增 calendar_resolve + 3 个 period 工具，作为时段类提问的标准前置/批量出口。

## 端口约定（已编排，互不冲突）

**所有相关服务一律从本项目 `D:\aicoding\ds-oracle-cli\` 内启动。** xiaozhi-server 等第三方代码已通过 `vendor/` 目录就地查阅/编辑/启动。

| 服务 | 端口 | 代码目录 | 启动 |
|---|---:|---|---|
| DS-Oracle FastAPI（设定 + 命理 REST）| **8812** | `app/` | `python -m uvicorn app.main:app --host 0.0.0.0 --port 8812` |
| DS-Oracle MCP Server（LLM 工具调用）| **8811** | `mcp_server.py` | `python mcp_server.py --port 8811` |
| xiaozhi-server（小智 ws/http）| **8765** ws + **8003** http | `vendor/xiaozhi-esp32-server/main/xiaozhi-server/` | `vendor\xiaozhi-esp32-server\main\xiaozhi-server\.venv\Scripts\python.exe app.py`（cwd 切到 vendor 路径）|
| manager-api（Java Spring 管理 API）| **8002** | `vendor/xiaozhi-esp32-server/main/manager-api/` | `mvn spring-boot:run` |
| manager-web（Vue 管理前端）| **8001** | `vendor/xiaozhi-esp32-server/main/manager-web/` | `npm install && npm run serve` |
| ngrok 公网隧道 | admin **4040** | 项目根 `ngrok.exe` | `.\ngrok.exe http 8811` |

**vendor/ 注意事项**：
- `vendor/xiaozhi-esp32-server/` 是 xiaozhi-server **完整自包含副本**（约 4.6 GB，含 models/data/test/.venv）
- 排除的只有 `node_modules/` 和 `.git/`（npm/git 可重建，不必要重复）
- xiaozhi-server 启动**完全不依赖原路径** `D:\aicoding\xiaozhi-esp32-server\`，所有依赖（含 .venv 的 opus.dll）已自包含在 vendor 内
- vendor/ 已加 .gitignore，**不入** ds-oracle 主项目 git 历史
- `vendor/.../data/.config.yaml` 含 API key，屏幕分享/分发压缩包时需剔除

## 已知问题 / 坑
- LLM 容易直接引用 calendar_resolve.ganzhi_year_solar 当流年，必须确保它和 by_period.ganzhi_month 算法一致（已修）。
- pytest 9 + Python 3.14 在 stdout capture 模块有 bug（`I/O operation on closed file`），逐文件跑测试可绕开。

## 最近一次中断时的状态
- 正在做: liuyao_verdict 全链路 + 4 引擎字段全暴露 + LLM 通俗化铁律已落地，commit 全部 push 到 origin/master
- 下一步应该: 硬件 SmartRing-Plus 下次 OTA 时把 mazu_display.cc:1890 的 `liuyao` addon 改成 `liuyao_verdict`
- 卡在哪: 无

## 技术栈
- Python 3.10+, FastAPI, Pydantic, SQLAlchemy (async)
- MCP: mcp SDK (FastMCP), 支持 streamable-http / SSE / stdio
- LLM: Kimi / OpenAI / Claude / Gemini 多厂商接口

## 关键文件
- `mcp_server.py` — MCP Server 入口，27 个 Tools，含完整 instructions 调度指南
- `app/engine/` — 16 个命理引擎，装饰器注册 `@register("system_name")`
- `app/engine/registry.py` — 引擎注册器，ChartRequest / ChartResult 数据模型
- `cli.py` — CLI 交互入口，18 项菜单
- `app/main.py` — FastAPI 入口
- `app/api/v1/chart.py` — REST API 路由（通用 + 便捷接口）
- `docs/mcp-trigger-prompts.md` — 各工具的语音唤醒提示词
- `docs/mcp-system-prompt.md` — 大模型调度指南（意图路由/反问策略/解读风格）

## MCP Tools（27 个）
- 命理 (16): ziwei, bazi, meihua, liuyao, liuyao_qigua, astrology, qimen, liuren, iching, qianwen, jiemeng, name_analysis, hehun, almanac, jiri, **lifenumber**（生命灵数/西方数字学）
- 算法断卦 (1): **liuyao_verdict** — 用神/旺衰/动变/四神/吉凶倾向，LLM 仅做白话翻译
- 签文专用 (4): qianwen_guanyin, qianwen_huangdaxian, qianwen_zhuge, qianwen_mazu
- 时段/解析 (5): calendar_resolve, ziwei_period, bazi_period, astrology_period, **lifenumber_period**
- 设备设置: 5 POST + 1 GET（不是 MCP，是 REST）— `/api/v1/setting/*`

## 开发约定
- 引擎统一接口: `ChartRequest` → `ChartResult`，通过 `@register()` 装饰器注册
- MCP 工具通过 `_call_engine()` 统一调用引擎
- 时间格式统一由 `_parse_time()` 处理（支持 24h/中文/时辰名/序号）
- `.env` 配置 API_TOKENS, LLM_PROVIDER, KIMI_API_KEY 等
- Git remote: https://github.com/gaoxingkele/ziwei-oracle.git, 主分支 master

## 常用命令
```bash
# MCP Server
python mcp_server.py --port 8811

# API Server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8812

# CLI
python cli.py

# 测试所有引擎
python test_all_engines.py
```
