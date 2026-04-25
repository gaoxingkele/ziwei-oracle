"""calendar_resolve 单元测试（v3 §6.1 测试用例）。

跑法：
    cd D:/aicoding/ds-oracle-cli
    python -m tests.test_calendar_resolve
"""
import sys
import io
import json

# Windows GBK stdout 兼容：强制 utf-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from app.engine.calendar import resolve_calendar


BASE = "2026-04-25"


def assert_range(result, expect_from, expect_to, label):
    g = result.get("resolved", {}).get("gregorian", [])
    if g != [expect_from, expect_to]:
        print(f"  ❌ {label}: expected {[expect_from, expect_to]}, got {g}")
        return False
    print(f"  ✅ {label}")
    return True


def assert_period_count(result, expect_count, label, tolerance=1):
    n = len(result.get("by_period", []))
    if abs(n - expect_count) > tolerance:
        print(f"  ❌ {label}: expected ~{expect_count} periods, got {n}")
        return False
    print(f"  ✅ {label}: {n} periods")
    return True


def main():
    print("=" * 60)
    print("calendar_resolve 单元测试 v3 §6.1")
    print(f"BASE_DATE={BASE}")
    print("=" * 60)

    failed = 0

    # 1. "今年" raw year
    print("\n[1] '今年' raw/year → 全年公历")
    r = resolve_calendar("今年", base_date=BASE, view="raw", granularity="year")
    if not assert_range(r, "2026-01-01", "2026-12-31", "全年范围"):
        failed += 1

    # 2. "今年接下来" bazi/month
    print("\n[2] '今年接下来' bazi/month → 起点 base_date")
    r = resolve_calendar("今年接下来", base_date=BASE, view="bazi", granularity="month")
    if not assert_range(r, "2026-04-25", "2026-12-31", "起点 base_date"):
        failed += 1
    if not assert_period_count(r, 9, "约 9 个流月", tolerance=1):
        failed += 1

    # 3. "下半年"
    print("\n[3] '下半年' bazi/month → 7 月起 6-7 个月（含 partial）")
    r = resolve_calendar("下半年", base_date=BASE, view="bazi", granularity="month")
    if not assert_range(r, "2026-07-01", "2026-12-31", "7 月起"):
        failed += 1
    # 7/1 不是节气日，会有一个 partial 月（甲午月部分）+ 6 个完整节气月
    if not assert_period_count(r, 7, "6-7 个流月", tolerance=1):
        failed += 1

    # 4. "未来 12 个月"
    print("\n[4] '未来12个月' bazi/month → 滚动 12 月")
    r = resolve_calendar("未来12个月", base_date=BASE, view="bazi", granularity="month")
    g = r["resolved"]["gregorian"]
    if not (g[0] == "2026-04-25" and g[1].startswith("2027-04")):
        print(f"  ❌ 范围错: {g}")
        failed += 1
    else:
        print(f"  ✅ 范围: {g}")
    if not assert_period_count(r, 12, "12 个流月", tolerance=2):
        failed += 1

    # 5. "农历三月" bazi → 公历 4/17 ~ 5/16，含月柱壬辰
    print("\n[5] '农历三月' bazi → 公历 4/17 ~ 5/16，含月柱壬辰")
    r = resolve_calendar("农历三月", base_date=BASE, view="bazi", granularity="month")
    g = r["resolved"]["gregorian"]
    expect = ("2026-04-17", "2026-05-16")
    if (g[0], g[1]) != expect:
        print(f"  ❌ 范围错: 期望 {expect}，得 {tuple(g)}")
        failed += 1
    else:
        print(f"  ✅ 范围: {g}")
    # 验证 by_period 里有 ganzhi_month=壬辰（农历三月跨立夏，含壬辰+癸巳两段）
    gz_list = [p.get("ganzhi_month") for p in r.get("by_period", [])]
    if "壬辰" not in gz_list:
        print(f"  ❌ 未找到 ganzhi_month=壬辰；实际: {gz_list}")
        failed += 1
    else:
        print(f"  ✅ 月柱壬辰存在；by_period={gz_list}")

    # 6. "明年"
    print("\n[6] '明年' raw/year → 公历 2027 全年")
    r = resolve_calendar("明年", base_date=BASE, view="raw", granularity="year")
    if not assert_range(r, "2027-01-01", "2027-12-31", "明年全年"):
        failed += 1
    if not r.get("ambiguity_note"):
        print(f"  ⚠️  期望 ambiguity_note 提示历法默认值")

    # 7. "明年下半年"
    print("\n[7] '明年下半年' bazi/month → 2027/7 ~ 2027/12")
    r = resolve_calendar("明年下半年", base_date=BASE, view="bazi", granularity="month")
    if not assert_range(r, "2027-07-01", "2027-12-31", "明年下半年"):
        failed += 1

    # 8. "2026 年 5 月到 8 月"
    print("\n[8] '2026年5月到8月' astrology/month → 公历 5/1 ~ 8/31")
    r = resolve_calendar("2026年5月到8月", base_date=BASE, view="astrology", granularity="month")
    if not assert_range(r, "2026-05-01", "2026-08-31", "5 月到 8 月"):
        failed += 1
    if not assert_period_count(r, 4, "4 个公历月", tolerance=0):
        failed += 1

    # 9. "农历五月初五"
    print("\n[9] '农历五月初五' bazi/day → 单日")
    r = resolve_calendar("农历五月初五那天", base_date=BASE, view="bazi", granularity="day")
    g = r["resolved"]["gregorian"]
    if g[0] != g[1]:
        print(f"  ❌ 应为单日，得 {g}")
        failed += 1
    else:
        print(f"  ✅ 单日 {g[0]}")

    # 10. ISO 直传
    print("\n[10] ISO 直传 → 不解析")
    r = resolve_calendar('{"from":"2026-04-25","to":"2026-12-31"}', view="bazi", granularity="month")
    if not assert_range(r, "2026-04-25", "2026-12-31", "ISO 范围"):
        failed += 1

    print("\n" + "=" * 60)
    if failed == 0:
        print(f"✅ 全部通过")
    else:
        print(f"❌ {failed} 个用例失败")
    print("=" * 60)
    return failed


if __name__ == "__main__":
    sys.exit(main())
