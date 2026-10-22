"""Certificado del informe e integridad del entrenamiento.

Responde a cuatro preguntas que el informe debe poder demostrar:

1. ¿De qué ciclo de sincronización salen los datos? (cycle_id, runs de la cadena)
2. ¿Qué antigüedad tienen las MEDICIONES? (marca de tiempo de cada muestra,
   nunca ``generated_at``)
3. ¿Son íntegros y coherentes? (huella SHA-256 de cada fuente y consistencia
   entre el modelo v3 y el v2, que deben leer los mismos valores de hoy)
4. ¿Se entregó? Desde la etapa de datos la entrega no es verificable; se
   declara explícitamente en lugar de suponerla.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta
from pathlib import Path

from .sources import SOURCE_FILES, parse_dt
from .stats import r

FRESH_MINUTES = {"confirmed_sleep": 18 * 60, "sleep_hrv": 18 * 60,
                 "heart_rate_live": 180, "body_battery_live": 180}


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _last_battery(row: dict):
    values = row.get("bodyBatteryValuesArray") if isinstance(row, dict) else None
    stamps = [item[0] for item in values or [] if isinstance(item, (list, tuple)) and item]
    return max(stamps) if stamps else None


def data_age(inputs: dict, now: datetime, tz) -> dict:
    """Antigüedad por MEDICIÓN real (fin del sueño, última muestra de HRV/FC/Body Battery).

    Se lee de las propias fuentes; la procedencia de report_ready.json solo se usa
    si una fuente no trae marca temporal."""
    today = now.date().isoformat()

    def day(key):
        days = (inputs.get(key) or {}).get("days") or {}
        return days.get(today) or {}

    found = {
        "confirmed_sleep": day("sleep").get("sleep_end_local") if day("sleep").get("window_confirmed") else None,
        "sleep_hrv": day("hrv").get("last_sample_local"),
        "heart_rate_live": day("hr_timeline").get("last_sample_local"),
        "body_battery_live": _last_battery(day("battery")),
    }
    prov = (inputs.get("report_ready") or {}).get("measurement_provenance") or {}
    out = {}
    for key, limit in FRESH_MINUTES.items():
        raw, basis = found.get(key), "fuente"
        if raw in (None, ""):
            raw, basis = (prov.get(key) or {}).get("measured_at"), "report_ready"
        moment = parse_dt(raw, tz)
        if moment is None:
            out[key] = {"measured_at": None, "age_minutes": None, "state": "sin_marca_temporal", "basis": None}
            continue
        age = (now - moment).total_seconds() / 60
        state = "futura" if age < -15 else "reciente" if age <= limit else "antigua"
        out[key] = {"measured_at": moment.isoformat(), "age_minutes": r(age, 0), "state": state, "basis": basis}
    return out


def consistency(readiness: dict, legacy: dict, tolerance: float) -> dict:
    """El v3 y el v2 usan la misma fusión: los valores de hoy deben coincidir."""
    cur = legacy.get("current") or {}
    if not cur or cur.get("date") != readiness.get("date"):
        return {"status": "no_comparable", "detail": "v2 sin datos del mismo día", "checks": {}}
    comp = readiness.get("components") or {}
    v3 = {"hrv_ms": (comp.get("hrv") or {}).get("today_ms"),
          "resting_hr": (comp.get("cardiac") or {}).get("resting_hr"),
          "sleep_hours": (comp.get("sleep") or {}).get("hours")}
    checks = {}
    for key, value in v3.items():
        other = cur.get(key)
        if value is None or other is None:
            checks[key] = {"v3": value, "v2": other, "ok": value is None and other is None}
        else:
            checks[key] = {"v3": value, "v2": other, "ok": abs(float(value) - float(other)) <= tolerance}
    ok = all(c["ok"] for c in checks.values())
    return {"status": "ok" if ok else "discrepancia", "checks": checks}


def certificate(root: Path, inputs: dict, readiness: dict, now: datetime, tz, cfg: dict) -> dict:
    ready = inputs.get("report_ready") or {}
    fb = inputs.get("feedback") or {}
    chain = ready.get("chain") or {}
    slot = parse_dt(ready.get("slot_at"), tz)
    same_day = bool(slot and slot.date() == now.date())
    verified = parse_dt(ready.get("verified_at"), tz)
    heart_gen = parse_dt((inputs.get("heart") or {}).get("generated_at"), tz)
    # Datos más nuevos que el último ciclo certificado → vienen de un Sync no programado
    newer_than_cycle = bool(verified and heart_gen and heart_gen > verified + timedelta(minutes=5))
    hashes = {}
    for name, _ in SOURCE_FILES.values():
        digest = _sha256(Path(root) / name)
        if digest:
            hashes[name] = digest[:16]
    ages = data_age(inputs, now, tz)
    cons = consistency(readiness, inputs.get("legacy_recovery") or {}, cfg["consistency_tolerance"])
    stale = [k for k, v in ages.items() if v["state"] in ("antigua", "futura")]
    issues = []
    if stale:
        issues.append("mediciones no recientes: " + ", ".join(stale))
    if cons["status"] == "discrepancia":
        issues.append("los modelos v3 y v2 leen valores distintos de hoy")
    if ready.get("status") != "ready":
        issues.append("la cadena no certificó datos preparados para este ciclo")
    health = inputs.get("workflow_health") or {}
    alerts = [a for a in health.get("alerts") or [] if isinstance(a, dict)]
    # Solo cuenta como perdida una franja que nadie recuperó. Si el cron de GitHub no disparó pero el respaldo de
    # Apps Script lanzó el Sync a tiempo («cron_missed_dispatch_recovered»), el ciclo se ejecutó: no es un aviso (V7.27).
    def _slots(code):
        return sorted({sl for a in alerts if a.get("code") == code for sl in (a.get("slots") or []) if isinstance(sl, str)})
    missed = _slots("sync_slot_not_recovered")
    recovered = [sl for sl in _slots("cron_missed_dispatch_recovered") if sl not in missed]
    if missed:
        issues.append(f"{len(missed)} franja(s) de Sync sin ejecutar ni recuperar")
    return {
        "generated_at": now.isoformat(),
        "cycle": {
            "cycle_id": ready.get("cycle_id"), "slot_at": ready.get("slot_at"),
            "status": ready.get("status"), "verified_at": ready.get("verified_at"),
            "scheduled_cycle_today": same_day,
            "data_newer_than_certified_cycle": newer_than_cycle,
            "data_synced_at": heart_gen.isoformat() if heart_gen else None,
            "note": ("Datos de un Sync posterior al último ciclo programado (p. ej. manual): válidos, sin certificado de franja propio."
                     if newer_than_cycle else None if same_day else
                     "Sin certificado de franja programada hoy: datos válidos, ciclo no programado."),
            "chain": {k: {"run_id": v.get("id"), "event": v.get("event"), "conclusion": v.get("conclusion")}
                      for k, v in chain.items() if isinstance(v, dict)},
        },
        "data_age": ages,
        "rpe_source": {"fetched_at": fb.get("source_fetched_at"), "latest_date": fb.get("remote_latest_date"),
                       "rows_sha256": (fb.get("source_rows_sha256") or "")[:16] or None,
                       "advanced_run_id": fb.get("advanced_run_id")},
        "source_sha256": hashes,
        "consistency_v3_v2": cons,
        "execution_health": {"status": health.get("status"), "checked_at": health.get("checked_at"),
                             "alerts": [{"code": a.get("code"), "severity": a.get("severity"),
                                         "slots": a.get("slots")} for a in alerts],
                             "missed_slots": missed, "recovered_slots": recovered},
        "delivery": {
            "status": "no_verificable_en_etapa_de_datos",
            "detail": ("Este certificado acredita datos preparados, no la recepción del informe. "
                       "ChatGPT no devuelve acuse; la rutina de Claude registra el ID de sesión en el paso V5.1."),
        },
        "status": "ok" if not issues else "con_avisos",
        "issues": issues,
    }


NO_RPE_TYPES = {"warmup", "skill", "mobility", "technique", "cooldown"}


def rpe_not_applicable(entry) -> bool:
    """La hoja declara explícitamente que esa actividad no lleva RPE (calentamiento, técnica…)."""
    if not isinstance(entry, dict) or entry.get("rpe") not in (None, ""):
        return False
    detail = entry.get("detail_json")
    if isinstance(detail, str) and detail.strip():
        try:
            detail = json.loads(detail)
        except ValueError:
            detail = {}
    kind = str((detail or {}).get("type") or "").lower() if isinstance(detail, dict) else ""
    notes = f"{entry.get('notes') or ''} {(detail or {}).get('notes') if isinstance(detail, dict) else ''}".lower()
    return kind in NO_RPE_TYPES or "rpe no declarado" in notes or "sin rpe" in notes or "no imputar" in notes


def training_integrity(sessions: dict, feedback: dict, today: str, days: int = 14) -> dict:
    """Empareja sesiones y RPE por ID exacto (nunca solo por fecha)."""
    end = date.fromisoformat(today)
    start = (end - timedelta(days=days - 1)).isoformat()
    fb = dict((feedback or {}).get("activities") or {})
    # Filas de la hoja sin RPE no llegan a "activities": se leen de la instantánea completa.
    for row in (feedback or {}).get("source_rows_AH") or []:
        if isinstance(row, dict) and row.get("ID actividad") and row["ID actividad"] not in fb:
            fb[row["ID actividad"]] = {"date": row.get("Fecha"), "activity": row.get("Actividad"),
                                       "rpe": row.get("RPE") or None, "notes": row.get("Notas"),
                                       "detail_json": row.get("Detalle JSON"), "_rpe_missing_row": True}
    window = {k: s for k, s in sessions.items() if start <= (s.get("date") or "") <= today}
    with_rpe = [s for s in window.values() if s.get("rpe") is not None]
    no_rpe = [s for s in window.values() if s.get("rpe") is None]
    declared = sorted((s for s in no_rpe if rpe_not_applicable(fb.get(s["id"]))), key=lambda s: s.get("start_local") or "")
    declared_ids = {s["id"] for s in declared}
    without = sorted((s for s in no_rpe if s["id"] not in declared_ids), key=lambda s: s.get("start_local") or "")
    orphan = sorted(k for k, v in fb.items()
                    if isinstance(v, dict) and start <= str(v.get("date") or "") <= today and k not in sessions)
    date_mismatch = sorted(k for k, v in fb.items()
                           if isinstance(v, dict) and k in sessions and v.get("date")
                           and v.get("date") != sessions[k].get("date"))
    total = len(window)
    applicable = total - len(declared)
    pct = 100.0 * len(with_rpe) / applicable if applicable else None
    status = "ok" if not without and not orphan and not date_mismatch else "revisar"
    return {
        "window_days": days, "from": start, "to": today,
        "sessions": total, "with_rpe": len(with_rpe), "rpe_coverage_pct": r(pct, 0),
        "rpe_not_applicable": [{"id": s["id"], "start_local": s.get("start_local"),
                                "label": (fb.get(s["id"]) or {}).get("activity")} for s in declared],
        "without_rpe": [{"id": s["id"], "start_local": s.get("start_local"), "type": s.get("type"),
                         "duration_min": s.get("duration_min"), "load": s.get("load")} for s in without],
        "rpe_without_activity": orphan, "date_mismatch": date_mismatch,
        "status": status,
        "rule": "Emparejado por ID exacto de actividad; las sesiones sin RPE no se rellenan ni se estiman.",
    }
