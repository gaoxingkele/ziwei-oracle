"""astrology_period 冒烟测试。"""
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from app.engine.astrology_period import calculate_astrology_period

try:
    import kerykeion as _ker
    HAS_KER = True
except ImportError:
    HAS_KER = False

profile = {
    "device_id": "test_dev_xx",
    "name": "测试",
    "birthday": "1995-03-03",
    "birthtime": "14:03",
    "sex": "1",
    "city": "Beijing",
}

print("=" * 60)
print(f"astrology_period 冒烟测试 (kerykeion {'已装' if HAS_KER else '未装'})")
print("=" * 60)

# 1. 今年下半年
print("\n[1] expr='今年下半年' month")
r = calculate_astrology_period(profile, "今年下半年", base_date="2026-04-25", granularity="month")
if not HAS_KER:
    if r.get("error") == "kerykeion_missing":
        print(f"  ✅ 正确报告 kerykeion_missing（本机依赖跳过策略下的预期行为）")
    else:
        print(f"  ❌ 期望 kerykeion_missing，得 {r}")
elif "error" in r:
    print(f"  ❌ {r}")
else:
    print(f"  ✅ natal_recap 行星数: {len(r['natal_recap'])}")
    for k, v in list(r["natal_recap"].items())[:4]:
        print(f"     {v.get('label')}: {v.get('sign')} {v.get('degree','')}°")
    print(f"     resolved: {r['resolved']['gregorian']}")
    print(f"     by_period: {len(r['by_period'])} 项")
    for p in r["by_period"][:3]:
        print(f"     {p['solar_range']} → {p['month_label']} (partial={p['is_partial']})")
    print(f"     scope_note 长度: {len(r.get('scope_note', ''))} chars")

# 2. profile 不完整
print("\n[2] 不完整 profile")
r = calculate_astrology_period({"device_id": "x", "birthday": None}, "今年")
if r.get("error") == "profile_incomplete":
    print(f"  ✅ 正确报错")
else:
    print(f"  ❌ 期望 profile_incomplete，得 {r}")

print("\n" + "=" * 60)
print("DONE")
