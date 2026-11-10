"""Historial de carreras con todo lo que da Garmin (V8.8).

Intervals.icu solo tiene actividades desde el 6/10/2026 y ``garmin_activity_metrics`` solo mira 7 días, así que una
carrera anterior se perdía. Este paso pide a Garmin Connect las carreras de los últimos ``DAYS`` días (una llamada),
guarda todos sus campos útiles y los parciales por km (una llamada por carrera nueva, como mucho ``MAX_SPLIT_CALLS``)
en ``running_history.json``, que se conserva entre ejecuciones. Nunca rompe la cadena: ante cualquier error deja el
historial como estaba y sale con 0.

Las funciones ``summarize_run``, ``summarize_splits`` y ``merge`` son puras (sin red) para poder probarlas.
"""
from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Madrid")
HISTORY = Path("running_history.json")
DAYS = 120
MAX_SPLIT_CALLS = 6
RUN_TYPES = ("running", "trail_running", "treadmill_running", "track_running", "street_running", "virtual_run",
             "indoor_running")

# clave de Garmin → clave propia (unidades en el nombre)
FIELDS = {
    "distance": "distance_m", "duration": "duration_s", "movingDuration": "moving_s", "elapsedDuration": "elapsed_s",
    "averageSpeed": "avg_speed_ms", "maxSpeed": "max_speed_ms", "avgGradeAdjustedSpeed": "gap_speed_ms",
    "averageHR": "avg_hr", "maxHR": "max_hr",
    "averageRunningCadenceInStepsPerMinute": "cadence_spm", "maxRunningCadenceInStepsPerMinute": "max_cadence_spm",
    "steps": "steps", "avgStrideLength": "stride_cm", "avgVerticalOscillation": "vertical_oscillation_cm",
    "avgGroundContactTime": "ground_contact_ms", "avgVerticalRatio": "vertical_ratio_pct",
    "elevationGain": "elev_gain_m", "elevationLoss": "elev_loss_m", "minElevation": "min_elev_m", "maxElevation": "max_elev_m",
    "avgPower": "avg_power_w", "maxPower": "max_power_w", "normPower": "norm_power_w",
    "calories": "calories", "vO2MaxValue": "vo2max",
    "aerobicTrainingEffect": "aerobic_te", "anaerobicTrainingEffect": "anaerobic_te", "activityTrainingLoad": "garmin_load",
    "fastestSplit_1000": "fastest_1k_s", "fastestSplit_1609": "fastest_mile_s", "fastestSplit_5000": "fastest_5k_s",
    "lapCount": "laps", "minTemperature": "min_temp_c", "maxTemperature": "max_temp_c",
    "moderateIntensityMinutes": "moderate_min", "vigorousIntensityMinutes": "vigorous_min",
    "differenceBodyBattery": "body_battery_delta",
}
SPLIT_FIELDS = {
    "distance": "distance_m", "duration": "duration_s", "movingDuration": "moving_s", "averageSpeed": "avg_speed_ms",
    "averageMovingSpeed": "moving_speed_ms", "averageHR": "avg_hr", "maxHR": "max_hr", "averageRunCadence": "cadence_spm",
    "elevationGain": "elev_gain_m", "elevationLoss": "elev_loss_m", "strideLength": "stride_cm",
    "groundContactTime": "ground_contact_ms", "verticalOscillation": "vertical_oscillation_cm", "verticalRatio": "vertical_ratio_pct",
    "averagePower": "avg_power_w",
}


def _num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _type_key(raw: dict) -> str:
    t = raw.get("activityType") or {}
    return str(t.get("typeKey") if isinstance(t, dict) else t or "")


def is_run(raw) -> bool:
    return isinstance(raw, dict) and (_type_key(raw) in RUN_TYPES or "running" in _type_key(raw))


def summarize_run(raw: dict) -> dict | None:
    """Resumen de una carrera de Garmin con todos los campos conocidos que traiga (los que falten no se inventan)."""
    if not is_run(raw):
        return None
    aid = raw.get("activityId") or raw.get("activityID")
    start = str(raw.get("startTimeLocal") or "").replace(" ", "T")
    if not aid or len(start) < 10:
        return None
    out = {"garmin_id": str(aid), "date": start[:10], "start_local": start[:19], "name": raw.get("activityName"),
           "type": _type_key(raw), "source": "garmin_connect",
           "te_label": raw.get("trainingEffectLabel") or raw.get("trainingEffectLabelSrvrCalc")}
    for src, dst in FIELDS.items():
        v = _num(raw.get(src))
        if v is not None:
            out[dst] = round(v, 3)
    zones = [_num(raw.get(f"hrTimeInZone_{i}")) for i in range(1, 6)]
    if any(z is not None for z in zones):
        out["hr_zone_s"] = [round(z or 0) for z in zones]
    return out


def summarize_splits(raw) -> list[dict]:
    """Parciales (vueltas automáticas, normalmente por km) tal como los da Garmin."""
    laps = raw.get("lapDTOs") if isinstance(raw, dict) else raw
    out = []
    for i, lap in enumerate(laps if isinstance(laps, list) else []):
        if not isinstance(lap, dict):
            continue
        row = {"lap": i + 1}
        for src, dst in SPLIT_FIELDS.items():
            v = _num(lap.get(src))
            if v is not None:
                row[dst] = round(v, 3)
        if row.get("distance_m"):
            out.append(row)
    return out


def merge(history: dict | None, runs: list[dict], now: datetime) -> dict:
    """Las carreras nuevas o corregidas sustituyen a las guardadas; los parciales ya descargados se conservan."""
    hist = history if isinstance(history, dict) else {}
    kept = dict(hist.get("runs") or {})
    for r in runs:
        old = kept.get(r["garmin_id"]) or {}
        kept[r["garmin_id"]] = dict(r, splits=r.get("splits") or old.get("splits") or [])
    return {"schema_version": 1, "source": "Garmin Connect (get_activities_by_date + get_activity_splits)",
            "generated_at": now.isoformat(), "window_days": DAYS,
            "runs": dict(sorted(kept.items(), key=lambda kv: kv[1].get("start_local") or ""))}


def _login():
    token_b64 = os.environ.get("GARMIN_TOKENS_B64", "").strip()
    if not token_b64:
        raise RuntimeError("GARMIN_TOKENS_B64 no está disponible")
    token_dir = Path.home() / ".garminconnect"
    token_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    token_file = token_dir / "garmin_tokens.json"
    token_file.write_bytes(base64.b64decode(token_b64))
    token_file.chmod(0o600)
    from garminconnect import Garmin
    api = Garmin()
    api.login(str(token_dir))
    return api


def main() -> int:
    now = datetime.now(TZ)
    try:
        history = json.loads(HISTORY.read_text(encoding="utf-8")) if HISTORY.exists() else {}
    except (OSError, ValueError):
        history = {}
    try:
        api = _login()
        raw = api.get_activities_by_date((now.date() - timedelta(days=DAYS)).isoformat(), now.date().isoformat(), activitytype="running")
        runs = [r for r in (summarize_run(x) for x in raw or []) if r]
        known = (history.get("runs") or {}) if isinstance(history, dict) else {}
        calls = 0
        for r in sorted(runs, key=lambda x: x["start_local"], reverse=True):
            if (known.get(r["garmin_id"]) or {}).get("splits") or calls >= MAX_SPLIT_CALLS:
                continue
            calls += 1
            try:
                r["splits"] = summarize_splits(api.get_activity_splits(r["garmin_id"]))
            except Exception as exc:  # noqa: BLE001 — la API de Garmin lanza tipos variados
                print(f"::warning title=Parciales de carrera no disponibles::{r['garmin_id']}: {type(exc).__name__}")
        out = merge(history, runs, now)
        HISTORY.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(json.dumps({"runs": len(out["runs"]), "fetched": len(runs), "split_calls": calls}))
    except Exception as exc:  # noqa: BLE001 — nunca rompe la cadena: se conserva el historial
        print(f"::warning title=Historial de carreras no actualizado::{type(exc).__name__}: {str(exc)[:160]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
