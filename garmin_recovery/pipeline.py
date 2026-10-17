"""Orquestación: fuentes → registro diario → historial → carga → readiness → salidas."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from . import APP_VERSION, MODEL_VERSION
from .config import load_config
from .history import recompute_daily_load, update_history
from .load import compute_load
from .quality import certificate, training_integrity
from .readiness import assess
from .records import build_day_records, build_sessions
from .sources import load_inputs


def _write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def trend(daily: dict, sessions: dict, end: str, cfg: dict, days: int = 28) -> list[dict]:
    """Recalcula el modelo para días pasados (sin compuerta matinal) para ver la evolución."""
    out = []
    last = date.fromisoformat(end)
    for i in range(days - 1, -1, -1):
        d = (last - timedelta(days=i)).isoformat()
        row = daily.get(d) or {}
        load = compute_load(daily, sessions, d, cfg)
        res = assess(daily, d, cfg, load=load, apply_morning_gate=False)
        hrv = res["components"]["hrv"]
        out.append({
            "date": d, "score": res["score"], "zone": res["zone"], "state": res["state"],
            "hrv_ms": row.get("hrv_ms"), "hrv_rolling_ms": hrv.get("rolling_ms"),
            "hrv_low_ms": hrv.get("normal_low_ms"), "hrv_high_ms": hrv.get("normal_high_ms"),
            "resting_hr": row.get("resting_hr"), "night_hr": row.get("night_hr"),
            "sleep_hours": row.get("sleep_hours"), "sleep_score": row.get("sleep_score"),
            "load": row.get("load") or 0.0, "srpe": row.get("srpe"),
            "sessions": row.get("sessions") or 0, "stress_avg": row.get("stress_avg"),
            "garmin_readiness": row.get("garmin_readiness"), "shift": row.get("shift"),
            "ctl": load.get("ctl"), "atl": load.get("atl"),
        })
    return out


def run(root: str | Path = ".", now: datetime | None = None, write: bool = True) -> dict:
    root = Path(root)
    cfg = load_config(root)
    tz = ZoneInfo(cfg["timezone"])
    now = now or datetime.now(tz)
    today = now.date().isoformat()

    inputs = load_inputs(root)
    sessions_fresh = build_sessions(inputs)
    day_records = build_day_records(inputs, now, sessions_fresh)
    daily, sessions = update_history(root / cfg["history_dir"], day_records, sessions_fresh, write=write)
    daily = recompute_daily_load(daily, sessions)

    load = compute_load(daily, sessions, today, cfg)
    readiness = assess(daily, today, cfg, load=load, morning=inputs.get("morning"))
    series = trend(daily, sessions, today, cfg)
    legacy = inputs.get("legacy_recovery") or {}
    recent_sessions = sorted(sessions.values(), key=lambda s: (s["date"], s.get("start_local") or ""), reverse=True)[:12]

    integrity = training_integrity(sessions, inputs.get("feedback") or {}, today)
    cert = certificate(root, inputs, readiness, now, tz, cfg)

    dates = sorted(daily)
    result = {
        "schema_version": 1, "app_version": APP_VERSION, "model_version": MODEL_VERSION,
        "generated_at": now.isoformat(), "timezone": cfg["timezone"], "date": today,
        "readiness": readiness, "load": load,
        "certificate": cert, "training_integrity": integrity,
        "legacy_v2": {"score": legacy.get("score"), "status": legacy.get("status"),
                      "state": legacy.get("state"), "date": (legacy.get("current") or {}).get("date")},
        "history": {"days": len(daily), "first_date": dates[0] if dates else None,
                    "last_date": dates[-1] if dates else None, "sessions": len(sessions)},
        "trend_28d": series, "recent_sessions": recent_sessions,
        "mode": "shadow",
        "mode_note": "Modelo v3 en paralelo: no sustituye recovery_assessment.json ni los informes existentes.",
    }
    if write:
        out = root / cfg["output_dir"]
        _write_json(out / "readiness_v3.json", result)
        from .dashboard import render
        (out / "dashboard.html").write_text(render(result), encoding="utf-8")
    return result
