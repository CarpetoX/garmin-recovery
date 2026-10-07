import json
import math
import sys
from pathlib import Path
from datetime import datetime, timedelta

REQUIRED = [
    Path("daily_summary.json"),
    Path("weekly_summary.json"),
    Path("garmin_heart_rate.json"),
    Path("advanced_analytics.json"),
    Path("data_quality.json"),
]

errors = []
warnings = []
objects = {}

for path in REQUIRED:
    if not path.exists():
        errors.append(f"missing:{path}")
        continue
    try:
        with open(path, encoding="utf-8") as f:
            objects[str(path)] = json.load(f)
    except Exception as exc:
        errors.append(f"invalid_json:{path}:{type(exc).__name__}:{exc}")


def walk(value, path="root"):
    if isinstance(value, dict):
        for k, v in value.items():
            walk(v, f"{path}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            walk(v, f"{path}[{i}]")
    elif isinstance(value, float) and not math.isfinite(value):
        errors.append(f"non_finite:{path}")

for name, obj in objects.items():
    walk(obj, name)

hr = objects.get("garmin_heart_rate.json", {})
if isinstance(hr, dict):
    for ds, row in (hr.get("days") or {}).items():
        if not isinstance(row, dict):
            errors.append(f"hr_day_not_object:{ds}")
            continue
        for key in ("daytime_avg_hr", "nighttime_avg_hr", "resting_hr"):
            value = row.get(key)
            if value is not None and not (20 <= value <= 250):
                errors.append(f"implausible_hr:{ds}:{key}:{value}")
        for key in ("daytime_sample_count", "nighttime_sample_count"):
            value = row.get(key)
            if value is not None and value < 0:
                errors.append(f"negative_sample_count:{ds}:{key}:{value}")

adv = objects.get("advanced_analytics.json", {})
if isinstance(adv, dict):
    for key in ("data_quality", "robust_trends", "baselines_by_context", "personal_recovery_index", "convergence_alert", "weekly_load", "heart_rate_recovery"):
        if key not in adv:
            errors.append(f"advanced_missing_key:{key}")
    q = adv.get("data_quality") or {}
    score = q.get("score") if isinstance(q, dict) else None
    if score is not None and not (0 <= score <= 100):
        errors.append(f"quality_score_out_of_range:{score}")
    pri = adv.get("personal_recovery_index") or {}
    pri_score = pri.get("score") if isinstance(pri, dict) else None
    if pri_score is not None and not (0 <= pri_score <= 100):
        errors.append(f"recovery_index_out_of_range:{pri_score}")

# Structural integration checks.
daily = objects.get("daily_summary.json", {})
weekly = objects.get("weekly_summary.json", {})
if isinstance(daily, dict) and "advanced_analytics" not in daily:
    errors.append("daily_missing_advanced_analytics")
if isinstance(weekly, dict) and "advanced_analytics" not in weekly:
    errors.append("weekly_missing_advanced_analytics")

if errors:
    print(json.dumps({"status": "error", "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2))
    sys.exit(1)

print(json.dumps({"status": "success", "errors": [], "warnings": warnings}, ensure_ascii=False, indent=2))
