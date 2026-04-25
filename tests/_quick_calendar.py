"""快速调试：每个 case 单独运行，立即 flush 输出。"""
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from app.engine.calendar import resolve_calendar


def run(label, **kwargs):
    t = time.time()
    try:
        r = resolve_calendar(base_date="2026-04-25", **kwargs)
        elapsed = time.time() - t
        g = r.get("resolved", {}).get("gregorian", "?")
        bp = len(r.get("by_period", []))
        note = r.get("ambiguity_note", "")
        print(f"[{elapsed:5.2f}s] {label}: {g} bp={bp}", flush=True)
        if note:
            print(f"         note: {note}", flush=True)
    except Exception as e:
        elapsed = time.time() - t
        print(f"[{elapsed:5.2f}s] {label}: ERROR {e}", flush=True)


cases = [
    ("c1 今年 raw/year",         dict(expr="今年", view="raw", granularity="year")),
    ("c2 今年接下来 bazi/month", dict(expr="今年接下来", view="bazi", granularity="month")),
    ("c3 下半年 bazi/month",      dict(expr="下半年", view="bazi", granularity="month")),
    ("c4 未来12月 bazi/month",    dict(expr="未来12个月", view="bazi", granularity="month")),
    ("c5 农历三月 bazi/day",      dict(expr="农历三月", view="bazi", granularity="day")),
    ("c6 明年 raw/year",          dict(expr="明年", view="raw", granularity="year")),
    ("c7 明年下半年 bazi/month",  dict(expr="明年下半年", view="bazi", granularity="month")),
    ("c8 5月到8月 astrology",     dict(expr="2026年5月到8月", view="astrology", granularity="month")),
    ("c9 农历五月初五 bazi/day",  dict(expr="农历五月初五那天", view="bazi", granularity="day")),
    ("c10 ISO bazi/month",        dict(expr='{"from":"2026-04-25","to":"2026-12-31"}', view="bazi", granularity="month")),
]

for label, kwargs in cases:
    run(label, **kwargs)
print("DONE", flush=True)
