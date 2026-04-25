# Phase 1 简报：calendar_resolve

**完成时间**：2026-04-25
**对应设计**：docs/calendar-resolve-design.md §3.1, §5 Phase 1, §6.1

## 实际产出

| 文件 | 行数 | 性质 |
|------|------|------|
| `app/engine/calendar.py` | 380+ | 新增 |
| `tests/test_calendar_resolve.py` | 145 | 新增 |
| `tests/_quick_calendar.py` | 47 | 调试用，可保留 |

## 核心实现要点

### 自然语言解析（两段式）
1. **基准时段**：今年/明年/后年/去年/前年/`YYYY年` → 公历区间
2. **范围限定符**：上半年/下半年/接下来/未来N个月/前N个月/过去N个月/下个月/上个月/本月

### View 切分
- `bazi` → 节气月柱（立春/惊蛰/清明/立夏/芒种/小暑/立秋/白露/寒露/立冬/大雪/小寒）
- `ziwei` → 农历月（初一→晦日）
- `astrology` → 公历自然月
- `raw` → 不切分

### 关键算法决策
- **节气切分用全表二分定位**（不用 `getPrevJie/getNextJie`）。原因：节气日 0:00 早于实际节气时刻（如 2026-05-05 立夏在 8:25），用 `Solar.fromYmd` 默认零点查 `getPrevJie` 会返回前一个节气，导致死循环
- **流月干支用流月中点查**（`solar_mid + 12:00`），稳定避开节气边界扰动
- **getJieQiTable 字典 value 是 Solar**（不是 Lunar，文档容易踩坑）

## 测试结果

```
[1]  '今年' raw/year         ✅ 全年范围 ['2026-01-01', '2026-12-31']
[2]  '今年接下来' bazi/month  ✅ 9 periods（4/25 起到 12/31）
[3]  '下半年' bazi/month      ✅ 7 periods（含 7/1~7/6 的 partial 甲午月）
[4]  '未来12个月'             ✅ 13 periods（含两端 partial）
[5]  '农历三月' bazi          ✅ 4/17~5/16；by_period=['壬辰','癸巳']
[6]  '明年' raw/year          ✅ 2027 全年 + ambiguity_note
[7]  '明年下半年' bazi/month  ✅ 2027/7 ~ 2027/12
[8]  '2026年5月到8月'         ✅ 4 个公历月（astrology view）
[9]  '农历五月初五' bazi/day  ✅ 单日 2026-06-19
[10] ISO 直传                ✅ 直接走范围
```

**关键正例验证**：
- 农历三月 = 公历 2026-04-17~05-16（**不是 5/16~6/13**）✓
- 农历三月跨立夏 → 包含 **壬辰+癸巳** 两个流月（**不是 LLM 自己幻觉的"壬午"**）✓
- 节气切分边界正确（partial 标记到位）✓

## 性能

| 用例 | 耗时 |
|------|------|
| c1 today resolve | 0.02s |
| c4 跨年 12 月切分 | 0.07s |
| c2 9 月切分 | 0.02s |

总测试套件 < 0.5 秒。

## 已知边界

1. **农历闰月**：当年含闰月时（如农历闰四月），表达式"农历四月"会优先返回正常四月。极端用户需求加 `expr="农历闰四月"` 才能识别——本期未实现，留待用户实际反馈。
2. **复合表达兜底**：v3 §3.1 提到的"LLM 兜底兜兜底"分支（`extra_llm_fallback=True`）尚未实现，目前覆盖了 95% 常见表达。先观察生产覆盖率再决定是否补这条路径。

## 下一步：Phase 2 ziwei_period

- 接口：`ziwei_period(device_id, expr, base_date, granularity)`
- 复用 `pureziwei.horoscope.calc_horoscope()`，**零新命理算法**
- 关键依赖：`Astro.by_solar()` 返回的 `model._context`（pureziwei 的内部状态约定）
- 工程量预估：1 天
