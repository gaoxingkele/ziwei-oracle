"""快速测试所有 14 个引擎是否能正常计算（不依赖 HTTP 服务）"""
import asyncio
import importlib
import traceback

# 注册所有引擎
for mod in [
    "app.engine.ziwei", "app.engine.meihua", "app.engine.liuyao",
    "app.engine.astrology", "app.engine.bazi", "app.engine.qimen",
    "app.engine.liuren", "app.engine.iching", "app.engine.qianwen",
    "app.engine.jiemeng", "app.engine.name_analysis", "app.engine.hehun",
    "app.engine.almanac", "app.engine.jiri",
]:
    importlib.import_module(mod)

from app.engine.registry import ChartRequest, calculate, list_systems

# 每个引擎的测试参数
TEST_CASES = {
    "ziwei": {
        "name": "测试用户", "birth_date": "1990-05-15",
        "birth_time": "6", "gender": "男",
    },
    "bazi": {
        "name": "测试用户", "birth_date": "1990-05-15",
        "birth_time": "6", "gender": "男",
    },
    "almanac": {
        "name": "查询", "birth_date": "2026-04-01",
        "birth_time": "0", "gender": "男",
    },
    "meihua": {
        "name": "测试用户", "birth_date": "2026-04-01",
        "birth_time": "6", "gender": "男", "question": "事业运势如何",
    },
    "liuyao": {
        "name": "测试用户", "birth_date": "2026-04-01",
        "birth_time": "6", "gender": "男", "question": "财运如何",
        "extra": {"yao_codes": [2, 2, 1, 2, 4, 2]},
    },
    "astrology": {
        "name": "测试用户", "birth_date": "1990-05-15",
        "birth_time": "6", "gender": "男",
    },
    "qimen": {
        "name": "测试用户", "birth_date": "2026-04-01",
        "birth_time": "6", "gender": "男",
    },
    "liuren": {
        "name": "测试用户", "birth_date": "2025-03-15",
        "birth_time": "6", "gender": "男",
    },
    "iching": {
        "name": "测试用户", "birth_date": "2026-04-01",
        "birth_time": "6", "gender": "男", "question": "问前程",
    },
    "qianwen": {
        "name": "测试用户", "birth_date": "2026-04-01",
        "birth_time": "0", "gender": "男",
        "extra": {"type": "guanyin"},
    },
    "jiemeng": {
        "name": "测试用户", "birth_date": "2026-04-01",
        "birth_time": "0", "gender": "男",
        "question": "蛇",
    },
    "name_analysis": {
        "name": "张三丰", "birth_date": "1990-05-15",
        "birth_time": "6", "gender": "男",
    },
    "hehun": {
        "name": "男方", "birth_date": "1990-05-15",
        "birth_time": "6", "gender": "男",
        "extra": {
            "spouse_birth_date": "1992-08-20",
            "spouse_birth_time": "3",
            "spouse_gender": "女",
        },
    },
    "jiri": {
        "name": "吉日查询", "birth_date": "2026-04-01",
        "birth_time": "0", "gender": "男",
        "question": "结婚",
        "extra": {"start_date": "2026-04-01", "end_date": "2026-05-01"},
    },
}


async def main():
    systems = list_systems()
    print(f"已注册引擎: {systems}\n")

    passed, failed = [], []
    for system in sorted(TEST_CASES.keys()):
        params = TEST_CASES[system]
        req = ChartRequest(system=system, **params)
        try:
            result = await calculate(req)
            summary_preview = result.text_summary[:120].replace("\n", " ")
            print(f"  [OK] {system:16s}  chart_id={result.chart_id}  summary={summary_preview}...")
            passed.append(system)
        except Exception as e:
            print(f"  [FAIL] {system:16s}  ERROR: {e}")
            traceback.print_exc()
            failed.append(system)

    print(f"\n{'='*60}")
    print(f"通过: {len(passed)}/{len(TEST_CASES)}  失败: {len(failed)}/{len(TEST_CASES)}")
    if failed:
        print(f"失败引擎: {failed}")


if __name__ == "__main__":
    asyncio.run(main())
