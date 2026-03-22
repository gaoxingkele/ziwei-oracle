from __future__ import annotations

SHICHEN_NAMES = "早子 丑 寅 卯 辰 巳 午 未 申 酉 戌 亥 晚子".split()

TIME_MAP: dict[int, tuple[int, int]] = {
    0: (0, 30), 1: (1, 30), 2: (3, 30), 3: (5, 30),
    4: (7, 30), 5: (9, 30), 6: (11, 30), 7: (13, 30),
    8: (15, 30), 9: (17, 30), 10: (19, 30), 11: (21, 30),
    12: (23, 30),
}

def parse_shichen(raw: str) -> int | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    if raw in SHICHEN_NAMES:
        return SHICHEN_NAMES.index(raw)
    try:
        idx = int(raw)
        if 0 <= idx <= 12:
            return idx
    except ValueError:
        pass
    return None

def safe_filename(s: str, max_len: int = 120) -> str:
    s = (s or "").strip()
    for c in r'\/:*?"<>|':
        s = s.replace(c, "_")
    s = s.strip(".") or "unnamed"
    return s[:max_len] if len(s) > max_len else s
