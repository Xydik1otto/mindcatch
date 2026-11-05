"""Focus statistics: pomodoro/focus minutes per day from time_logs, as SVG bars.

Pure functions — the date range is injectable so tests don't depend on the
clock. An open (running) timer contributes nothing until it is closed.
"""

from __future__ import annotations

from datetime import date, timedelta

ACCENT = "#7c6cff"
MUTED = "#8b95a5"


def minutes_by_day(logs: list[dict], days: int = 7, today: date | None = None) -> list[dict]:
    """Minutes of closed focus sessions per calendar day for the last ``days`` days."""
    today = today or date.today()
    start = today - timedelta(days=days - 1)
    totals = {(start + timedelta(days=i)).isoformat(): 0 for i in range(days)}
    for log in logs:
        if log.get("ended_at") is None:
            continue  # still running — not finished focus yet
        day = (log.get("started_at") or "")[:10]
        if day in totals:
            totals[day] += int(log.get("minutes") or 0)
    return [{"date": d, "minutes": m} for d, m in totals.items()]


def total_minutes(bars: list[dict]) -> int:
    return sum(b["minutes"] for b in bars)


def bar_chart_svg(bars: list[dict], width: int = 504, height: int = 180) -> str:
    """Simple SVG bar chart: one bar per day, date labels + minute values."""
    n = max(len(bars), 1)
    pad_l, pad_b, pad_t = 6, 22, 18
    chart_h = height - pad_b - pad_t
    slot = (width - pad_l * 2) / n
    bar_w = min(slot * 0.62, 48)
    peak = max([b["minutes"] for b in bars], default=0) or 1
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="Фокус-хвилини за день">',
        f'<line x1="{pad_l}" y1="{height - pad_b}" x2="{width - pad_l}" '
        f'y2="{height - pad_b}" stroke="{MUTED}" stroke-width="1"/>',
    ]
    for i, b in enumerate(bars):
        x = pad_l + i * slot + (slot - bar_w) / 2
        h = round(chart_h * b["minutes"] / peak) if b["minutes"] else 0
        y = height - pad_b - h
        if h:
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h}" '
                f'rx="4" fill="{ACCENT}"><title>{b["date"]}: {b["minutes"]} хв</title></rect>')
            parts.append(
                f'<text x="{x + bar_w / 2:.1f}" y="{y - 4:.1f}" font-size="10" '
                f'fill="{MUTED}" text-anchor="middle">{b["minutes"]}</text>')
        dd = b["date"][8:10] + "." + b["date"][5:7]
        parts.append(
            f'<text x="{x + bar_w / 2:.1f}" y="{height - 7}" font-size="10" '
            f'fill="{MUTED}" text-anchor="middle">{dd}</text>')
    parts.append("</svg>")
    return "".join(parts)
