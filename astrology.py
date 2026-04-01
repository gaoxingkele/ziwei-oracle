from __future__ import annotations

from pathlib import Path

from config import ASTRO_CITY, ASTRO_LAT, ASTRO_LNG, ASTRO_NATION, ASTRO_TZ_STR

# 与紫微时辰序号保持一致（0~12）
_TIME_MAP: dict[int, tuple[int, int]] = {
    0: (0, 30),   # 早子
    1: (1, 30),   # 丑
    2: (3, 30),   # 寅
    3: (5, 30),   # 卯
    4: (7, 30),   # 辰
    5: (9, 30),   # 巳
    6: (11, 30),  # 午
    7: (13, 30),  # 未
    8: (15, 30),  # 申
    9: (17, 30),  # 酉
    10: (19, 30), # 戌
    11: (21, 30), # 亥
    12: (23, 30), # 晚子
}


def _safe_filename(s: str, max_len: int = 120) -> str:
    s = (s or "").strip()
    for c in r'\/:*?"<>|':
        s = s.replace(c, "_")
    s = s.strip(".") or "unnamed"
    return s[:max_len] if len(s) > max_len else s


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


def build_astrology_context_text(subject: object) -> str:
    raw_json = ""
    try:
        raw_json = subject.model_dump_json(indent=2)  # type: ignore[attr-defined]
    except Exception:
        raw_json = ""
    if len(raw_json) > 4000:
        raw_json = raw_json[:4000] + "\n...（节选）"

    lines = [
        "【西方星相学关键位】",
        _point_summary(subject, "sun", "太阳"),
        _point_summary(subject, "moon", "月亮"),
        _point_summary(subject, "ascendant", "上升"),
        _point_summary(subject, "mercury", "水星"),
        _point_summary(subject, "venus", "金星"),
        _point_summary(subject, "mars", "火星"),
        _point_summary(subject, "jupiter", "木星"),
        _point_summary(subject, "saturn", "土星"),
    ]
    if raw_json:
        lines.extend(
            [
                "",
                "【kerykeion 结构化数据（JSON 节选）】",
                raw_json,
            ]
        )
    return "\n".join(lines)


def generate_kerykeion_chart_and_text(
    *,
    name: str,
    date_str: str,
    time_index: int,
    gender: str,
    output_dir: str,
    file_base: str,
) -> tuple[str, str, str]:
    """
    基于 kerykeion 生成本命盘 SVG 与文本摘要。
    返回: (md_path, svg_path, context_text)
    """
    try:
        from kerykeion import AstrologicalSubjectFactory
        from kerykeion.chart_data_factory import ChartDataFactory
        from kerykeion.charts.chart_drawer import ChartDrawer
    except Exception as e:
        raise RuntimeError("请先安装 kerykeion: pip install kerykeion") from e

    parts = date_str.split("-")
    if len(parts) != 3:
        raise ValueError(f"日期格式无效: {date_str}")
    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
    hour, minute = _TIME_MAP.get(time_index, (11, 30))

    subject = AstrologicalSubjectFactory.from_birth_data(
        name=name,
        year=year,
        month=month,
        day=day,
        hour=hour,
        minute=minute,
        city=ASTRO_CITY,
        nation=ASTRO_NATION,
        lng=ASTRO_LNG,
        lat=ASTRO_LAT,
        tz_str=ASTRO_TZ_STR,
        online=False,
    )

    chart_data = ChartDataFactory.create_natal_chart_data(subject)
    drawer = ChartDrawer(chart_data=chart_data)

    out_dir = Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_base = _safe_filename(file_base)
    svg_name = f"{safe_base}_kerykeion"
    drawer.save_svg(output_path=out_dir, filename=svg_name)
    svg_path = str((out_dir / f"{svg_name}.svg").resolve())

    context_text = build_astrology_context_text(subject)
    md_path_obj = out_dir / f"{safe_base}_kerykeion.md"
    md_content = "\n".join(
        [
            "# 西方星相学排盘（kerykeion）",
            "",
            f"- 姓名: {name}",
            f"- 生日: {date_str}",
            f"- 时辰序号: {time_index}",
            f"- 性别: {gender}",
            f"- 位置: {ASTRO_CITY}/{ASTRO_NATION} ({ASTRO_LNG}, {ASTRO_LAT}) {ASTRO_TZ_STR}",
            "",
            context_text,
        ]
    )
    md_path_obj.write_text(md_content, encoding="utf-8")
    return str(md_path_obj.resolve()), svg_path, context_text
