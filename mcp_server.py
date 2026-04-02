"""DS-Oracle MCP Server — 14 个命理计算引擎作为 MCP Tools 暴露给大模型调用

启动:
  python mcp_server.py                    # 默认 streamable-http, 0.0.0.0:8811
  python mcp_server.py --port 9000        # 自定义端口
  python mcp_server.py --transport sse    # SSE 模式
  python mcp_server.py --transport stdio  # stdio 模式（本地调试）
"""
from __future__ import annotations

import argparse
import importlib
import os
import re
from pathlib import Path

from dotenv import load_dotenv

# 加载 .env
load_dotenv(Path(__file__).resolve().parent / ".env")

from mcp.server.fastmcp import FastMCP

# ── 注册所有引擎 ──
for mod in [
    "app.engine.ziwei", "app.engine.bazi", "app.engine.meihua",
    "app.engine.liuyao", "app.engine.astrology", "app.engine.qimen",
    "app.engine.liuren", "app.engine.iching", "app.engine.qianwen",
    "app.engine.jiemeng", "app.engine.name_analysis", "app.engine.hehun",
    "app.engine.almanac", "app.engine.jiri",
]:
    importlib.import_module(mod)

from app.engine.registry import ChartRequest, calculate as engine_calculate

# ── 时间转换：24小时制 → 时辰序号 ──
_SHICHEN_ORDER = "早子 丑 寅 卯 辰 巳 午 未 申 酉 戌 亥 晚子".split()


def _hour_to_shichen(hour: int) -> int:
    if hour == 0:
        return 0
    if hour == 23:
        return 12
    return (hour + 1) // 2


def _parse_time(s: str) -> str:
    """将多种时间格式统一转为时辰序号字符串。"""
    s = (s or "").strip()
    if not s:
        return "6"
    # 时辰名
    if s in _SHICHEN_ORDER:
        return str(_SHICHEN_ORDER.index(s))
    # HH:MM
    m = re.match(r"^(\d{1,2}):(\d{2})$", s)
    if m:
        return str(_hour_to_shichen(int(m.group(1)) % 24))
    # 中文: 上午9点, 下午3点
    m = re.match(r"^(上午|早上|凌晨|下午|晚上|傍晚)(\d{1,2})点?$", s)
    if m:
        period, h = m.group(1), int(m.group(2))
        if period in ("下午", "晚上", "傍晚") and 1 <= h <= 11:
            h += 12
        elif period == "凌晨" and h == 12:
            h = 0
        return str(_hour_to_shichen(h % 24))
    # 纯数字
    if s.isdigit():
        n = int(s)
        if 0 <= n <= 12:
            return str(n)
        if 13 <= n <= 23:
            return str(_hour_to_shichen(n))
    return "6"


# ── 创建 MCP Server ──
mcp = FastMCP(
    "DS-Oracle",
    instructions=(
        "DS-Oracle 是一套东方命理计算工具集，包含紫微斗数、八字、梅花易数、六爻、"
        "奇门遁甲、大六壬、周易、西方星盘、求签、解梦、姓名分析、合婚、黄历、黄道吉日等。"
        "每个工具返回精准的计算结果（text_summary），你应基于这些结果用亲切、专业的风格为用户解读。"
        "解读时避免宿命化断言和灾祸渲染，用现代语言表达传统智慧，给出可执行的建议。"
    ),
)


async def _call_engine(system: str, **kwargs) -> str:
    """统一调用引擎并返回 text_summary。"""
    req = ChartRequest(system=system, **kwargs)
    result = await engine_calculate(req)
    return result.text_summary


# ══════════════════════════════════════════════
# 14 个 MCP Tools
# ══════════════════════════════════════════════

@mcp.tool()
async def ziwei(
    name: str,
    birth_date: str,
    birth_time: str,
    gender: str,
) -> str:
    """紫微斗数排盘。根据出生信息排出命盘十二宫、主星亮度、四化等。

    Args:
        name: 姓名
        birth_date: 公历出生日期，格式 YYYY-MM-DD，如 1990-05-15
        birth_time: 出生时间，支持 24小时制(如14:00)、中文(如下午2点)、时辰名(如午)
        gender: 性别，男 或 女
    """
    return await _call_engine(
        "ziwei", name=name, birth_date=birth_date,
        birth_time=_parse_time(birth_time), gender=gender,
    )


@mcp.tool()
async def bazi(
    name: str,
    birth_date: str,
    birth_time: str,
    gender: str,
) -> str:
    """八字排盘（四柱八字）。排出年月日时四柱、十神、藏干、纳音等。

    Args:
        name: 姓名
        birth_date: 公历出生日期，格式 YYYY-MM-DD
        birth_time: 出生时间，支持 24小时制(如14:00)、中文(如下午2点)、时辰名(如午)
        gender: 性别，男 或 女
    """
    return await _call_engine(
        "bazi", name=name, birth_date=birth_date,
        birth_time=_parse_time(birth_time), gender=gender,
    )


@mcp.tool()
async def meihua(
    question: str,
    birth_date: str = "",
    birth_time: str = "",
) -> str:
    """梅花易数起卦。根据时间起卦，得到本卦、互卦、变卦和体用关系。

    Args:
        question: 占题/所问之事，如"本周面试能否通过"
        birth_date: 起卦日期 YYYY-MM-DD，留空为当天
        birth_time: 起卦时间，留空为当前时辰
    """
    from datetime import datetime
    if not birth_date:
        birth_date = datetime.now().strftime("%Y-%m-%d")
    return await _call_engine(
        "meihua", name="占问", birth_date=birth_date,
        birth_time=_parse_time(birth_time), gender="男", question=question,
    )


@mcp.tool()
async def liuyao(
    yao_codes: list[int],
    question: str = "",
    birth_date: str = "",
    gender: str = "男",
) -> str:
    """六爻排盘（纳甲法）。根据六爻码排出卦象、世应、六亲、六兽等。

    Args:
        yao_codes: 六爻码，6个数字(1~4)的列表，从初爻到上爻。1=少阳 2=少阴 3=老阳(动) 4=老阴(动)
        question: 占题/所问之事
        birth_date: 起卦日期 YYYY-MM-DD，留空为当天
        gender: 性别
    """
    from datetime import datetime
    if not birth_date:
        birth_date = datetime.now().strftime("%Y-%m-%d")
    return await _call_engine(
        "liuyao", name="占问", birth_date=birth_date,
        birth_time="6", gender=gender, question=question,
        extra={"yao_codes": yao_codes},
    )


@mcp.tool()
async def astrology(
    name: str,
    birth_date: str,
    birth_time: str,
    gender: str,
) -> str:
    """西方占星术星盘。计算太阳、月亮、上升等星体在星座和宫位的分布。

    Args:
        name: 姓名
        birth_date: 公历出生日期，格式 YYYY-MM-DD
        birth_time: 出生时间，支持 24小时制(如14:00)、中文(如下午2点)
        gender: 性别，男 或 女
    """
    return await _call_engine(
        "astrology", name=name, birth_date=birth_date,
        birth_time=_parse_time(birth_time), gender=gender,
    )


@mcp.tool()
async def qimen(
    birth_date: str = "",
    birth_time: str = "",
    question: str = "",
) -> str:
    """奇门遁甲排盘。排出八门、九星、八神、天地人三盘。

    Args:
        birth_date: 日期 YYYY-MM-DD，留空为当天
        birth_time: 时间，留空为当前时辰
        question: 占问之事
    """
    from datetime import datetime
    if not birth_date:
        birth_date = datetime.now().strftime("%Y-%m-%d")
    return await _call_engine(
        "qimen", name="占问", birth_date=birth_date,
        birth_time=_parse_time(birth_time), gender="男", question=question,
    )


@mcp.tool()
async def liuren(
    birth_date: str = "",
    birth_time: str = "",
    guiren: int = 1,
    question: str = "",
) -> str:
    """大六壬排盘。排出四课、三传、天地盘、格局等。

    Args:
        birth_date: 日期 YYYY-MM-DD，留空为当天
        birth_time: 时间，留空为当前时辰
        guiren: 贵人选择，1=昼贵 2=夜贵，默认1
        question: 占问之事
    """
    from datetime import datetime
    if not birth_date:
        birth_date = datetime.now().strftime("%Y-%m-%d")
    return await _call_engine(
        "liuren", name="占问", birth_date=birth_date,
        birth_time=_parse_time(birth_time), gender="男",
        question=question, extra={"guiren": str(guiren)},
    )


@mcp.tool()
async def iching(
    question: str,
    birth_date: str = "",
    birth_time: str = "",
) -> str:
    """周易筮法（大衍筮法）。以传统方式起卦，得本卦、之卦及爻辞。

    Args:
        question: 占问之事
        birth_date: 日期 YYYY-MM-DD，留空为当天
        birth_time: 时间，留空为当前时辰
    """
    from datetime import datetime
    if not birth_date:
        birth_date = datetime.now().strftime("%Y-%m-%d")
    return await _call_engine(
        "iching", name="占问", birth_date=birth_date,
        birth_time=_parse_time(birth_time), gender="男", question=question,
    )


@mcp.tool()
async def qianwen(
    sign_type: str = "guanyin",
    question: str = "",
) -> str:
    """求签。支持观音灵签(98签)、黄大仙灵签(100签)、诸葛神算(384签)。

    Args:
        sign_type: 签种，guanyin=观音灵签, huangdaxian=黄大仙灵签, zhuge=诸葛神算
        question: 心中所问之事
    """
    from datetime import datetime
    return await _call_engine(
        "qianwen", name="求签", birth_date=datetime.now().strftime("%Y-%m-%d"),
        birth_time="0", gender="男", question=question,
        extra={"type": sign_type},
    )


@mcp.tool()
async def jiemeng(
    keyword: str,
) -> str:
    """周公解梦。根据梦境关键词查询解梦条目。

    Args:
        keyword: 梦境关键词，如"蛇"、"飞"、"水"、"考试"
    """
    from datetime import datetime
    return await _call_engine(
        "jiemeng", name="解梦", birth_date=datetime.now().strftime("%Y-%m-%d"),
        birth_time="0", gender="男", question=keyword,
    )


@mcp.tool()
async def name_analysis(
    name: str,
) -> str:
    """姓名五格分析。根据康熙字典笔画计算天格、人格、地格、外格、总格及三才配置。

    Args:
        name: 待分析的姓名，如"张三丰"
    """
    return await _call_engine(
        "name_analysis", name=name, birth_date="2000-01-01",
        birth_time="0", gender="男",
    )


@mcp.tool()
async def hehun(
    name_a: str,
    birth_date_a: str,
    birth_time_a: str,
    gender_a: str,
    name_b: str,
    birth_date_b: str,
    birth_time_b: str,
    gender_b: str,
) -> str:
    """八字合婚。对比双方八字，从日干、纳音、地支六合/六冲等维度评分。

    Args:
        name_a: 甲方姓名
        birth_date_a: 甲方公历出生日期 YYYY-MM-DD
        birth_time_a: 甲方出生时间
        gender_a: 甲方性别，男 或 女
        name_b: 乙方姓名
        birth_date_b: 乙方公历出生日期 YYYY-MM-DD
        birth_time_b: 乙方出生时间
        gender_b: 乙方性别，男 或 女
    """
    return await _call_engine(
        "hehun", name=name_a, birth_date=birth_date_a,
        birth_time=_parse_time(birth_time_a), gender=gender_a,
        extra={
            "spouse_birth_date": birth_date_b,
            "spouse_birth_time": _parse_time(birth_time_b),
            "spouse_gender": gender_b,
        },
    )


@mcp.tool()
async def almanac(
    date: str = "",
) -> str:
    """黄历查询。查询指定日期的宜忌、吉神凶煞、冲煞、时辰吉凶等。

    Args:
        date: 查询日期 YYYY-MM-DD，留空为今天
    """
    from datetime import datetime as dt
    if not date:
        date = dt.now().strftime("%Y-%m-%d")
    return await _call_engine(
        "almanac", name="查询", birth_date=date,
        birth_time="0", gender="男",
    )


@mcp.tool()
async def jiri(
    activity: str,
    start_date: str = "",
    end_date: str = "",
) -> str:
    """黄道吉日查询。在日期范围内查找适合特定事项的黄道吉日。
    支持口语输入如"结婚"、"搬家"、"开业"等，会自动映射为黄历标准术语。

    Args:
        activity: 要查询的事项，如"结婚"、"搬家"、"开业"、"出行"、"动土"
        start_date: 起始日期 YYYY-MM-DD，留空为今天
        end_date: 截止日期 YYYY-MM-DD，留空为起始日期后30天
    """
    from datetime import datetime as dt
    if not start_date:
        start_date = dt.now().strftime("%Y-%m-%d")
    extra = {"start_date": start_date}
    if end_date:
        extra["end_date"] = end_date
    return await _call_engine(
        "jiri", name="吉日查询", birth_date=start_date,
        birth_time="0", gender="男", question=activity, extra=extra,
    )


# ══════════════════════════════════════════════
# 启动入口
# ══════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DS-Oracle MCP Server")
    parser.add_argument("--transport", default="streamable-http",
                        choices=["stdio", "sse", "streamable-http"],
                        help="传输方式 (默认 streamable-http)")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址 (默认 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8811, help="监听端口 (默认 8811)")
    args = parser.parse_args()

    if args.transport == "stdio":
        print("DS-Oracle MCP Server (stdio mode)")
        mcp.run(transport="stdio")
    else:
        # FastMCP 通过环境变量读取 host/port
        os.environ["UVICORN_HOST"] = args.host
        os.environ["UVICORN_PORT"] = str(args.port)
        print(f"DS-Oracle MCP Server starting on {args.host}:{args.port} ({args.transport})")
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.run(transport=args.transport)
