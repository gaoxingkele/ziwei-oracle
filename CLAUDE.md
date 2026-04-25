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
- 目标:[一句话说明]
- 技术栈:[语言/框架]
- 关键约束:[比如"必须兼容 Python 3.9"、"不要改动 X 模块"]

## 当前进度
- 已完成:[功能A、模块B]
- 进行中:[正在改 xxx.py 的 yyy 函数]
- 待办:[1. ... 2. ... 3. ...]

## 关键决策记录
- 2026-04-25:决定用 X 而不是 Y,原因:...
- 2026-04-23:重构了 auth 模块,接口变成 ...

## 已知问题 / 坑
- [踩过的坑,避免再踩]

## 最近一次中断时的状态
- 正在做:[具体到函数名/文件名/行号]
- 下一步应该:[非常具体的下一步动作]
- 卡在哪:[如果有疑问或阻塞]

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

## 15 个 MCP Tools
ziwei, bazi, meihua, liuyao, liuyao_qigua, astrology, qimen, liuren, iching, qianwen, jiemeng, name_analysis, hehun, almanac, jiri

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
