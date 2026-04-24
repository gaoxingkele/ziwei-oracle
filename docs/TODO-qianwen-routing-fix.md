# 修复计划：紫微/八字话题被 LLM 误路由到求签工具

> 生成时间：2026-04-18
> 起因：MazuKit 客户端在"紫微斗数"屏问"今年财运如何"，服务端流式回复
> 前半段正常（紫微语气），后半段突然串到**妈祖六十甲子签**签诗内容。
> 本文件记录根因与建议改动，**不包含代码修改**——请手动执行。

---

## 1. 客户端送达服务端的原文（确证，来自 MazuKit logs/proxy.log）

MazuKit v1.48 在紫微话题下以 `listen/detect.text` 方式发送：

```
用户资料：姓名可用拆证，性别女，公历生日1995-08-03 16:00，出生地浙江 杭州。
今天是2026年4月18日。用户问：今年2026年的财运如何？
```

服务端流式回复（同一轮）：

```
[02:02:59] 今年2026年的财运整体来说是比较乐观的
[02:03:04] 签诗中提到"只恐前途有变迁，劝君作事可宜先根据"，
          妈祖六十意味着在财运甲子签的结果方面可能会有一些变化 ...
```

→ 前半紫微语气正常，后半混入妈祖签文。**客户端发送无误**，问题在服务端 LLM 路由/上下文控制。

> 客户端侧已于 v1.49 追加硬约束前缀："请严格用紫微斗数理论作答 ... 禁止使用求签/签诗/六十甲子签形式或 MCP 求签工具"。这是**临时缓解**，根治仍需服务端改。

---

## 2. 根因：ds-oracle-cli MCP 的两处诱导

### 风险 A — `qianwen_huangdaxian` docstring 含"求财、问运"关键词

文件：`mcp_server.py:616-623`

```python
@mcp.tool()
async def qianwen_huangdaxian(question: str = "") -> str:
    """黄大仙灵签（共100签）。求财、问运、问事尤验。

    Args:
        question: 心中所问之事
    """
    return await _draw_qian("huangdaxian", question)
```

**问题**：`求财` / `问运` / `问事` 三个词高度吸引 LLM 在看到用户问"财运/运势/事业"时把该工具当候选。  
**建议改为**：

```python
@mcp.tool()
async def qianwen_huangdaxian(question: str = "") -> str:
    """黄大仙灵签（共100签）。传统以问财、问运、问事见长。

    ⚠️ 仅当用户**明确**表达"抽签 / 求一支黄大仙签 / 摇签" 时调用。
    用户若只是问"运势 / 财运 / 事业 / 感情 / 健康"（未指定方法），
    应改用 ziwei / bazi / astrology，不要默认走本工具。

    Args:
        question: 心中所问之事
    """
    return await _draw_qian("huangdaxian", question)
```

同样的模式请一并修正其它签文工具的描述：

- `qianwen_guanyin`（mcp_server.py:606）
- `qianwen_zhuge`（mcp_server.py:626）
- `qianwen_mazu`（mcp_server.py:636）
- `qianwen`（通用入口，mcp_server.py:578）

统一在 docstring 第一段尾部追加一句"⚠️ 仅当用户明确要求抽签/求签时调用；询问运势/财运/感情等应改用 ziwei/bazi/astrology"。

### 风险 B — `FastMCP.instructions` 路由表缺"运势/财运 → 非 qianwen"反向规则

文件：`mcp_server.py:159-246`（`mcp = FastMCP(...)` 的 `instructions` 字符串）

**当前路由表（节选）**：

```
- 紫微/命盘/十二宫/主星 → ziwei
- 八字/四柱/五行/日主/天干地支/大运 → bazi
- ...
- 求签/抽签/灵签/签文（未指定签种）→ qianwen（默认观音，可 sign_type 切换）
```

**当前模糊意图处理（节选）**：

```
- "看看我的命运/运势" → 反问："您想看紫微斗数（侧重命盘格局）还是八字...？"
- "帮我算一卦" → 默认走梅花易数
- "帮我算算" → 反问"您想算什么呢？"
```

**问题**：缺"用户问财运/事业/感情/健康"这类**高频具体问题**的默认路由，LLM 自由发挥时可能挑中 qianwen_*。

**建议在"模糊场景处理"段追加**：

```markdown
- "今年财运如何/事业顺不顺/感情怎样/身体好吗"（**泛意**问运势，未指定方法）
  → **默认** ziwei 或 bazi（出生档案齐全时直接调用，零追问）
  → **不要**走 qianwen / qianwen_* —— 求签仅用于用户明确说"抽签/求签"
```

**同时在"核心原则"段（mcp_server.py:164 附近）追加第 4 条**：

```markdown
4. **方法默认优先命盘**：用户问具体运势/财运/事业/感情/健康等问题时，
   首选 `ziwei(device_id=...)` 或 `bazi(device_id=...)`，而非求签类。
   只有用户**明确**说"抽签""求一支xx签""摇签"时，才调 qianwen / qianwen_*。
```

---

## 3. 独立问题：ds-oracle-cli 的 MCP 是否接入了小智 WS 服务器？

从 MazuKit 的日志观察：
- 紫微话题下流式回复里**没有**任何工具调用的痕迹（无 `tool_result` 片段、无结构化命盘）
- 只是自由文本，前紫微后签诗——更像 LLM hallucinate

推测：**小智 WS 服务器（117.50.48.22:8000）可能没连 ds-oracle-cli 的 MCP**，或只连了老版本的求签 MCP。

**待确认**（本文不包含改动，仅列出）：
1. 小智服务器侧的 `.mcp/` 配置里是否有 `http://<host>:8811`（ds-oracle MCP 默认端口）？
2. 若未接入，接入后紫微问题应能直接路由到 `ziwei(device_id=...)`，流式回复里可见命盘摘要。
3. 若已接入但仍 hallucinate，考虑把 `FastMCP.instructions` 的"核心原则"也同步进小智服务器的 system prompt（小智开源版允许自定义 system）。

参考已有文档 `docs/xiaozhi-mcp-integration.md`。

---

## 4. 改动清单（打钩执行）

- [ ] `mcp_server.py:578-594` — `qianwen` docstring 加硬约束
- [ ] `mcp_server.py:606-613` — `qianwen_guanyin` docstring 加硬约束
- [ ] `mcp_server.py:616-623` — `qianwen_huangdaxian` docstring 加硬约束（删除"求财、问运"诱导词或改为说明性措辞）
- [ ] `mcp_server.py:626-633` — `qianwen_zhuge` docstring 加硬约束
- [ ] `mcp_server.py:636-643` — `qianwen_mazu` docstring 加硬约束
- [ ] `mcp_server.py:164` 附近 — `FastMCP.instructions` "核心原则"加第 4 条"方法默认优先命盘"
- [ ] `mcp_server.py:193` 附近 — "模糊场景处理"加"今年财运如何 → ziwei/bazi"规则
- [ ] 确认小智 WS 服务器已连 ds-oracle MCP（检查 mcp 配置端口 8811）
- [ ] 重启 MCP Server / 小智服务器后，用 MazuKit 紫微屏回归测试"今年财运如何？"

---

## 5. 验证

部署后用 MazuKit v1.49 紫微屏录音问：**"今年财运如何？"**

**期望结果**（任选其一即为修复成功）：
- ✅ 服务端流式回复出现"命宫/身宫/主星"等紫微术语，无签诗片段
- ✅ 日志可见 `ziwei(device_id=...)` 工具调用记录
- ❌ 仍出现"签诗/甲子/妈祖"等字样 → 说明服务端未接入 MCP 或 system prompt 未生效，回到第 3 节排查

---

*本文件由 MazuKit 侧 Claude 会话生成，提交给 ds-oracle-cli 的维护者执行。*
