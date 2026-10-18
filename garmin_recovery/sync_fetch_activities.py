#!/usr/bin/env python3
"""Descarga actividades de Intervals.icu y escribe activities.json y activities.csv.

Extraído sin cambios del paso inline "Obtener actividades de Intervals.icu" de .github/workflows/sync.yml (V5.9).
Necesita INTERVALS_API_KEY en el entorno.
"""
import os
import json
import csv
import base64
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

key = os.environ["INTERVALS_API_KEY"]
today = datetime.now(ZoneInfo("Europe/Madrid")).date()
newest = today
oldest = newest - timedelta(days=90)

url = (
    "https://intervals.icu/api/v1/athlete/0/activities"
    f"?oldest={oldest.isoformat()}"
    f"&newest={newest.isoformat()}"
)

auth = base64.b64encode(f"API_KEY:{key}".encode()).decode()
req = urllib.request.Request(
    url,
    headers={
        "Authorization": "Basic " + auth,
        "Accept": "application/json",
        "User-Agent": "Garmin-Recovery-Sync/3.1"
    }
)

with urllib.request.urlopen(req, timeout=30) as r:
    body = r.read().decode()
    activities = json.loads(body) if body else []

if not isinstance(activities, list):
    raise RuntimeError("Respuesta de actividades no válida")

with open("activities.json", "w", encoding="utf-8") as f:
    json.dump(activities, f, indent=2, ensure_ascii=False)

fields = [
    "id", "date", "start_date_local", "name", "type",
    "moving_time", "elapsed_time", "recording_time", "distance", "calories",
    "average_heartrate", "max_heartrate", "trimp",
    "icu_training_load", "hr_load", "icu_intensity",
    "icu_ctl", "icu_atl", "lthr", "athlete_max_hr",
    "icu_resting_hr", "icu_weight", "icu_hrr",
    "icu_rpe", "session_rpe", "feel", "device_name", "source",
    "hr_zone_times", "icu_hr_zones", "created", "icu_sync_date"
]

with open("activities.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for x in activities:
        start = x.get("start_date_local", "") or ""
        w.writerow({
            "id": x.get("id", ""),
            "date": start[:10],
            "start_date_local": start,
            "name": x.get("name", ""),
            "type": x.get("type", ""),
            "moving_time": x.get("moving_time", ""),
            "elapsed_time": x.get("elapsed_time", ""),
            "recording_time": x.get("icu_recording_time", ""),
            "distance": x.get("distance", x.get("icu_distance", "")),
            "calories": x.get("calories", ""),
            "average_heartrate": x.get("average_heartrate", ""),
            "max_heartrate": x.get("max_heartrate", ""),
            "trimp": x.get("trimp", ""),
            "icu_training_load": x.get("icu_training_load", ""),
            "hr_load": x.get("hr_load", ""),
            "icu_intensity": x.get("icu_intensity", ""),
            "icu_ctl": x.get("icu_ctl", ""),
            "icu_atl": x.get("icu_atl", ""),
            "lthr": x.get("lthr", ""),
            "athlete_max_hr": x.get("athlete_max_hr", ""),
            "icu_resting_hr": x.get("icu_resting_hr", ""),
            "icu_weight": x.get("icu_weight", ""),
            "icu_hrr": json.dumps(x.get("icu_hrr"), ensure_ascii=False),
            "icu_rpe": x.get("icu_rpe", ""),
            "session_rpe": x.get("session_rpe", ""),
            "feel": x.get("feel", ""),
            "device_name": x.get("device_name", ""),
            "source": x.get("source", ""),
            "hr_zone_times": json.dumps(x.get("icu_hr_zone_times"), ensure_ascii=False),
            "icu_hr_zones": json.dumps(x.get("icu_hr_zones"), ensure_ascii=False),
            "created": x.get("created", ""),
            "icu_sync_date": x.get("icu_sync_date", "")
        })
