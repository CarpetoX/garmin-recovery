"""Constantes y utilidades estadísticas puras del análisis avanzado (sin depender de la hora actual)."""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import math
import statistics


TZ = ZoneInfo("Europe/Madrid")

PATHS = {
    "activities": Path("activities.json"),
    "wellness": Path("wellness.json"),
    "heart_rate": Path("garmin_heart_rate.json"),
    "extended": Path("garmin_extended.json"),
    "stress": Path("garmin_stress.json"),
    "body_battery": Path("garmin_body_battery.json"),
    "daily": Path("daily_summary.json"),
    "weekly": Path("weekly_summary.json"),
    "hrr": Path("activity_hr_recovery.json"),
    "advanced": Path("advanced_analytics.json"),
    "quality": Path("data_quality.json"),
    "context": Path("day_context.json"),
    "feedback": Path("training_feedback.json"),
}

def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, allow_nan=False)

def num(value):
    return (
        float(value)
        if isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        else None
    )

def safe_date(value):
    if isinstance(value, str) and len(value) >= 10:
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except Exception:
            return None
    return None

def parse_dt(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None

def percentile(values, p):
    xs = sorted(v for v in (num(x) for x in values) if v is not None)
    if not xs:
        return None
    if len(xs) == 1:
        return round(xs[0], 2)
    pos = (len(xs) - 1) * p
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return round(xs[lo], 2)
    value = xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)
    return round(value, 2)

def robust_stats(values):
    xs = [v for v in (num(x) for x in values) if v is not None]
    if not xs:
        return {
            "n": 0,
            "median": None,
            "mean": None,
            "p10": None,
            "p90": None,
            "mad": None,
        }

    med = statistics.median(xs)
    mad = statistics.median([abs(x - med) for x in xs])

    return {
        "n": len(xs),
        "median": round(med, 2),
        "mean": round(statistics.fmean(xs), 2),
        "p10": percentile(xs, 0.10),
        "p90": percentile(xs, 0.90),
        "mad": round(mad, 2),
    }

def robust_z(value, stats):
    value = num(value)
    if value is None or not isinstance(stats, dict):
        return None

    med = num(stats.get("median"))
    mad = num(stats.get("mad"))

    if med is None or mad in (None, 0):
        return None

    return round(0.6745 * (value - med) / mad, 2)

def linear_slope(values):
    pts = [(i, num(v)) for i, v in enumerate(values) if num(v) is not None]
    if len(pts) < 3:
        return None

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    xbar = statistics.fmean(xs)
    ybar = statistics.fmean(ys)

    den = sum((x - xbar) ** 2 for x in xs)
    if den == 0:
        return None

    return round(
        sum((x - xbar) * (y - ybar) for x, y in pts) / den,
        3,
    )

METRICS = (
    "hrv",
    "resting_hr",
    "sleep_hours",
    "sleep_score",
    "respiration",
    "daytime_hr",
    "nighttime_hr",
    "stress_avg",
    "body_battery_latest",
)

def pearson(xs, ys):
    pairs = [
        (num(x), num(y))
        for x, y in zip(xs, ys, strict=False)
        if num(x) is not None
        and num(y) is not None
    ]

    if len(pairs) < 4:
        return None

    a = [x for x, _ in pairs]
    b = [y for _, y in pairs]

    am = statistics.fmean(a)
    bm = statistics.fmean(b)

    den = math.sqrt(
        sum((x - am) ** 2 for x in a)
        * sum((y - bm) ** 2 for y in b)
    )

    if den == 0:
        return None

    return round(
        sum(
            (x - am) * (y - bm)
            for x, y in pairs
        )
        / den,
        3,
    )
