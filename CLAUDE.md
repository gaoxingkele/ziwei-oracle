# DS-Oracle 项目指南

## 项目概述
中华术数综合平台，FastAPI 后端 + MCP Server + CLI 客户端，集成 15 个命理/卜筮引擎。

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
