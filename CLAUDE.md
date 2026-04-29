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
- 目标: 中华术数综合平台 — 紫微/八字/占星/六壬/奇门/梅花/六爻/签文/解梦/合婚/起名/黄历/择日 一体化引擎
- 技术栈: Python 3.10+, FastAPI, MCP SDK (FastMCP), SQLite/PostgreSQL, Kimi/OpenAI/Claude LLM
- 关键约束: 引擎统一 `ChartRequest → ChartResult`，时间一律 `_parse_time()`，禁止 LLM 自行做命理算术

## 当前进度（截至 2026-04-29）
- 已完成:
  - 19 个原始 MCP 工具（15 命理 + 4 签文专用）
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
  1. xiaozhi-esp32-server 接入实测（ds-oracle FastAPI 8000 端口需让位，建议改 8010）
  2. 项目状态/CLAUDE.md 同步到 memory/project_status.md

## 关键决策记录
- 2026-04-27: calendar_resolve 的 ganzhi_year_solar 改用 (start+end)/2 中点算干支，对齐 by_period.ganzhi_month。原因: 1/1 在立春前会算到上一年干支，与 by_period 字段打架，LLM 抄错导致 MazuKit v1.69 把 2026 说成"乙巳"。
- 2026-04-26: 时段类提问统一走 *_period 工具，禁止 LLM 自行做农历换算/月柱推算/刑冲合害。原因: LLM 算术不可靠，必须由引擎权威给出。
- 2026-04-25: 新增 calendar_resolve + 3 个 period 工具，作为时段类提问的标准前置/批量出口。

## 已知问题 / 坑
- DS-Oracle FastAPI 默认 :8000 与小智 xiaozhi-server :8000 ws 端口冲突，本机同时跑需改一边端口。
- LLM 容易直接引用 calendar_resolve.ganzhi_year_solar 当流年，必须确保它和 by_period.ganzhi_month 算法一致（已修）。

## 最近一次中断时的状态
- 正在做: v3 时段工具收尾，所有 commit 已 push 到 origin/master
- 下一步应该: 用户要求并行启动 4 个服务器（小智 xiaozhi-server + manager-api + DS-Oracle MCP + DS-Oracle 设定服务器），需先解决 8000 端口冲突
- 卡在哪: 等用户确认第 4 个服务器是不是 manager-api，以及 ds-oracle FastAPI 改用哪个端口

## 技术栈
- Python 3.10+, FastAPI, Pydantic, SQLAlchemy (async)
- MCP: mcp SDK (FastMCP), 支持 streamable-http / SSE / stdio
- LLM: Kimi / OpenAI / Claude / Gemini 多厂商接口

## 关键文件
- `mcp_server.py` — MCP Server 入口，15 个 Tools，含完整 instructions 调度指南
- `app/engine/` — 15 个命理引擎，装饰器注册 `@register("system_name")`
- `app/engine/registry.py` — 引擎注册器，ChartRequest / ChartResult 数据模型
- `cli.py` — CLI 交互入口，18 项菜单
- `app/main.py` — FastAPI 入口
- `app/api/v1/chart.py` — REST API 路由（通用 + 便捷接口）
- `docs/mcp-trigger-prompts.md` — 15 个工具的语音唤醒提示词
- `docs/mcp-system-prompt.md` — 大模型调度指南（意图路由/反问策略/解读风格）

## MCP Tools（24 个）
- 命理 (15): ziwei, bazi, meihua, liuyao, liuyao_qigua, astrology, qimen, liuren, iching, qianwen, jiemeng, name_analysis, hehun, almanac, jiri
- 签文专用 (4): qianwen_guanyin, qianwen_huangdaxian, qianwen_zhuge, qianwen_mazu
- 时段/解析 (4): calendar_resolve, ziwei_period, bazi_period, astrology_period
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
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# CLI
python cli.py

# 测试所有引擎
python test_all_engines.py
```
