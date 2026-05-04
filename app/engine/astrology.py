from __future__ import annotations
import uuid
from app.common.utils import TIME_MAP, parse_shichen
from app.config import ASTRO_CITY, ASTRO_LAT, ASTRO_LNG, ASTRO_NATION, ASTRO_TZ_STR
from app.engine.registry import ChartRequest, ChartResult, register

try:
    from kerykeion import AstrologicalSubjectFactory
except ImportError:
    AstrologicalSubjectFactory = None

def _point_summary(subject: object, attr_name: str, label: str) -> str:
    point = getattr(subject, attr_name, None)
    if point is None:
        return f"- {label}: 无"
    sign = getattr(point, "sign", "") or ""
    house = getattr(point, "house", "") or ""
    position = getattr(point, "position", None)
    pos_text = f"{position:.2f}°" if isinstance(position, (int, float)) else ""
    if house:
        return f"- {label}: {sign} {pos_text}（{house}）".strip()
    return f"- {label}: {sign} {pos_text}".strip()

@register("astrology")
def calculate_astrology_engine(req: ChartRequest) -> ChartResult:
    if AstrologicalSubjectFactory is None:
        raise RuntimeError("请先安装 kerykeion: pip install kerykeion")
    time_idx = parse_shichen(req.birth_time) or 6
    hour, minute = TIME_MAP.get(time_idx, (11, 30))
    parts = req.birth_date.split("-")
    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
    city = (req.extra.get("city") if req.extra else None) or ASTRO_CITY
    subject = AstrologicalSubjectFactory.from_birth_data(
        name=req.name, year=year, month=month, day=day,
        hour=hour, minute=minute,
        city=city, nation=ASTRO_NATION,
        lng=ASTRO_LNG, lat=ASTRO_LAT, tz_str=ASTRO_TZ_STR, online=False,
    )
    raw = {}
    try:
        raw = subject.model_dump(mode="json")
    except Exception:
        pass
    text = _build_astrology_text(subject, raw)
    return ChartResult(
        chart_id=f"ch_{uuid.uuid4().hex[:12]}",
        system="astrology", raw_data=raw, text_summary=text,
    )


def _build_astrology_text(subject: object, raw: dict) -> str:
    lines = ["══════════ 西方星盘 ══════════"]
    # 行星 (主行星 + 外行星)
    lines.append("──── 行星位置 ────")
    for attr, label in [
        ("sun", "太阳"), ("moon", "月亮"), ("ascendant", "上升"), ("medium_coeli", "天顶"),
        ("mercury", "水星"), ("venus", "金星"), ("mars", "火星"),
        ("jupiter", "木星"), ("saturn", "土星"),
        ("uranus", "天王星"), ("neptune", "海王星"), ("pluto", "冥王星"),
        ("mean_node", "北交点"), ("chiron", "凯龙星"),
    ]:
        lines.append(_point_summary(subject, attr, label))

    # 12 宫位 (houses)
    houses = raw.get("houses") or []
    if not houses:
        # 试试 first_house / second_house 这种结构
        houses_alt = []
        for i, name in enumerate([
            "first_house", "second_house", "third_house", "fourth_house",
            "fifth_house", "sixth_house", "seventh_house", "eighth_house",
            "ninth_house", "tenth_house", "eleventh_house", "twelfth_house",
        ], 1):
            h = getattr(subject, name, None)
            if h:
                sign = getattr(h, "sign", "")
                pos = getattr(h, "position", None)
                pos_text = f"{pos:.1f}°" if isinstance(pos, (int, float)) else ""
                houses_alt.append(f"  第{i}宫: {sign} {pos_text}")
        if houses_alt:
            lines.append("")
            lines.append("──── 12 宫位 (宫头星座) ────")
            lines.extend(houses_alt)
    else:
        lines.append("")
        lines.append("──── 12 宫位 (宫头星座) ────")
        for i, h in enumerate(houses, 1):
            sign = h.get("sign", "?")
            pos = h.get("position")
            pos_text = f"{pos:.1f}°" if isinstance(pos, (int, float)) else ""
            lines.append(f"  第{i}宫: {sign} {pos_text}")

    # 相位 (aspects)
    aspects = raw.get("aspects") or []
    if not aspects:
        aspects = getattr(subject, "aspects", None) or []
        try:
            aspects = [a.model_dump() if hasattr(a, "model_dump") else a for a in aspects]
        except Exception:
            aspects = []
    if aspects:
        lines.append("")
        lines.append("──── 主要相位 ────")
        for a in aspects[:15]:  # 限制最多 15 条避免文本过长
            p1 = a.get("p1_name") or a.get("first_planet") or "?"
            p2 = a.get("p2_name") or a.get("second_planet") or "?"
            asp = a.get("aspect") or a.get("aspect_name") or "?"
            orb = a.get("orbit") or a.get("orb")
            orb_text = f" (容许度 {orb:.1f}°)" if isinstance(orb, (int, float)) else ""
            lines.append(f"  {p1} {asp} {p2}{orb_text}")

    return "\n".join(lines)
