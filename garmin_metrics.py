import os
import json
import base64
import statistics
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Madrid")
NOW = datetime.now(TZ)
TODAY = NOW.date()

STATUS_PATH = Path("garmin_status.json")
STRESS_PATH = Path("garmin_stress.json")
BB_PATH = Path("garmin_body_battery.json")


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def stress_summary(raw):
    if not isinstance(raw, dict):
        return None

    values = raw.get("stressValuesArray") or raw.get("stressValues") or []
    levels = []
    if isinstance(values, list):
        for item in values:
            if (
                isinstance(item, (list, tuple))
                and len(item) >= 2
                and number(item[1]) is not None
                and item[1] >= 0
            ):
                levels.append(item[1])

    p90 = None
    if levels:
        ordered = sorted(levels)
        p90 = ordered[min(len(ordered) - 1, int(0.90 * (len(ordered) - 1)))]

    return {
        "average_stress": number(
            raw.get("avgStressLevel", raw.get("averageStressLevel"))
        ),
        "max_stress": number(raw.get("maxStressLevel")),
        "stress_duration_secs": number(raw.get("stressDuration")),
        "rest_stress_duration_secs": number(raw.get("restStressDuration")),
        "sample_count": len(levels),
        "sample_mean": round(statistics.fmean(levels), 1) if levels else None,
        "sample_p90": round(p90, 1) if p90 is not None else None,
    }


def body_battery_summary(raw):
    if not isinstance(raw, dict):
        return None

    values = raw.get("bodyBatteryValuesArray") or []
    samples = []
    latest_ts = None

    if isinstance(values, list):
        for item in values:
            if (
                isinstance(item, (list, tuple))
                and len(item) >= 2
                and number(item[1]) is not None
            ):
                samples.append(item[1])
                latest_ts = item[0]

    return {
        "charged": number(raw.get("charged")),
        "drained": number(raw.get("drained")),
        "latest": samples[-1] if samples else None,
        "highest": max(samples) if samples else None,
        "lowest": min(samples) if samples else None,
        "sample_count": len(samples),
        "latest_sample_timestamp": latest_ts,
        "start_local": raw.get("startTimestampLocal"),
        "end_local": raw.get("endTimestampLocal"),
    }


status = {
    "generated_at": NOW.isoformat(),
    "timezone": "Europe/Madrid",
    "status": "error",
    "error": None,
    "latest_stress_date": None,
    "latest_body_battery_date": None,
}

try:
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

    stress_store = load_json(
        STRESS_PATH, {"timezone": "Europe/Madrid", "days": {}}
    )
    if not isinstance(stress_store, dict):
        stress_store = {"timezone": "Europe/Madrid", "days": {}}
    stress_store.setdefault("days", {})

    body_battery_store = load_json(
        BB_PATH, {"timezone": "Europe/Madrid", "days": {}}
    )
    if not isinstance(body_battery_store, dict):
        body_battery_store = {"timezone": "Europe/Madrid", "days": {}}
    body_battery_store.setdefault("days", {})

    # Primera ejecución: intenta recuperar 7 días.
    # Después: sólo refresca ayer y hoy para reducir llamadas a Garmin.
    if stress_store["days"]:
        stress_dates = [TODAY - timedelta(days=1), TODAY]
    else:
        stress_dates = [
            TODAY - timedelta(days=i) for i in range(6, -1, -1)
        ]

    stress_errors = {}
    for day in stress_dates:
        date_str = day.isoformat()
        try:
            payload = api.get_stress_data(date_str)
            if isinstance(payload, dict) and payload:
                stress_store["days"][date_str] = payload
        except Exception as exc:
            stress_errors[date_str] = f"{type(exc).__name__}: {exc}"

    # Body Battery permite consultar un rango en una sola petición.
    bb_start = TODAY - timedelta(
        days=6 if not body_battery_store["days"] else 1
    )

    body_battery_error = None
    try:
        payload = api.get_body_battery(
            bb_start.isoformat(), TODAY.isoformat()
        )
        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict):
                    date_str = item.get("date")
                    if date_str:
                        body_battery_store["days"][date_str] = item
    except Exception as exc:
        body_battery_error = f"{type(exc).__name__}: {exc}"

    stress_store["generated_at"] = NOW.isoformat()
    body_battery_store["generated_at"] = NOW.isoformat()

    save_json(STRESS_PATH, stress_store)
    save_json(BB_PATH, body_battery_store)

    today_str = TODAY.isoformat()
    today_stress = stress_summary(stress_store["days"].get(today_str))
    today_bb = body_battery_summary(
        body_battery_store["days"].get(today_str)
    )

    daily = load_json("daily_summary.json", {})
    if isinstance(daily, dict):
        daily["garmin_metrics"] = {
            "source": "Garmin Connect",
            "generated_at": NOW.isoformat(),
            "stress": today_stress,
            "body_battery": today_bb,
            "note": (
                "Stress y Body Battery son métricas propietarias de Garmin; "
                "interpretar junto con sueño, HRV, FC y sensaciones."
            ),
        }
        save_json("daily_summary.json", daily)

    weekly = load_json("weekly_summary.json", {})
    if isinstance(weekly, dict):
        week_start = TODAY - timedelta(days=6)
        per_day = {}

        for i in range(7):
            date_str = (week_start + timedelta(days=i)).isoformat()
            per_day[date_str] = {
                "stress": stress_summary(
                    stress_store["days"].get(date_str)
                ),
                "body_battery": body_battery_summary(
                    body_battery_store["days"].get(date_str)
                ),
            }

        weekly["garmin"] = {
            "source": "Garmin Connect",
            "generated_at": NOW.isoformat(),
            "days": per_day,
            "stress_days_present": sum(
                1 for value in per_day.values()
                if value["stress"] is not None
            ),
            "body_battery_days_present": sum(
                1 for value in per_day.values()
                if value["body_battery"] is not None
            ),
        }
        save_json("weekly_summary.json", weekly)

    status["status"] = (
        "success"
        if today_stress is not None or today_bb is not None
        else "partial"
    )
    status["latest_stress_date"] = max(
        stress_store["days"].keys(), default=None
    )
    status["latest_body_battery_date"] = max(
        body_battery_store["days"].keys(), default=None
    )
    status["stress_fetch_errors"] = stress_errors
    status["body_battery_fetch_error"] = body_battery_error

    if status["status"] == "partial":
        status["error"] = (
            "No se obtuvieron métricas Garmin para hoy; "
            "se preservaron los datos previos."
        )

except Exception as exc:
    status["error"] = f"{type(exc).__name__}: {exc}"

save_json(STATUS_PATH, status)
print(json.dumps(status, ensure_ascii=False))
