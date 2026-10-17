"""Registro diario canónico y sesiones normalizadas.

La fusión fisiológica (HRV, sueño, FC en reposo, FC nocturna) reutiliza
``recovery_reliability.nightly_rows`` para que la app y la cadena existente
usen exactamente las mismas prioridades de fuente. Aquí solo se añaden los
campos que el modelo v3 necesita (carga, estrés, subjetivo, turnos…).
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from .stats import finite

# Campos persistidos en history/daily.csv (orden estable = diffs legibles)
DAILY_FIELDS = [
    "date", "hrv_ms", "resting_hr", "night_hr", "sleep_hours", "sleep_score",
    "deep_min", "rem_min", "awake_min", "spo2", "respiration",
    "sleep_context", "sleep_start_local", "sleep_end_local",
    "stress_avg", "body_battery_high", "body_battery_low",
    "garmin_readiness", "garmin_recovery_hours", "garmin_hrv_status",
    "icu_ctl", "icu_atl", "icu_ramp",
    "soreness", "fatigue", "stress_subjective", "mood", "motivation",
    "weight_kg", "vo2max",
    "sessions", "duration_min", "load", "srpe", "rpe_sessions",
    "shift", "sources",
    # V5.3: puntuaciones de cada modelo y decisión operativa del día (para su histórico)
    "v2_score", "hybrid_score", "v3_score", "decision_zone",
]

SESSION_FIELDS = [
    "id", "date", "start_local", "type", "name", "label",
    "duration_min", "load", "trimp", "avg_hr", "max_hr", "rpe", "srpe",
]

TEXT_FIELDS = {"date", "sleep_context", "sleep_start_local", "sleep_end_local",
               "garmin_hrv_status", "shift", "sources", "decision_zone",
               "id", "start_local", "type", "name", "label"}


def num(value, low=None, high=None):
    vals = finite([value])
    if not vals:
        return None
    v = vals[0]
    if (low is not None and v < low) or (high is not None and v > high):
        return None
    return v


def _days(source) -> dict:
    days = source.get("days") if isinstance(source, dict) else None
    return days if isinstance(days, dict) else {}


def _battery_range(row: dict):
    values = row.get("bodyBatteryValuesArray") if isinstance(row, dict) else None
    levels = []
    for item in values or []:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            level = num(item[1], 0, 100)
            if level is not None:
                levels.append(level)
    return (max(levels), min(levels)) if levels else (None, None)


def build_sessions(inputs: dict) -> list[dict]:
    feedback = (inputs.get("feedback") or {}).get("activities") or {}
    if not isinstance(feedback, dict):
        feedback = {}
    sessions = []
    for act in inputs.get("activities") or []:
        if not isinstance(act, dict) or not act.get("id"):
            continue
        start = str(act.get("start_date_local") or "")
        day = str(act.get("date") or start[:10])
        if len(day) != 10:
            continue
        seconds = num(act.get("moving_time"), 0, 86400) or num(act.get("elapsed_time"), 0, 86400)
        minutes = round(seconds / 60, 1) if seconds else None
        fb = feedback.get(str(act["id"])) or {}
        rpe = num(fb.get("rpe"), 0, 10)
        if rpe is None:
            rpe = num(act.get("icu_rpe"), 0, 10)
        srpe = round(rpe * minutes, 1) if rpe is not None and minutes else None
        sessions.append({
            "id": str(act["id"]), "date": day, "start_local": start or None,
            "type": act.get("type"), "name": act.get("name"),
            "label": fb.get("activity") or None,
            "duration_min": minutes,
            "load": num(act.get("icu_training_load"), 0, 2000),
            "trimp": num(act.get("trimp"), 0, 2000),
            "avg_hr": num(act.get("average_heartrate"), 30, 230),
            "max_hr": num(act.get("max_heartrate"), 30, 240),
            "rpe": rpe, "srpe": srpe,
        })
    sessions.sort(key=lambda s: (s["date"], s["start_local"] or ""))
    return sessions


def aggregate_sessions(sessions) -> dict:
    by_day: dict = defaultdict(lambda: {"sessions": 0, "duration_min": 0.0, "load": 0.0,
                                        "srpe": 0.0, "rpe_sessions": 0})
    for s in sessions:
        d = by_day[s["date"]]
        d["sessions"] += 1
        d["duration_min"] += s.get("duration_min") or 0.0
        d["load"] += s.get("load") or 0.0
        if s.get("srpe") is not None:
            d["srpe"] += s["srpe"]
            d["rpe_sessions"] += 1
    for d in by_day.values():
        d["duration_min"] = round(d["duration_min"], 1)
        d["load"] = round(d["load"], 1)
        d["srpe"] = round(d["srpe"], 1) if d["rpe_sessions"] else None
    return dict(by_day)


def build_day_records(inputs: dict, now: datetime, sessions: list[dict] | None = None) -> dict:
    """Devuelve {fecha: registro} para los últimos 60 días con cualquier dato."""
    from recovery_reliability import nightly_rows  # misma fusión que la cadena

    base = nightly_rows(inputs.get("wellness") or [], inputs.get("hrv") or {},
                        inputs.get("sleep") or {}, inputs.get("extended") or {},
                        inputs.get("heart") or {}, now)
    wellness = {w.get("id"): w for w in inputs.get("wellness") or [] if isinstance(w, dict)}
    recovery_csv = {row.get("date"): row for row in inputs.get("recovery_csv") or []}
    ext_days = _days(inputs.get("extended"))
    stress_days = _days(inputs.get("stress"))
    battery_days = _days(inputs.get("battery"))
    shift_days = (inputs.get("shifts") or {}).get("days") or {}
    load_days = aggregate_sessions(sessions if sessions is not None else build_sessions(inputs))

    records = {}
    for day, row in base.items():
        ext = ext_days.get(day) or {}
        ready = ext.get("training_readiness") or {}
        sleep_detail = ext.get("sleep_detail") or {}
        hrv_status = ext.get("hrv_status") or {}
        w = wellness.get(day) or {}
        rc = recovery_csv.get(day) or {}
        stress = stress_days.get(day) or {}
        bb_high, bb_low = _battery_range(battery_days.get(day) or {})
        load = load_days.get(day) or {}
        rec = {
            "date": day,
            "hrv_ms": row.get("hrv_ms"), "resting_hr": row.get("resting_hr"),
            "night_hr": row.get("night_hr"), "sleep_hours": row.get("sleep_hours"),
            "sleep_score": row.get("sleep_score"),
            "deep_min": num(sleep_detail.get("deep_minutes"), 0, 900),
            "rem_min": num(sleep_detail.get("rem_minutes"), 0, 900),
            "awake_min": num(sleep_detail.get("awake_minutes"), 0, 900),
            "spo2": num(sleep_detail.get("avg_spo2"), 70, 100) or num(w.get("spO2"), 70, 100),
            "respiration": num(sleep_detail.get("avg_respiration"), 4, 40),
            "sleep_context": row.get("sleep_context"),
            "sleep_start_local": row.get("sleep_start_local"),
            "sleep_end_local": row.get("sleep_end_local"),
            "stress_avg": num(stress.get("avgStressLevel"), 0, 100),
            "body_battery_high": bb_high, "body_battery_low": bb_low,
            "garmin_readiness": num(ready.get("score"), 0, 100),
            "garmin_recovery_hours": num(ready.get("recovery_time_hours"), 0, 200),
            "garmin_hrv_status": hrv_status.get("status") or None,
            "icu_ctl": num(w.get("ctl"), 0, 300), "icu_atl": num(w.get("atl"), 0, 400),
            "icu_ramp": num(w.get("rampRate"), -100, 100),
            # Intervals.icu: escala 1 (mejor) – 4 (peor) en los cinco campos
            "soreness": num(w.get("soreness"), 1, 4), "fatigue": num(w.get("fatigue"), 1, 4),
            "stress_subjective": num(w.get("stress"), 1, 4), "mood": num(w.get("mood"), 1, 4),
            "motivation": num(w.get("motivation"), 1, 4),
            "weight_kg": num(w.get("weight"), 30, 250),
            "vo2max": num(w.get("vo2max"), 10, 95) or num(rc.get("vo2max"), 10, 95),
            "sessions": load.get("sessions"), "duration_min": load.get("duration_min"),
            "load": load.get("load"), "srpe": load.get("srpe"),
            "rpe_sessions": load.get("rpe_sessions"),
            "shift": shift_days.get(day) or None,
            "sources": "|".join(f"{k}:{v}" for k, v in sorted((row.get("sources") or {}).items()) if v) or None,
        }
        if any(rec.get(k) is not None for k in DAILY_FIELDS if k not in ("date", "shift", "sources")):
            records[day] = rec
    return records


def date_range(end: str, days: int) -> list[str]:
    last = datetime.fromisoformat(end).date()
    return [(last - timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]
