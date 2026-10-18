"""Estado de las fuentes de datos (Intervals.icu y Garmin) para el informe, a partir de lo ya publicado."""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Madrid")


def _read(root: Path, name: str):
    try:
        return json.loads((Path(root) / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _age(last: str | None, today: date) -> int | None:
    try:
        return (today - date.fromisoformat(str(last)[:10])).days
    except (TypeError, ValueError):
        return None


def _state(age: int | None, err: dict | None) -> tuple[str, str]:
    if err and err.get("status") == "error":
        n = int(err.get("consecutive_failures") or 0)
        return "🔴" if n >= 3 else "🟠", f"fallo {err.get('kind') or '?'}" + (f" (HTTP {err['http']})" if err.get("http") else "") + f", {n} seguido(s)"
    if age is None:
        return "⚪", "sin datos"
    if age <= 0:
        return "🟢", "al día"
    return ("🟠", f"{age} día atrasado") if age == 1 else ("🔴", f"{age} días atrasado")


def collect(root, now: datetime | None = None) -> list[dict]:
    root, today = Path(root), (now or datetime.now(TZ)).astimezone(TZ).date()
    istat = _read(root, "intervals_status.json") or {}
    gs = _read(root, "garmin_status.json") or {}
    wellness = _read(root, "wellness.json") or []
    acts = _read(root, "activities.json") or []
    sleep = (_read(root, "garmin_sleep_history.json") or {}).get("days") or {}
    w_new = max((str(x.get("id") or "") for x in wellness if isinstance(x, dict)
                 and any(x.get(k) not in (None, "", 0) for k in ("hrv", "restingHR", "sleepSecs"))), default=None)
    a_new = max((str(x.get("start_date_local") or "")[:10] for x in acts if isinstance(x, dict) and x.get("start_date_local")), default=None)
    rows = [("Intervals.icu · bienestar (HRV, FC reposo, sueño)", w_new, istat.get("wellness")),
            ("Intervals.icu · actividades", a_new, istat.get("activities")),
            ("Garmin · FC diurna y nocturna", gs.get("latest_heart_rate_date"), None),
            ("Garmin · estrés", gs.get("latest_stress_date"), None),
            ("Garmin · Body Battery", gs.get("latest_body_battery_date"), None),
            ("Garmin · Training Readiness y tiempo de recuperación", gs.get("latest_extended_date"), None),
            ("Garmin · sueño", max((d for d in sleep if isinstance(sleep[d], dict)), default=None), None)]
    out = []
    for label, last, err in rows:
        if label.endswith("actividades"):
            # la fecha de la última actividad no mide la salud de la fuente (puede no haber entrenado): manda la descarga
            if err and err.get("status") == "ok":
                icon, text = "🟢", "descarga correcta" + (f" ({str(err.get('last_ok_at'))[:10]})" if err.get("last_ok_at") else "")
            elif err:
                icon, text = _state(None, err)
            else:
                icon, text = "⚪", "sin registro de descarga todavía"
            out.append({"source": label, "last": last, "icon": icon, "state": text})
            continue
        icon, text = _state(_age(last, today), err)
        out.append({"source": label, "last": last, "icon": icon, "state": text})
    if gs.get("error"):
        out.append({"source": "Garmin · última ejecución", "last": gs.get("generated_at", "")[:10], "icon": "🟠",
                    "state": "error: " + str(gs["error"])[:100]})
    return out


def to_markdown(rows: list[dict]) -> str:
    L = ["\n### Fuentes de datos\n", "| Fuente | Último dato | Estado |", "|---|---|---|"]
    for r in rows:
        L.append(f"| {r['source']} | {r['last'] or '—'} | {r['icon']} {r['state']} |")
    L.append("\n_Un retraso de un día es normal a primera hora; se avisa por GitHub si Intervals falla tres veces seguidas._")
    return "\n".join(L) + "\n"
