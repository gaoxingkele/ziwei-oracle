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

# 加载 .env：本机调试若存在 .env.local 则优先用它（云端无此文件，回落 .env）
_root = Path(__file__).resolve().parent
load_dotenv(_root / ".env.local" if (_root / ".env.local").exists() else _root / ".env")

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

# ── 注册所有引擎（缺依赖的跳过：本机调试常见，如 kerykeion/kinqimen）──
for mod in [
    "app.engine.ziwei", "app.engine.bazi", "app.engine.meihua",
    "app.engine.liuyao", "app.engine.astrology", "app.engine.qimen",
    "app.engine.liuren", "app.engine.iching", "app.engine.qianwen",
    "app.engine.jiemeng", "app.engine.name_analysis", "app.engine.hehun",
    "app.engine.almanac", "app.engine.jiri",
]:
    try:
        importlib.import_module(mod)
    except ImportError as _e:
        print(f"[warn] engine skipped: {mod} ({_e})")

from app.engine.registry import ChartRequest, calculate as engine_calculate
from app.engine.calendar import resolve_calendar
from app.engine.ziwei_period import calculate_ziwei_period
from app.engine.bazi_period import calculate_bazi_period
from app.engine.astrology_period import calculate_astrology_period

# ── 时间转换：24小时制 → 时辰序号 ──
_SHICHEN_ORDER = "早子 丑 寅 卯 辰 巳 午 未 申 酉 戌 亥 晚子".split()


def _hour_to_shichen(hour: int) -> int:
    if hour == 0:
        return 0
    if hour == 23:
        return 12
    return (hour + 1) // 2


# ── 用户档案（device_id = MCP_USER_ID）──
_REQUIRED_PROFILE_FIELDS = ("birthday", "birthtime", "city", "sex")


def _sex_to_gender(sex) -> str | None:
    if sex == 1 or sex == "1":
        return "男"
    if sex == 0 or sex == "0":
        return "女"
    return None


def _resolve_device_id(device_id: str = "") -> str:
    """统一 device_id 解析：显式参数 > MCP_USER_ID 环境变量 > mcp_anonymous。"""
    did = (device_id or "").strip()
    if did:
        return did
    return os.getenv("MCP_USER_ID") or "mcp_anonymous"


async def _load_user_profile(device_id: str = "") -> dict:
    """读取指定 device_id（或默认当前 MCP 用户）的档案。未设置字段为 None。"""
    from app.store.crud.settings import get_setting
    from app.store.db import SessionLocal

    did = _resolve_device_id(device_id)
    async with SessionLocal() as session:
        row = await get_setting(session, did)
    if row is None:
        return {"device_id": did, "name": None, "sex": None,
                "birthday": None, "birthtime": None, "city": None,
                "updated_at": None}
    return row.to_dict()


def _missing_profile_fields(profile: dict) -> list[str]:
    return [f for f in _REQUIRED_PROFILE_FIELDS if not profile.get(f) and profile.get(f) != 0]


async def _resolve_birth_args(
    name: str, birth_date: str, birth_time: str, gender: str,
    device_id: str = "", city: str = "",
) -> tuple[str, str, str, str, str]:
    """无论 LLM 是否传参，都尝试读取档案并用档案补齐空位；
    返回 (name, birth_date, birth_time, gender, city)。
    仍有 date/time/gender 缺失时抛 ValueError 让 LLM 向用户追问。"""
    # 始终查档案（即便 LLM 已经传了全部参数）——档案主要用来补 city 字段
    profile = await _load_user_profile(device_id)

    name = name or (profile.get("name") or "")
    birth_date = birth_date or (profile.get("birthday") or "")
    birth_time = birth_time or (profile.get("birthtime") or "")
    if not gender:
        gender = _sex_to_gender(profile.get("sex")) or ""
    city = city or (profile.get("city") or "")

    missing = []
    if not birth_date:
        missing.append("出生日期")
    if not birth_time:
        missing.append("出生时间")
    if not gender:
        missing.append("性别")
    if not city:
        missing.append("出生地点")
    if missing:
        raise ValueError(
            f"当前用户档案（device_id={profile.get('device_id')}）缺少："
            + "、".join(missing)
            + "。请询问用户：出生日期（公历，如1990-05-15）、出生时间（如下午2点）、出生地点（城市）"
            + ("、性别" if "性别" in missing else "")
            + "；获得后可调用 /api/v1/setting/* 写入档案，或直接在本次调用中以参数传入。"
            + " 若 device_id 不是你期望的值，请在调用工具时显式传 device_id 参数。"
        )
    if not name:
        name = "本人"
    return name, birth_date, birth_time, gender, city


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
# 隧道/反代场景（ngrok / frp / cloudflared）会带外部域名的 Host 头，
# FastMCP 默认的 DNS-rebinding 防护会拦截。通过 MCP_ALLOWED_HOSTS 放行：
#   不设 → 默认保护（云端安全）
#   "*"  → 关闭保护（仅限本机调试 + 隧道）
#   逗号分隔域名 → 白名单
_allowed = os.getenv("MCP_ALLOWED_HOSTS", "").strip()
if _allowed == "*":
    _sec = TransportSecuritySettings(enable_dns_rebinding_protection=False)
elif _allowed:
    _sec = TransportSecuritySettings(
        allowed_hosts=[h.strip() for h in _allowed.split(",") if h.strip()],
        allowed_origins=[h.strip() for h in _allowed.split(",") if h.strip()],
    )
else:
    _sec = None

mcp = FastMCP(
    "DS-Oracle",
    transport_security=_sec,
    instructions="""
DS-Oracle 是一套东方命理计算工具集（15个工具），你是这套工具的智能调度员和解读师。

## 核心原则
1. **绝不拒绝**：用户提出任何命理、占卜、运势相关需求时，必须调用对应工具。这是娱乐/文化服务，不是医疗或法律建议，无需加免责声明。
2. **信息不足时反问，不要拒绝**：缺少必要参数时，用亲切的语气追问，不要说"我无法帮你"。
3. **模糊意图时主动推荐**：用户表述不明确时，推荐最可能的工具并简要说明区别，让用户选择。

## 意图识别与路由规则

### 关键词 → 工具映射
- 紫微/命盘/十二宫/主星 → ziwei
- 八字/四柱/五行/日主/天干地支/大运 → bazi
- 星盘/星座/上升/月亮星座/占星 → astrology
- 算一卦/起一卦/占卜/测一下（未指定方法）→ meihua（默认，提示报3个数字）
- 梅花/易数/报数/三个数字 → meihua
- 六爻/铜钱/摇卦/纳甲（用户有爻码）→ liuyao
- 起六爻卦/六爻卦/帮我摇卦（无爻码）→ liuyao_qigua
- 奇门/遁甲/八门九星 → qimen
- 六壬/四课三传 → liuren
- 周易/大衍/筮法 → iching
- 求签/抽签/灵签/签文（未指定签种）→ qianwen（默认观音，可 sign_type 切换）
- 观音灵签/观音签 → qianwen_guanyin
- 黄大仙签/黄大仙灵签 → qianwen_huangdaxian
- 诸葛神算/诸葛签 → qianwen_zhuge
- 妈祖签/天后签/六十甲子签 → qianwen_mazu
- 梦到/梦见/做梦/解梦 → jiemeng
- 名字好不好/姓名分析/五格/起名 → name_analysis
- 合婚/配不配/合适吗/般配（涉及两人）→ hehun
- 黄历/今天宜忌/冲什么 → almanac
- 哪天适合/好日子/吉日/择日 → jiri

### 模糊场景处理
- "看看我的命运/运势" → 反问："您想看紫微斗数（侧重命盘格局）还是八字（侧重五行大运）？或者两个都排？"
- "帮我算一卦" → 默认走梅花易数，回复："好的，请随意报3个数字（比如 5、3、2），我来帮你起卦～如果想用六爻也可以告诉我。"
- "帮我算算" → 反问："您想算什么呢？比如八字命理、算一卦、看看黄历、还是其他？"
- "我想看看感情" → 反问："您想用什么方式看感情呢？可以算一卦（梅花易数）、看八字、或者和对象合婚～"
- "今天适合搬家吗" → almanac（查当天宜忌）
- "什么时候适合搬家" → jiri（择吉日）

## 参数收集策略（反问模板）

当缺少必要参数时，用以下方式追问：

### 需要出生信息的工具（ziwei / bazi / astrology / hehun）—— 档案优先（强制）

**这组工具共用同一条规则，不因具体工具名而改变。** 不管用户是问"八字"、"紫微"还是"星座/星盘"，流程完全一致：

1. **device_id 透传**：系统提示或用户消息里会下发 `device_id`。所有档案相关调用（`get_user_profile` / `ziwei` / `bazi` / `astrology` / `hehun`）**必须把这个 device_id 原样传入**，一次对话中不可遗漏、不可更改。
2. **零追问策略**：不要先问"请告诉我生日时间"之类。第一步就是**直接调用目标工具**（如 `ziwei(device_id=...)`），其他参数全部留空。服务端会自动读取档案补齐。
3. **只在服务端返回 "当前用户档案（device_id=...）缺少：…" 错误后，才按下面模板追问**：
   > 好的～麻烦告诉我您要咨询之人的：
   > 1. 姓名（称呼就行）
   > 2. 出生日期（公历，如1990年5月15日）
   > 3. 出生时间（大概几点就行，如下午2点）
   > 4. 出生地点（城市）
   > 5. 性别
4. 如果想先确认档案是否齐全（避免用户体验上的"错误后再问"），可以先调 `get_user_profile(device_id=...)` 查看。
5. 错误消息里的 device_id 如果不对（与对话上下文下发的不一致），请在下一次工具调用里显式传正确的 device_id。
6. **给他人排盘**（如"帮我朋友排一下"）：此时**不要**依赖档案，应把对方姓名/日期/时间/地点/性别作为参数显式传给工具。

**反例（不要这么做）**：
- ❌ 用户说"帮我看紫微" → LLM 回答"请告诉我你的生日和时间"
- ❌ 用户说"我的星盘如何" → LLM 只问生日不调用 `astrology`
- ✅ 正确做法：直接 `ziwei(device_id="...")` 或 `astrology(device_id="...")`，档案齐全就出结果，缺失才追问。

### 需要占题的工具（meihua/liuyao_qigua/iching/qimen/liuren）
"请问您想问什么事呢？比如事业、感情、财运、出行等，说得越具体解读越准哦～"

### 梅花易数报数
"请随意报3个数字（任何数字都行，跟着感觉走），我来帮你起卦～"

### 合婚（hehun）
"好的，合婚需要双方的信息：
甲方：姓名、出生日期、出生时间、性别
乙方：姓名、出生日期、出生时间、性别"

## 解读风格
- 基于工具返回的 text_summary 进行解读，保留专业术语但用白话解释
- 语气亲切自然，像一位懂行的朋友在聊天
- 避免宿命化断言（不说"你命中注定"），用"从盘面来看""趋势上""可以留意"等表述
- 避免灾祸渲染，遇到不利信息用建设性方式表达（如"这段时间宜守不宜攻"而非"大凶"）
- 给出具体可执行的建议，而非笼统的"顺其自然"
- 可以组合调用多个工具来给出更全面的解读
""",
)


async def _call_engine(system: str, **kwargs) -> str:
    """统一调用引擎并返回 text_summary。"""
    import os
    import time
    from app.common import audit_log

    user_id = os.getenv("MCP_USER_ID") or "mcp_anonymous"
    trace_id = audit_log.new_trace_id()
    tokens = audit_log.set_context(user_id=user_id, trace_id=trace_id)
    start = time.perf_counter()
    audit_log.log_event(
        user_id, "mcp_tool_in", trace_id=trace_id,
        system=system,
        params={k: v for k, v in kwargs.items() if k != "extra"},
        extra=kwargs.get("extra") or {},
    )
    try:
        req = ChartRequest(system=system, **kwargs)
        result = await engine_calculate(req)
    except Exception as exc:
        audit_log.log_event(
            user_id, "mcp_tool_error", level="ERROR", trace_id=trace_id,
            system=system, error_type=type(exc).__name__, error=str(exc),
            duration_ms=int((time.perf_counter() - start) * 1000),
        )
        audit_log.reset_context(tokens)
        raise
    summary = result.text_summary
    audit_log.log_event(
        user_id, "mcp_tool_out", trace_id=trace_id,
        system=system, chart_id=result.chart_id,
        summary_len=len(summary),
        summary_preview=summary[:300],
        duration_ms=int((time.perf_counter() - start) * 1000),
    )
    audit_log.reset_context(tokens)
    return summary


# ══════════════════════════════════════════════
# 14 个 MCP Tools
# ══════════════════════════════════════════════


@mcp.tool()
async def get_user_profile(device_id: str = "") -> str:
    """查询指定 device_id 的用户档案（姓名/性别/出生日期/出生时间/出生地点）。
    在调用 ziwei/bazi/astrology/hehun 前应先调用本工具，确认档案是否已设定：
      - 若已设定出生日期/时间/地点/性别，则直接调用对应工具并传同一 device_id（其它参数留空即可）
      - 若字段为 null，则先询问用户补全这些信息
    档案由设备端通过 /api/v1/setting/birthday、/birthtime、/city、/sex、/name 写入，
    需保证与调用本工具时传入的 device_id 一致。

    Args:
        device_id: 设备/用户标识；留空则使用服务端环境变量 MCP_USER_ID，再无则 mcp_anonymous
    """
    profile = await _load_user_profile(device_id)
    missing = _missing_profile_fields(profile)
    lines = [
        f"device_id: {profile.get('device_id')}",
        f"姓名 name: {profile.get('name') or '（未设置）'}",
        f"性别 sex: {_sex_to_gender(profile.get('sex')) or '（未设置）'}",
        f"出生日期 birthday: {profile.get('birthday') or '（未设置）'}",
        f"出生时间 birthtime: {profile.get('birthtime') or '（未设置）'}",
        f"出生地点 city: {profile.get('city') or '（未设置）'}",
        f"updated_at: {profile.get('updated_at') or '—'}",
    ]
    if missing:
        lines.append("")
        lines.append("缺失字段：" + "、".join(missing) + " —— 请向用户询问后再调用命理工具。")
    else:
        lines.append("")
        lines.append("档案完整，可直接以空参数调用 ziwei/bazi/astrology。")
    return "\n".join(lines)

@mcp.tool()
async def ziwei(
    name: str = "",
    birth_date: str = "",
    birth_time: str = "",
    gender: str = "",
    city: str = "",
    device_id: str = "",
) -> str:
    """紫微斗数排盘。根据出生信息排出命盘十二宫、主星亮度、四化等。
    调用策略：推荐仅传入 device_id，其余留空——服务端会自动用该设备已保存的档案
    （由 /api/v1/setting/* 设定）补齐。档案齐全时**不要**再向用户追问。

    Args:
        name: 姓名（留空使用档案）
        birth_date: 公历出生日期 YYYY-MM-DD（留空使用档案）
        birth_time: 出生时间，支持 24h/中文/时辰名（留空使用档案）
        gender: 性别，男 或 女（留空使用档案）
        city: 出生地（留空使用档案；ziwei 本身不依赖城市但用于校验档案完整性）
        device_id: 设备标识；留空则用服务端 MCP_USER_ID
    """
    name, birth_date, birth_time, gender, _city = await _resolve_birth_args(
        name, birth_date, birth_time, gender, device_id=device_id, city=city,
    )
    return await _call_engine(
        "ziwei", name=name, birth_date=birth_date,
        birth_time=_parse_time(birth_time), gender=gender,
    )


@mcp.tool()
async def bazi(
    name: str = "",
    birth_date: str = "",
    birth_time: str = "",
    gender: str = "",
    city: str = "",
    device_id: str = "",
) -> str:
    """八字排盘（四柱八字）。排出年月日时四柱、十神、藏干、纳音等。
    调用策略：推荐仅传入 device_id，其余留空——服务端会自动用该设备已保存的档案补齐。
    档案齐全时**不要**再向用户追问。

    Args:
        name: 姓名（留空使用档案）
        birth_date: 公历出生日期 YYYY-MM-DD（留空使用档案）
        birth_time: 出生时间（留空使用档案）
        gender: 性别，男 或 女（留空使用档案）
        city: 出生地（留空使用档案；bazi 本身不依赖城市但用于校验档案完整性）
        device_id: 设备标识；留空则用服务端 MCP_USER_ID
    """
    name, birth_date, birth_time, gender, _city = await _resolve_birth_args(
        name, birth_date, birth_time, gender, device_id=device_id, city=city,
    )
    return await _call_engine(
        "bazi", name=name, birth_date=birth_date,
        birth_time=_parse_time(birth_time), gender=gender,
    )


@mcp.tool()
async def meihua(
    question: str,
    numbers: list[int] | None = None,
    birth_date: str = "",
    birth_time: str = "",
) -> str:
    """梅花易数起卦。用户报3个数字起卦，或根据时间自动起卦。得到本卦、互卦、变卦和体用关系。
    这是"帮我算一卦"的默认工具（除非用户明确要求六爻）。

    Args:
        question: 占题/所问之事，如"本周面试能否通过"
        numbers: 用户报的3个数字，分别用于上卦、下卦、动爻。如[5,3,2]。留空则按时间自动起卦
        birth_date: 起卦日期 YYYY-MM-DD，留空为当天
        birth_time: 起卦时间，留空为当前时辰
    """
    from datetime import datetime
    if not birth_date:
        birth_date = datetime.now().strftime("%Y-%m-%d")
    extra = {}
    if numbers and len(numbers) >= 3:
        extra["numbers"] = numbers
    return await _call_engine(
        "meihua", name="占问", birth_date=birth_date,
        birth_time=_parse_time(birth_time), gender="男", question=question,
        extra=extra,
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
async def liuyao_qigua(
    question: str = "",
    gender: str = "男",
) -> str:
    """六爻起卦（自动摇卦）。系统自动模拟摇铜钱六次生成卦象，并进行六爻解读。
    适用于用户没有铜钱、不知道爻码，想让系统帮忙起卦的场景。

    Args:
        question: 占题/所问之事，如"最近工作能否顺利"
        gender: 性别，男 或 女，默认男
    """
    import hashlib
    import time
    from datetime import datetime

    # 以当前时间戳为种子，生成6个爻码
    ts = time.time_ns()
    yao_codes = []
    for i in range(6):
        seed = f"{ts}-yao-{i}"
        h = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
        yao_codes.append(h % 4 + 1)  # 1=少阳 2=少阴 3=老阳 4=老阴

    yao_names = {1: "少阳 ⚊", 2: "少阴 ⚋", 3: "老阳 ⚊→⚋(动)", 4: "老阴 ⚋→⚊(动)"}
    shake_detail = "\n".join(
        f"  第{i+1}爻: {yao_names[c]}" for i, c in enumerate(yao_codes)
    )

    birth_date = datetime.now().strftime("%Y-%m-%d")
    result = await _call_engine(
        "liuyao", name="占问", birth_date=birth_date,
        birth_time="6", gender=gender, question=question,
        extra={"yao_codes": yao_codes},
    )

    return f"【自动摇卦结果】\n{shake_detail}\n爻码: {yao_codes}\n\n{result}"


@mcp.tool()
async def astrology(
    name: str = "",
    birth_date: str = "",
    birth_time: str = "",
    gender: str = "",
    city: str = "",
    device_id: str = "",
) -> str:
    """西方占星术星盘。计算太阳、月亮、上升等星体在星座和宫位的分布。
    调用策略：推荐仅传入 device_id，其余留空——服务端会自动用该设备已保存的档案
    （含出生地 city）补齐，不要再向用户追问出生信息。
    注：出生地用于星盘的城市标签；经纬度/时区目前使用服务端默认值。

    Args:
        name: 姓名（留空使用档案）
        birth_date: 公历出生日期 YYYY-MM-DD（留空使用档案）
        birth_time: 出生时间（留空使用档案）
        gender: 性别，男 或 女（留空使用档案）
        city: 出生地（留空使用档案中的 city）
        device_id: 设备标识；留空则用服务端 MCP_USER_ID
    """
    name, birth_date, birth_time, gender, city = await _resolve_birth_args(
        name, birth_date, birth_time, gender, device_id=device_id, city=city,
    )
    return await _call_engine(
        "astrology", name=name, birth_date=birth_date,
        birth_time=_parse_time(birth_time), gender=gender,
        extra={"city": city},
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
    """求签（通用入口）。支持观音灵签(98签)、黄大仙灵签(100签)、诸葛神算(384签)、妈祖六十甲子签(60签)。

    Args:
        sign_type: 签种，guanyin=观音灵签, huangdaxian=黄大仙灵签, zhuge=诸葛神算, mazu=妈祖六十甲子签
        question: 心中所问之事
    """
    from datetime import datetime
    return await _call_engine(
        "qianwen", name="求签", birth_date=datetime.now().strftime("%Y-%m-%d"),
        birth_time="0", gender="男", question=question,
        extra={"type": sign_type},
    )


async def _draw_qian(qtype: str, question: str) -> str:
    from datetime import datetime
    return await _call_engine(
        "qianwen", name="求签", birth_date=datetime.now().strftime("%Y-%m-%d"),
        birth_time="0", gender="男", question=question,
        extra={"type": qtype},
    )


@mcp.tool()
async def qianwen_guanyin(question: str = "") -> str:
    """观音灵签（共98签）。心诚所问，抽一签获诗偈、解签、典故。

    Args:
        question: 心中所问之事
    """
    return await _draw_qian("guanyin", question)


@mcp.tool()
async def qianwen_huangdaxian(question: str = "") -> str:
    """黄大仙灵签（共100签）。求财、问运、问事尤验。

    Args:
        question: 心中所问之事
    """
    return await _draw_qian("huangdaxian", question)


@mcp.tool()
async def qianwen_zhuge(question: str = "") -> str:
    """诸葛神算（共384签）。对应易经384爻，擅断吉凶进退。

    Args:
        question: 心中所问之事
    """
    return await _draw_qian("zhuge", question)


@mcp.tool()
async def qianwen_mazu(question: str = "") -> str:
    """妈祖六十甲子签（共60签）。以六十甲子配签诗，渡海、出行、平安事尤应。

    Args:
        question: 心中所问之事
    """
    return await _draw_qian("mazu", question)


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
# Period 工具（Phase 1-4）
# ══════════════════════════════════════════════

@mcp.tool()
async def calendar_resolve(
    expr: str,
    base_date: str = "",
    view: str = "raw",
    granularity: str = "auto",
) -> str:
    """解析中文/自然语言时间表达式，返回公历/农历范围和按时段切分列表。

    Args:
        expr: 时间表达式，如"今年"、"明年上半年"、"2025年3月"、"2025-03-01~2025-06-30"
        base_date: 基准日期 YYYY-MM-DD，留空为今天
        view: 切分视角，raw/bazi/ziwei/astrology
        granularity: 切分粒度，auto/month/year
    """
    import json
    result = resolve_calendar(expr=expr, base_date=base_date, view=view, granularity=granularity)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def ziwei_period(
    expr: str,
    base_date: str = "",
    granularity: str = "month",
    device_id: str = "",
) -> str:
    """紫微斗数运限分析——给定时间范围，返回流年/流月与命宫主星的关系。
    调用策略：仅传 expr 和 device_id，服务端自动读取命主档案。

    Args:
        expr: 时间表达式，如"今年"、"明年上半年"、"2025年3月"
        base_date: 基准日期 YYYY-MM-DD，留空为今天
        granularity: 切分粒度，month（默认）或 year
        device_id: 设备标识；留空则用服务端 MCP_USER_ID
    """
    import json
    profile = await _load_user_profile(device_id)
    result = calculate_ziwei_period(profile=profile, expr=expr, base_date=base_date, granularity=granularity)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def bazi_period(
    expr: str,
    base_date: str = "",
    granularity: str = "month",
    device_id: str = "",
) -> str:
    """八字流年流月分析——给定时间范围，返回各流月天干地支与日主的刑冲合害、十神关系。
    调用策略：仅传 expr 和 device_id，服务端自动读取命主档案。

    Args:
        expr: 时间表达式，如"今年"、"明年上半年"、"2025年3月"
        base_date: 基准日期 YYYY-MM-DD，留空为今天
        granularity: 切分粒度，month（默认）或 year
        device_id: 设备标识；留空则用服务端 MCP_USER_ID
    """
    import json
    profile = await _load_user_profile(device_id)
    result = calculate_bazi_period(profile=profile, expr=expr, base_date=base_date, granularity=granularity)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def astrology_period(
    expr: str,
    base_date: str = "",
    granularity: str = "month",
    device_id: str = "",
) -> str:
    """西方占星时段分析——给定时间范围，返回本命盘摘要与时段切分（基础版，不含行星行运）。
    调用策略：仅传 expr 和 device_id，服务端自动读取命主档案。

    Args:
        expr: 时间表达式，如"今年"、"明年上半年"、"2025年3月"
        base_date: 基准日期 YYYY-MM-DD，留空为今天
        granularity: 切分粒度，month（默认）或 year
        device_id: 设备标识；留空则用服务端 MCP_USER_ID
    """
    import json
    profile = await _load_user_profile(device_id)
    result = calculate_astrology_period(profile=profile, expr=expr, base_date=base_date, granularity=granularity)
    return json.dumps(result, ensure_ascii=False, indent=2)


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
