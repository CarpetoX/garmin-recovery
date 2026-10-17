"""Lectura tolerante de las fuentes que publica la cadena existente."""
from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SOURCE_FILES = {
    "wellness": ("wellness.json", list),
    "hrv": ("garmin_hrv_timeline.json", dict),
    "sleep": ("garmin_sleep_history.json", dict),
    "extended": ("garmin_extended.json", dict),
    "heart": ("garmin_heart_rate.json", dict),
    "stress": ("garmin_stress.json", dict),
    "battery": ("garmin_body_battery.json", dict),
    "activities": ("activities.json", list),
    "feedback": ("training_feedback.json", dict),
    "shifts": ("shift_calendar.json", dict),
    "morning": ("morning_sleep_status.json", dict),
    "legacy_recovery": ("recovery_assessment.json", dict),
    "report_ready": ("report_ready.json", dict),
    "hr_timeline": ("garmin_hr_timeline.json", dict),
    "daily_summary": ("daily_summary.json", dict),
    "workflow_health": ("workflow_health.json", dict),
    "recovery_csv": ("recovery.csv", list),
}


def read_json(path: Path, expected: type):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, expected) else expected()
    except (OSError, ValueError):
        return expected()


def read_csv(path: Path) -> list[dict]:
    try:
        with path.open(encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))
    except OSError:
        return []


def load_inputs(root: str | Path = ".") -> dict:
    root = Path(root)
    inputs: dict = {}
    for key, (name, expected) in SOURCE_FILES.items():
        path = root / name
        inputs[key] = read_csv(path) if name.endswith(".csv") else read_json(path, expected)
    if not inputs["activities"]:
        inputs["activities"] = read_csv(root / "activities.csv")
    return inputs


def parse_dt(value, tz: ZoneInfo) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return datetime.fromtimestamp(value / 1000 if value > 1e11 else value, tz)
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.replace(tzinfo=tz) if parsed.tzinfo is None else parsed.astimezone(tz)
    except (ValueError, TypeError, OverflowError, OSError):
        return None
