"""Orquestación: fuentes → registro diario → historial → carga → readiness → salidas."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from . import APP_VERSION, MODEL_VERSION
from .config import load_config
from .history import recompute_daily_load, update_history, write_table
from .load import compute_load
from .decision import operative_decision
from .quality import certificate, training_integrity
from .readiness import GUIDANCE, assess
from .records import DAILY_FIELDS, build_day_records, build_sessions
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
            "v2_score": row.get("v2_score"), "hybrid_score": row.get("hybrid_score"),
            "decision_zone": row.get("decision_zone"),
            "deep_min": row.get("deep_min"), "rem_min": row.get("rem_min"),
            "sleep_context": row.get("sleep_context"), "stress_avg_full": row.get("stress_avg"),
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

    garmin_today = (daily.get(today) or {}).get("garmin_readiness")
    decision = operative_decision(readiness, legacy, inputs.get("daily_summary") or {}, garmin_today,
                                  GUIDANCE, bool(cfg.get("model_validated")))
    # Histórico de modelos: se guarda la foto del día (la última ejecución del día prevalece)
    scores = {m["id"]: m.get("score") for m in decision["registry"]}
    today_row = daily.setdefault(today, {f: None for f in DAILY_FIELDS} | {"date": today})
    today_row.update({"v2_score": scores.get("recovery_assessment_v2"),
                      "hybrid_score": scores.get("readiness_hybrid"),
                      "v3_score": readiness.get("score"), "decision_zone": decision["zone"]})
    if series and series[-1]["date"] == today:
        series[-1].update({"v2_score": today_row["v2_score"], "hybrid_score": today_row["hybrid_score"],
                           "decision_zone": today_row["decision_zone"]})
    if write:
        write_table(root / cfg["history_dir"] / "daily.csv", daily, DAILY_FIELDS, "date")
    integrity = training_integrity(sessions, inputs.get("feedback") or {}, today)
    from .planned import load_planned, plan_block
    plan_rows, plan_source = load_planned(root)
    tomorrow = (date.fromisoformat(today) + timedelta(days=1)).isoformat()
    planned = plan_block(plan_rows, today, tomorrow, decision, list(sessions.values()), plan_source)
    cert = certificate(root, inputs, readiness, now, tz, cfg)

    dates = sorted(daily)
    result = {
        "schema_version": 1, "app_version": APP_VERSION, "model_version": MODEL_VERSION,
        "generated_at": now.isoformat(), "timezone": cfg["timezone"], "date": today,
        "decision": decision, "readiness": readiness, "load": load,
        "certificate": cert, "training_integrity": integrity, "planned": planned,
        "legacy_v2": {"score": legacy.get("score"), "status": legacy.get("status"),
                      "state": legacy.get("state"), "date": (legacy.get("current") or {}).get("date")},
        "history": {"days": len(daily), "first_date": dates[0] if dates else None,
                    "last_date": dates[-1] if dates else None, "sessions": len(sessions)},
        "trend_28d": series, "recent_sessions": recent_sessions,
        "mode": "shadow",
        "mode_note": ("Modelo v3 en paralelo: no sustituye recovery_assessment.json. La recomendación del día es "
                      "decision.guidance (la más conservadora entre modelos), no readiness.guidance."),
    }
    if write:
        out = root / cfg["output_dir"]
        _write_json(out / "readiness_v3.json", result)
        from .dashboard import render
        (out / "dashboard.html").write_text(render(result), encoding="utf-8")
        from .report import write_report
        write_report(root, out, result)
    return result
