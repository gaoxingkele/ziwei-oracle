# 流月/流年时段分析工具设计方案 v3

> 目的：根治 LLM 在「农历↔公历换算 + 节气月柱推算 + 流月对命主命理关系」上的幻觉。
> 来源：MazuKit v1.64 实测发现，LLM 在 bazi/ziwei 工具返回静态命盘后，自行编造历法事实（农历三月=壬午月=公历 5/16~6/13；正确应为壬辰月、4/17~5/16）。
> 决策：**工具算尽一切命理关系，LLM 只做语言化解读**。LLM 不可靠的不仅是历法换算，连"流月十神"、"刑冲合害"这种规则查表也时常算错——尤其在多月份连续输出时错误会沿对话累积。
> 日期：2026-04-25
> v3 变更：
> - 撤回 v2 "LLM 拿干支自己算十神"的判断（实测不可靠）
> - 三个 `*_period` 工具回归（v1 思路），但**单步调用**（拒绝 v1 的双步 chain，避免 LLM 数组透传出错）
> - 明确每个字段的来源（依赖库现成 / 新写代码 / 暂留空），划清准确性边界
> - 占星 transit/ingress/retrograde 标记为后续升级项，本期占星只做基础切分

---

## 1. 关键区分：静态盘 vs 动态时段

### 1.1 静态盘（已有，**不动**）

| 工具 | 输入 | 输出 | 调用次数 |
|------|------|------|---------|
| `bazi`      | 生日 + 性别 + 地点 | 四柱 + 大运 + 用神 | 每用户一次（可缓存） |
| `ziwei`     | 生日 + 性别 + 地点 | 命盘 + 十二宫 + 主星 | 每用户一次 |
| `astrology` | 生日 + 地点      | 本命行星 + 宫位 + 相位 | 每用户一次 |

特点：依赖**用户出生参数**，按各自门派规则一次性算出，结果**不随当前时间变化**。

### 1.2 动态时段（本方案聚焦）

任何含时间表达的提问——无论问过去印证或问未来预测——都需要：

1. 从对话语义里识别用户**问的是哪段时间**（"今年下半年"/"农历三月"/"明年春节前后"/"2025 年 10 月"…）
2. 把这段时间换算成对应历法的精确范围（八字看节气月柱、紫微看农历月、占星看公历跨月）
3. 计算这段时间相对**用户静态命盘**的所有命理关系（流月十神、刑冲合害、宫位飞星、化禄化忌…）
4. 返回结构化数据，让 LLM **不做任何命理算术**，只做语言化解读

**核心原则**：LLM 不准——它推不对节气、月柱、十神、四化、刑冲合害。所有命理判定必须由工具完成。

---

## 2. 设计原则

| 责任 | 由谁承担 | 理由 |
|------|---------|------|
| 理解模糊时间表达 | **LLM** | 自然语言强项 |
| 历法精确换算 | **`calendar_resolve`** 内部 | LLM 不可靠 |
| 流月/流年干支推算 | **lunar / pureziwei 库** | 已有标准实现 |
| 流月对命主命理关系（十神/冲合/四化）| **`*_period` 工具内部** | 即便规则简单 LLM 也常错 |
| 自然语义包装 + 用户感知层语气 | **LLM** | 这是它该干的 |
| 上下文注入 | **MCP 协议自动**（tool_result 进 dialogue）| 不需要客户端额外做 |

**编排流程（典型）**：

```
用户："我下半年财运如何？"
                ↓
LLM 决策：识别"下半年" + 当前主话题是八字 → 调 bazi_period(device_id, expr="下半年")
                ↓
bazi_period 内部 4 步：
  1. expr → ISO 范围（calendar_resolve 复用）
  2. 按节气切分流月（lunar.JieQi）
  3. 每月算流月干支（lunar.LiuYue.getGanZhi）
  4. 每月算流月十神 + 与原局四柱的刑冲合害（新写，~35 行代码）
                ↓
返回：{natal_recap, by_period: [{ganzhi_month, solar_range, ten_god_to_day, interactions, ...}]}
                ↓
LLM 看到 final result：直接用其中字段语言化输出，禁止自行重算
```

LLM **只调一次工具**，prompt 不需要复杂的 chain 编排指令。

---

## 3. 工具规格

### 3.1 `calendar_resolve` — 纯历法换算（基础组件）

**职责**：把对话里的自然语言时间表达解析成多视角时间结构。**不做命理判定**。可独立调用（用户问"农历三月对应公历几号"时直接用），也作为 `*_period` 工具的内部组件。

```python
@mcp.tool()
def calendar_resolve(
    expr: str,
    base_date: str = "",       # 默认 today，YYYY-MM-DD
    view: str = "raw",         # "raw" | "bazi" | "ziwei" | "astrology"
    granularity: str = "auto", # "auto" | "day" | "month" | "year"
) -> dict:
    """
    支持：
    - 自然语言：今年/今年接下来/下半年/未来 12 个月/农历三月/明年春节前后/2025 年 10 月
    - ISO 区间：'{"from":"2026-04-25","to":"2026-12-31"}'
    - 单点：today / 2026-05-01
    """
```

**返回**：

```python
{
  "resolved": {
    "gregorian": ["2026-07-01", "2026-12-31"],   # 公历起止（依赖库：lunar.Solar）
    "lunar": "丙午年五月十七 ~ 丙午年冬月初三",       # 农历起止描述（lunar.Lunar）
    "ganzhi_year_solar": "丙午",                  # 公历年对应干支（按立春切，lunar 给）
    "jieqi_in_range": [                           # 时段内经过的节气（lunar.JieQi）
      {"name":"小暑","datetime":"2026-07-07 12:21"},
      ...
    ]
  },
  "view": "bazi",
  "granularity": "month",
  "by_period": [    # raw 时为 []；bazi/ziwei/astrology 时按各自切法分段
    {
      "solar_range": ["2026-07-07", "2026-08-06"],
      "lunar_range": "五月廿三 ~ 六月廿四",
      "ganzhi_month": "乙未",                 # bazi/ziwei 视图填，astrology 留空
      "lunar_month_idx": 6,                    # ziwei 视图主用
      "is_partial": false                      # 该时段是否被基准日期切开
    },
    ...
  ],
  "ambiguity_note": ""    # 解析有歧义时给提示，如"明年默认按公历计算"
}
```

**字段来源**：100% 来自 `app/lunar/`，零新算法。`view` 切分逻辑约 50 行新代码。

**自然语言解析两段式**：
- **基准时段**："今年"/"明年"/"2025 年"/"X 月" → 公历区间
- **范围限定符**："上半年"/"下半年"/"接下来"/"前 X 个月" → 在基准上裁切

复合表达解析失败时（如"后年春节前后"），回落到一次轻量 LLM 调用做兜底（`extra_llm_fallback=True`）。

---

### 3.2 `bazi_period` — 八字流年/流月时段分析

**职责**：吃 `device_id + expr`，内部完成"时间解析 → 历法换算 → 流月干支 → 流月对命主命理关系"，返回 LLM 可直接语言化的结构。

```python
@mcp.tool()
def bazi_period(
    device_id: str = "",
    expr: str = "今年接下来",
    base_date: str = "",
    granularity: str = "month",   # month（默认）| day（按需）| year（轻摘要）
) -> dict
```

**返回结构**：

```python
{
  "natal_recap": {                                # 命主信息回放（防 LLM 串错参照系）
    "year_gz": "乙亥", "month_gz": "己卯",
    "day_gz": "癸巳",  "hour_gz": "癸未",
    "day_master": "癸水",
    "yong_shen": ["金", "水"],                    # 出生时已判定的喜用神
    "ji_shen":   ["土", "火"]
  },
  "resolved": {...},                              # 同 calendar_resolve.resolved
  "by_period": [
    {
      "ganzhi_month": "乙未",
      "solar_range": ["2026-07-07", "2026-08-06"],
      "lunar_range": "五月廿三 ~ 六月廿四",
      "jieqi_start": {"name":"小暑","datetime":"2026-07-07 12:21"},
      "ten_god_to_day_gan":  "偏财",              # 流月天干对日主十神（lunar.SHI_SHEN 查表）
      "ten_god_to_day_zhi":  ["正官", "正印"],    # 流月地支藏干对日主十神（藏干主气+余气）
      "interactions_with_natal": [                # 流月地支与原局四柱地支的关系
        {"target":"month_zhi(卯)","relation":"未卯半合木"},
        {"target":"day_zhi(巳)","relation":"巳未拱午"},
        {"target":"hour_zhi(未)","relation":"自刑"}
      ],
      "wuxing_delta": {"金":+1,"木":+0,"水":+0,"火":+0,"土":+1},  # 流月五行加进来后的盘内变化
      "yong_shen_status": "弱化",                # 喜用神得失地（参考性，标准化为四档：得地/平/弱化/严重失地）
      "is_partial": false
    },
    ...
  ],
  "scope_note": "本期为流月分析，未含流日；如需精细到日请加 granularity='day'"
}
```

**字段来源**：

| 字段 | 来源 | 准确性 |
|------|------|--------|
| natal_recap | bazi 引擎已有结果（直接复用） | ✅ |
| resolved + solar/lunar_range/jieqi | lunar 库（`Solar`/`Lunar`/`JieQi`） | ✅ |
| ganzhi_month | `LiuYue.getGanZhi()`（五虎遁正确实现） | ✅ |
| ten_god_to_day_gan/zhi | 新写 5 行：`LunarUtil.SHI_SHEN[day_gan + 流月干]` | ✅ 算法等同出生月柱十神 |
| interactions_with_natal | 新写 ~30 行：流月地支 vs 原局 4 个地支批量比对 `LunarUtil.CHONG/HE_GAN_5/HE_ZHI_6` | ✅ 标准刑冲合害规则表 |
| wuxing_delta | 新写 ~10 行：原局五行计数 + 流月五行 1 加 | ✅ |
| yong_shen_status | 新写 ~20 行：用神所属五行 vs 当月五行强弱（**标准化四档输出，避开门派分歧**） | ⚠️ 中性参考。多门派对"用神得失地"判定有分歧，工具用最普适规则（用神五行得令/失令） |

总新代码量 ~70 行，全部在 lunar 库现有规则表上做查询。

---

### 3.3 `ziwei_period` — 紫微运限时段分析

**职责**：吃 `device_id + expr`，循环每月调 `pureziwei.horoscope.calc_horoscope()`，把流年/大限/小限/流月/化禄化权化科化忌 一次返还给 LLM。

```python
@mcp.tool()
def ziwei_period(
    device_id: str = "",
    expr: str = "今年接下来",
    base_date: str = "",
    granularity: str = "month",   # month（默认）| year（仅流年+大限）
) -> dict
```

**返回结构**：

```python
{
  "natal_recap": {
    "ming_gong": "卯", "shen_gong": "亥",
    "main_stars_in_ming": ["紫微", "天府"],
    "wu_xing_ju": "水二局"
  },
  "resolved": {...},
  "by_period": [
    {
      "lunar_month": "六月",
      "lunar_month_idx": 6,
      "solar_range": ["2026-07-15", "2026-08-12"],   # 农历六月对应公历范围
      "ganzhi_month": "乙未",
      "yearly": {                                     # 流年（pureziwei 给）
        "soul_palace": "巳",
        "stem_branch": "丙午",
        "mutagen": {"禄":"廉贞", "权":"破军", "科":"武曲", "忌":"太阳"}
      },
      "decadal": {                                    # 大限
        "palace": "辰",
        "stem_branch": "戊辰",
        "mutagen": {...}
      },
      "yearly_age": {                                 # 小限
        "palace": "亥",
        "nominal_age": 32
      },
      "monthly": {                                    # 流月
        "soul_palace": "申",
        "stem_branch": "乙未",
        "mutagen": {...},
        "stars_in_soul": ["天梁", "化禄"]
      }
    },
    ...
  ]
}
```

**字段来源**：100% 来自 `pureziwei.horoscope.calc_horoscope()`。**本工具不写任何命理算法**，只是 wrapper。准确性 = pureziwei 的准确性。

---

### 3.4 `astrology_period` — 占星时段（**本期基础版**）

**职责**：吃 `device_id + expr`，返回**时段公历切分** + 用户**本命盘回放**。**不算 transit/ingress/retrograde**——这些标记为后续升级项。

```python
@mcp.tool()
def astrology_period(
    device_id: str = "",
    expr: str = "今年接下来",
    base_date: str = "",
    granularity: str = "month",
) -> dict
```

**返回结构（v3 基础版）**：

```python
{
  "natal_recap": {
    "sun": {"sign":"双鱼","house":7,"position":12.34},
    "moon": {...}, "ascendant": {...},
    "planets": {...}
  },
  "resolved": {...},
  "by_period": [
    {
      "solar_range": ["2026-07-01", "2026-07-31"],
      "month_label": "2026 年 7 月",
      "is_partial": false
    },
    ...
  ],
  "scope_note": "本期占星 period 仅返回时段切分与本命盘；行星行运/相位/逆行扫描在后续版本提供。LLM 解读流年时请基于本命盘和已知占星常识做轻量判断，避免编造具体的 transit 日期。"
}
```

**字段来源**：

| 字段 | 来源 | 准确性 |
|------|------|--------|
| natal_recap | astrology 引擎已有结果（kerykeion） | ✅ |
| solar_range / month_label | calendar_resolve 复用 | ✅ |
| transit_aspects | ❌ **暂不输出** | — 后续版本 |
| ingresses | ❌ **暂不输出** | — 后续版本 |
| retrogrades | ❌ **暂不输出** | — 后续版本 |

**为什么基础版够用**：语音交互场景用户问占星往往是定性问题（"我今年木星运怎样"）。LLM 拿到本命盘 + 公历切分，能给出基于本命的合理通性解读。要精确 transit 日期需要 ephemeris 扫描，工程量大且与 astro.com 类标杆软件可能有 0.5°+ 偏差，留待后续验证。

`scope_note` 字段会让 LLM 自觉收敛"具体到几月几日"的输出。

---

## 4. System Prompt 修改

加进 `mcp_server.py` 的 FastMCP `instructions` 和 `docs/mcp-system-prompt.md`：

```markdown
## 涉及时段的命理提问，必须用 *_period 工具

凡用户问题包含时间词（今年/明年/X月/接下来/未来/上半年/下半年/什么时候/几号/最近/这段时间/过去那年），且需要给出时段相关的命理回答时，按当前主话题选择：

- 八字主题 → 调 `bazi_period(device_id, expr=<原文里的时间表达>)`
- 紫微主题 → 调 `ziwei_period(device_id, expr=<原文里的时间表达>)`
- 占星主题 → 调 `astrology_period(device_id, expr=<原文里的时间表达>)`

调用一次工具就能拿到全部信息，**不要先调 calendar_resolve 再调 *_period**——后者已经内部做了。

引用规则（铁律）：
- 输出里的日期、农历、月柱、十神、刑冲合害、化禄化忌**必须**直接来自工具返回字段
- 禁止自行做农历↔公历转换、五虎遁推月柱、节气日期估算
- 禁止自行算"流月对日主十神"、"流月与原局刑冲合害"、"流月四化飞星"——工具都给了
- 占星时段问题：拿到 by_period 切分后，基于本命盘做通性解读；不要编造具体的 transit 日期/星象事件

不需要时段工具的场景：
- "我命格如何"（无时间）→ 直接用静态 bazi/ziwei/astrology
- "农历三月对应公历几号"（纯历法查询）→ 用 calendar_resolve(view="raw")
```

---

## 5. 实现步骤

### Phase 1：`calendar_resolve` 主体（1 天）
1. 新建 `app/engine/calendar.py`（不走 `@register`，仅在 mcp_server 暴露）
2. 实现两段式自然语言解析（基准 + 限定符）
3. 实现 view 切分（bazi 节气 / ziwei 农历月 / astrology 公历月 / raw 不切）
4. `mcp_server.py` 注册 `@mcp.tool() calendar_resolve`
5. 单元测试覆盖 §6.1

### Phase 2：`ziwei_period`（1 天，**最稳**）
1. 新建 `app/engine/ziwei_period.py`
2. 调 `_resolve_device_id` 拿 profile，调 `ziwei` 引擎拿 natal
3. 调 `calendar_resolve(view="ziwei")` 拿月份切分
4. 循环每月调 `pureziwei.horoscope.calc_horoscope(horoscope_date=该月初一)`
5. `mcp_server.py` 注册工具
6. 单元测试 §6.2 + 与 pureziwei 默认输出对照

### Phase 3：`bazi_period`（2 天）
1. 新建 `app/engine/bazi_period.py`
2. 调 `_resolve_device_id` 拿 profile，调 `bazi` 引擎拿 natal（含 day_gan/yong_shen）
3. 调 `calendar_resolve(view="bazi")` 拿节气月切分
4. 对每月：
   - `LiuYue.getGanZhi()` 取流月干支
   - `LunarUtil.SHI_SHEN[day_gan + 流月干]` 算流月天干十神
   - 流月地支藏干 → 多个十神
   - 流月地支 vs 原局四个地支：查 `CHONG`/`HE_ZHI_6` 表算 interactions
   - 五行 delta：流月加入后五行计数变化
   - yong_shen_status：用神五行 vs 流月五行强弱（标准四档输出）
5. `mcp_server.py` 注册工具
6. 单元测试 §6.3 + 找命理书已知正例做对照

### Phase 4：`astrology_period`（基础版，0.5 天）
1. 新建 `app/engine/astrology_period.py`
2. wrapper：调 astrology 引擎拿 natal_recap，调 calendar_resolve(view="astrology") 拿公历月切分
3. 不实现 transit/ingress/retrograde，scope_note 字段说明
4. `mcp_server.py` 注册工具

### Phase 5：System prompt + 客户端（0.5 天）
1. 更新 `docs/mcp-system-prompt.md` 加入 §4 内容
2. 同步改 `mcp_server.py` 的 `FastMCP(instructions=...)`
3. MazuKit 客户端把每屏 ANTI_CAL_HALLUC 改为"涉及时间的命理问题用 *_period 工具"

### Phase 6：上线验收（0.5 天）
1. §7 端到端用例验
2. 监控生产 LLM 输出里"农历X月是壬午月"这类自行推算的错误句式应消失

**总工时 5.5 天**（占星 transit 后续升级再加 3-4 天）。

---

## 6. 单元测试用例

### 6.1 `calendar_resolve`

| expr | base_date | view | granularity | 期望 resolved.gregorian | by_period 数 | 关键校验 |
|------|-----------|------|-------------|-------------------------|------|----------|
| `"今年"` | 2026-04-25 | raw | year | 2026-01-01 ~ 2026-12-31 | 0 | 公历全年 |
| `"今年接下来"` | 2026-04-25 | bazi | month | 2026-04-25 ~ 2026-12-31 | ~9 | 起点是 base_date |
| `"下半年"` | 2026-04-25 | bazi | month | 2026-07-01 ~ 2026-12-31 | 6 | 7 月起，节气切 |
| `"未来 12 个月"` | 2026-04-25 | bazi | month | 2026-04-25 ~ 2027-04-24 | 12 | 滚动 12 月 |
| `"农历三月"` | 2026-04-25 | bazi | day | 2026-04-17 ~ 2026-05-16 | 30 | 公历 4/17 起 |
| `"农历三月"` | 2026-04-25 | ziwei | month | 2026-04-17 ~ 2026-05-16 | 1 | 农历整月 |
| `"明年"` | 2026-04-25 | raw | year | 2027-01-01 ~ 2027-12-31 | 0 | 公历明年（ambiguity_note 注明）|
| `"明年下半年"` | 2026-04-25 | bazi | month | 2027-07-01 ~ 2027-12-31 | 6 | 嵌套表达 |
| `"2026年5月到8月"` | 任意 | astrology | month | 2026-05-01 ~ 2026-08-31 | 4 | 公历区间 |
| `'{"from":"2026-04-25","to":"2026-12-31"}'` | 忽略 | bazi | month | 同 from/to | ~9 | ISO 直传 |

**关键正例**：
- 农历三月 = 公历 2026-04-17 至 2026-05-16（**不是** 5/16~6/13）
- 农历三月 bazi 视图月柱 = 壬辰（**不是** 壬午）
- bazi view 月份起点 = 节（立春/惊蛰/清明…），非农历初一也非公历 1 号

### 6.2 `ziwei_period`

| 输入 | 期望 |
|------|------|
| device 1995-03-03 14:03 男, expr="今年" | by_period 含 12 月（农历 1-12 月），yearly.stem_branch="丙午"，每月 mutagen 四化非空 |
| 同上, expr="下半年" | by_period 含农历 6-11 月（共 6 月） |
| 同上, expr="今年" granularity="year" | by_period 仅 1 项（含流年+大限 nameTag） |

校验点：每个月 `monthly.stem_branch` 应与 lunar 库 `LiuYue.getGanZhi()` 一致（pureziwei 内部应该已对齐，此为回归检查）。

### 6.3 `bazi_period`

| 输入 | 期望 |
|------|------|
| device 1995-03-03 14:03 男 (癸日干), expr="今年下半年" | 6 个流月，每月 `ten_god_to_day_gan` 字段非空，`interactions_with_natal` 数组无误（如 6 月乙未月：未对原局月柱卯成卯未半合木） |
| 单月手算对照 | 拿一个命理书例题（已知答案），跑工具对照每月十神/冲合 |
| `granularity="day"` 单日查询 | 返回 1 项，含日柱 + 日柱对日主十神 |

---

## 7. 端到端验收用例

部署后让 MazuKit 用以下提问触发，观察服务端日志的工具调用链：

| 用户提问 | 期望调用 | 期望解读引用 |
|---------|---------|-------------|
| "今年下半年财运" | `bazi`（如未调过）+ `bazi_period(expr="下半年")` | LLM 回复里出现 "乙未月（公历 7/7~8/6）流月偏财" 等工具返回字段 |
| "农历三月运势" | `bazi_period(expr="农历三月")` | "壬辰月（公历 4/17~5/16）" |
| "今年我紫微大限运势" | `ziwei_period(expr="今年", granularity="year")` | LLM 引用 yearly.mutagen 四化 |
| "今年木星行运对我影响" | `astrology_period(expr="今年")` | LLM 基于 natal_recap 通性解读，不编 transit 日期 |
| "农历三月对应公历几号" | `calendar_resolve(view="raw")` | 仅历法换算，不调命理工具 |
| "我命格如何" | `bazi` 或 `ziwei`（静态） | **不应**调 `*_period` |

**回归检查**：MazuKit 日志中"农历X月是壬午月"、"公历 5/16~6/13"、"流月正官但实际为偏财"等自行推算错误句式应消失。

---

## 8. 不在本方案范围

- **占星 transit/ingress/retrograde**（标记后续版本）
- **八字"用神得失地"的多门派分歧细化**（v3 用最普适的"五行得令/失令"标准四档输出，不深入子平派 vs 盲派 vs 新派的判定差异）
- **流时**（精度需求小，紫微和八字都能做但用户语音很少问到这粒度）
- **跨年大跨度（5 年以上）流月分析**（性能与精度边际收益低）
- 不重构现有 bazi/ziwei/astrology 引擎
- 不持有用户档案缓存（pureziwei 计算够快，每次现算；缓存收益低风险高）

---

## 9. v1 → v2 → v3 决策演进

| 项 | v1 | v2 | v3（当前） | 关键判断 |
|----|----|----|----|----|
| 工具数量 | 4（resolve + 3 period） | 1（仅 resolve） | **4**（同 v1 数量但 API 不同） | 既要解决幻觉又要 LLM 单步编排 |
| LLM 编排步数 | 2 步（chain） | 1 步 | **1 步** | 多步 chain 实测不稳 |
| 数组参数透传 | 有 | 无 | **无** | LLM 在长 JSON 数组上易错 |
| 命理计算谁干 | 工具 | LLM（错） | **工具** | LLM 不可靠（v2 修正） |
| 月柱/十神来源 | period 工具 | LLM 自算 | **工具用 lunar 库查表** | 标准命理算法 |
| 三流派切法 | 隐式 | view 枚举 | **view 枚举** | 显式建模 |
| "明年"语义 | 命理年 | 公历 | **公历**（ambiguity_note 注明） | 符合用户直觉 |
| astrology 范围 | 完整 transit | 完整 transit | **基础切分**（transit 留待升级） | 风险隔离，不阻塞主流程 |
| 工程量 | 7-9 天 | 2.5-3.5 天 | **5.5 天**（不含 transit） | 平衡确定性与覆盖度 |

---

## 10. 准确性边界声明（重要）

| 字段/能力 | 算法来源 | 准确性等级 |
|----------|---------|-----------|
| 公历↔农历换算、节气、流年/流月干支 | `lunar` 库 | A 命理标准实现 |
| 流月对日主十神、藏干十神 | `lunar.SHI_SHEN` 查表 | A 命理标准实现 |
| 流月与原局四柱刑冲合害 | `lunar.CHONG/HE_*` 查表 | A 命理标准实现 |
| 紫微流年/大限/小限/流月/四化飞星 | `pureziwei.horoscope` | A 紫微斗数标准实现 |
| 八字流月用神得失地（四档） | 新写，"用神五行得令/失令"标准规则 | B 中性参考；不同门派可能有 ±10% 判定差异 |
| 占星 transit aspects / ingress / retrograde | **本期不实现** | — 后续版本验证 |

A 级字段在 LLM 解读时可直接引用并强调精确性；B 级字段建议 LLM 表述为"参考性""可能"。

---

*v3 由 @gaoxingkele 与 Claude 在 2026-04-25 会话中确定。前两版决策与对账过程留存于会话归档供回溯。*
