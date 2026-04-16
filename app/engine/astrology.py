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
    lines = ["【西方星相学关键位】"]
    for attr, label in [
        ("sun", "太阳"), ("moon", "月亮"), ("ascendant", "上升"),
        ("mercury", "水星"), ("venus", "金星"), ("mars", "火星"),
        ("jupiter", "木星"), ("saturn", "土星"),
    ]:
        lines.append(_point_summary(subject, attr, label))
    text = "\n".join(lines)
    raw = {}
    try:
        raw = subject.model_dump(mode="json")
    except Exception:
        pass
    return ChartResult(
        chart_id=f"ch_{uuid.uuid4().hex[:12]}",
        system="astrology", raw_data=raw, text_summary=text,
    )
