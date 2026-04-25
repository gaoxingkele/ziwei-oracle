"""bazi_period 冒烟测试。"""
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from app.engine.bazi_period import calculate_bazi_period

# 测试 profile：1995-03-03 14:03 男（与 ziwei 测试一致）
profile = {
    "device_id": "test_dev_xx",
    "birthday": "1995-03-03",
    "birthtime": "14:03",
    "sex": "1",
}

print("=" * 60)
print("bazi_period 冒烟测试")
print("=" * 60)

# 1. 今年下半年
print("\n[1] expr='今年下半年' month")
r = calculate_bazi_period(profile, "今年下半年", base_date="2026-04-25", granularity="month")
if "error" in r:
    print(f"  ❌ {r}")
else:
    n = r["natal_recap"]
    print(f"  ✅ natal: 四柱 {n['year_gz']}/{n['month_gz']}/{n['day_gz']}/{n['hour_gz']} 日主={n['day_master']}")
    print(f"     用神={n['yong_shen']} 忌神={n['ji_shen']}")
    print(f"     resolved: {r['resolved']['gregorian']}")
    print(f"     by_period: {len(r['by_period'])} 项")
    for p in r["by_period"][:3]:
        print(f"     {p['solar_range']} {p['ganzhi_month']} 干十神={p['ten_god_to_day_gan']} 支十神={p['ten_god_to_day_zhi']}")
        if p['interactions_with_natal']:
            print(f"       关系: {p['interactions_with_natal']}")
        print(f"       五行delta={p['wuxing_delta']} 用神状态={p['yong_shen_status']}")

# 2. 农历三月（v1 文档里 LLM 误判的关键 case）
print("\n[2] expr='农历三月' month — 关键回归 case")
r = calculate_bazi_period(profile, "农历三月", base_date="2026-04-25", granularity="month")
if "error" in r:
    print(f"  ❌ {r}")
else:
    bp = r["by_period"]
    gz_list = [p["ganzhi_month"] for p in bp]
    print(f"  ✅ 范围 {r['resolved']['gregorian']}")
    print(f"     by_period 月柱={gz_list}（应为 ['壬辰', '癸巳']，不是 'LLM 误判的壬午'）")
    for p in bp:
        print(f"     {p['ganzhi_month']}: 干十神={p['ten_god_to_day_gan']} 关系={p['interactions_with_natal']}")

# 3. 今年（year 粒度）
print("\n[3] expr='今年' year")
r = calculate_bazi_period(profile, "今年", base_date="2026-04-25", granularity="year")
if "error" in r:
    print(f"  ❌ {r}")
else:
    print(f"  ✅ {r['resolved']['gregorian']} bp={len(r['by_period'])}")
    if r["by_period"]:
        p = r["by_period"][0]
        print(f"     流年干支={p['ganzhi_month']} 干十神={p['ten_god_to_day_gan']}")

# 4. 不完整 profile
print("\n[4] 不完整 profile")
r = calculate_bazi_period({"device_id": "x", "birthday": None, "birthtime": None, "sex": None}, "今年")
if r.get("error") == "profile_incomplete":
    print(f"  ✅ 正确报错")
else:
    print(f"  ❌ 期望 profile_incomplete，得 {r}")

print("\n" + "=" * 60)
print("DONE")
