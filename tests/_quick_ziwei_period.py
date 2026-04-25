"""ziwei_period 快速冒烟测试。"""
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from app.engine.ziwei_period import calculate_ziwei_period

# 测试 profile（与对话里使用的设备一致：1995-03-03 14:03 男）
profile = {
    "device_id": "test_dev_xx",
    "name": "测试",
    "birthday": "1995-03-03",
    "birthtime": "14:03",
    "sex": "1",  # 男
    "city": "福州",
}

print("=" * 60)
print("ziwei_period 冒烟测试")
print("=" * 60)

# 1. 今年下半年（month）
print("\n[1] expr='今年下半年' month")
r = calculate_ziwei_period(profile, "今年下半年", base_date="2026-04-25", granularity="month")
if "error" in r:
    print(f"  ❌ {r}")
else:
    print(f"  ✅ natal_recap: 命宫={r['natal_recap']['ming_gong']} 五行局={r['natal_recap']['wu_xing_ju']}")
    print(f"     resolved: {r['resolved']['gregorian']}")
    print(f"     by_period: {len(r['by_period'])} 项")
    for p in r["by_period"][:3]:
        m = p.get("monthly", {})
        y = p.get("yearly", {})
        print(f"     {p['solar_range']} 农历{p.get('lunar_range')} 流月={m.get('stem_branch')}@{m.get('palace')} 流月四化={m.get('mutagen')}")

# 2. 今年（year 粒度，仅大限+流年）
print("\n[2] expr='今年' year")
r = calculate_ziwei_period(profile, "今年", base_date="2026-04-25", granularity="year")
if "error" in r:
    print(f"  ❌ {r}")
else:
    print(f"  ✅ resolved: {r['resolved']['gregorian']} bp={len(r['by_period'])}")

# 3. 农历三月（month 粒度）
print("\n[3] expr='农历三月' month")
r = calculate_ziwei_period(profile, "农历三月", base_date="2026-04-25", granularity="month")
if "error" in r:
    print(f"  ❌ {r}")
else:
    bp = r["by_period"]
    print(f"  ✅ bp={len(bp)} 项；范围 {r['resolved']['gregorian']}")
    if bp:
        m = bp[0].get("monthly", {})
        print(f"     流月={m.get('stem_branch')}@{m.get('palace')} 化={m.get('mutagen')}")

# 4. 不完整 profile
print("\n[4] 不完整 profile")
r = calculate_ziwei_period({"device_id": "x", "birthday": None, "birthtime": None, "sex": None}, "今年")
if r.get("error") == "profile_incomplete":
    print(f"  ✅ 正确报错: {r['hint']}")
else:
    print(f"  ❌ 期望 profile_incomplete，得 {r}")

print("\n" + "=" * 60)
print("DONE")
