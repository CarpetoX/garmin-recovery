#!/usr/bin/env python3
"""Descarga wellness de Intervals.icu (90 días) y escribe wellness.json y recovery.csv.

Extraído sin cambios del paso inline "Obtener wellness de Intervals.icu" de .github/workflows/sync.yml (V5.9).
Necesita INTERVALS_API_KEY en el entorno.
"""
import os, json, csv, base64, urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

key = os.environ["INTERVALS_API_KEY"]
today = datetime.now(ZoneInfo("Europe/Madrid")).date()
newest = today
oldest = newest - timedelta(days=90)

url = (
    "https://intervals.icu/api/v1/athlete/0/wellness"
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
    data = json.loads(body) if body else []

if not isinstance(data, list) or not data:
    raise RuntimeError("Intervals.icu devolvió wellness vacío; no se sobrescriben los datos previos")

with open("wellness.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

fields = [
    "date", "hrv", "hrvSDNN", "restingHR",
    "sleepSecs", "sleepHours", "sleepScore", "sleepQuality",
    "avgSleepingHR", "spO2", "readiness", "weight", "vo2max",
    "ctl", "atl", "ctlLoad", "atlLoad", "rampRate",
    "steps", "floorsClimbed", "respiration",
    "stress", "fatigue", "soreness", "mood", "motivation",
    "hydration", "hydrationVolume", "updated"
]

with open("recovery.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for x in data:
        sleep_secs = x.get("sleepSecs")
        sleep_hours = round(sleep_secs / 3600, 2) if isinstance(sleep_secs, (int, float)) else ""
        w.writerow({
            "date": x.get("id", ""),
            "hrv": x.get("hrv", ""),
            "hrvSDNN": x.get("hrvSDNN", ""),
            "restingHR": x.get("restingHR", ""),
            "sleepSecs": sleep_secs if sleep_secs is not None else "",
            "sleepHours": sleep_hours,
            "sleepScore": x.get("sleepScore", ""),
            "sleepQuality": x.get("sleepQuality", ""),
            "avgSleepingHR": x.get("avgSleepingHR", ""),
            "spO2": x.get("spO2", ""),
            "readiness": x.get("readiness", ""),
            "weight": x.get("weight", ""),
            "vo2max": x.get("vo2max", ""),
            "ctl": x.get("ctl", ""),
            "atl": x.get("atl", ""),
            "ctlLoad": x.get("ctlLoad", ""),
            "atlLoad": x.get("atlLoad", ""),
            "rampRate": x.get("rampRate", ""),
            "steps": x.get("steps", ""),
            "floorsClimbed": x.get("floorsClimbed", ""),
            "respiration": x.get("respiration", ""),
            "stress": x.get("stress", ""),
            "fatigue": x.get("fatigue", ""),
            "soreness": x.get("soreness", ""),
            "mood": x.get("mood", ""),
            "motivation": x.get("motivation", ""),
            "hydration": x.get("hydration", ""),
            "hydrationVolume": x.get("hydrationVolume", ""),
            "updated": x.get("updated", "")
        })
