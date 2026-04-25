# Phase 2 简报：ziwei_period

**完成时间**：2026-04-25
**对应设计**：docs/calendar-resolve-design.md §3.3, §5 Phase 2

## 实际产出

| 文件 | 行数 | 性质 |
|------|------|------|
| `app/engine/ziwei_period.py` | 145 | 新增 |
| `tests/_quick_ziwei_period.py` | 60 | 新增（冒烟） |

## 核心实现要点

100% wrapper `pureziwei.horoscope.calc_horoscope()`，**零新命理算法**：

1. 加载 profile → 调 `Astro().by_solar()` 排出本命盘 + 拿 `model._context`
2. 调 `calendar_resolve(view="ziwei")` 切农历月
3. 每月取中点日期 → 调 `calc_horoscope(horoscope_date=...)` 拿运限
4. 把 `HoroscopeModel.{yearly, decadal, age, monthly}` 转精简 dict

**字段映射**：
- `monthly.mutagen` 列表 → 精简成 `{禄:..., 权:..., 科:..., 忌:...}` dict
- `decadal/yearly_age` 同理
- 命宫主星按 `palace.name == "命宫"` 取（避免误用第一个宫位）

## 测试结果

```
[1] '今年下半年' month
   ✅ 命宫=酉 五行局=水二局
   ✅ 7 个农历月（含 7/1~7/13 partial 五月余 + 6 个完整农历月）
   ✅ 每月四化齐备（如六月乙未：禄天机/权天梁/科紫微/忌太阴）

[2] '今年' year
   ✅ 1 个全年 period（含流年+大限）

[3] '农历三月' month
   ✅ 单农历月 4/17~5/16
   ✅ 流月壬辰@辰：禄天梁、权紫微、科左辅、忌武曲

[4] 不完整 profile
   ✅ profile_incomplete 错误正确返回
```

## 准确性等级

**A 级** — pureziwei 标准实现：
- 流月干支与 lunar 库五虎遁一致
- 化禄/权/科/忌 由 pureziwei.data.mutagen_table 标准查表
- 流年/大限/小限 由 pureziwei.horoscope 标准算法

## 关键依赖：`Astro._context` 约定

`pureziwei.Astro._build_astrolabe()` 把内部状态保存在 `model._context`（pureziwei/astro.py:226 注释明确说"供 horoscope() 使用"）。本工具依赖这个约定 API：

```python
ctx = natal_model._context  # birth_cal, gender, direction, soul_palace_index,
                            # wu_xing_value, palace_stems, decadals, ages_table
```

未来 pureziwei 升级若改这个字段名需回归测试。

## 已知边界

1. **闰月**：calendar_resolve ziwei view 当前按"绝对月份序号"切，闰月会归到正常月（如闰四月归四月）。极端用户场景下需扩展。
2. **跨年时段**（如"未来 12 个月"）：每月 horoscope_date 用月中点查，跨年时 `yearly` 字段会动态切换（流年丙午→丁未），LLM 需要会读懂。

## 下一步：Phase 3 bazi_period

- 接口：`bazi_period(device_id, expr, base_date, granularity)`
- 复用 lunar 库 EightChar/LiuYue + 新写 ~70 行流月对命主关系代码
- 关键新算法：
  - 流月对日干十神（`LunarUtil.SHI_SHEN[day_gan + 流月干]` 查表）
  - 流月地支与原局四地支刑冲合害（`LunarUtil.CHONG/HE_GAN_5/HE_ZHI_6`）
  - 流月加入后五行 delta
  - 用神得失地（B 级，标注参考性）
- 工程量预估：2 天
