"""Historial largo de recuperación (V9.4): de marzo de 2026 en adelante.

Los archivos diarios de la cadena guardan unos 60 días y ``history/daily.csv`` empieza el 24/09/2026, así que no
se veía cómo ha cambiado la recuperación desde que el atleta empezó CrossFit. Este módulo:

* ``backfill``: descarga de Garmin, día a día y solo los días que faltan, HRV nocturna, FC en reposo, sueño
  (con el mismo filtro que ``garmin_sleep_history.extract_sleep``), estrés medio y Body Battery máximo/mínimo, y los
  guarda en ``history/daily_longterm.csv``. Se ejecuta a mano (workflow «Historial largo de Garmin»).
* ``monthly``: medianas mensuales combinando ese archivo con ``history/daily.csv`` (manda daily.csv si un día está en
  los dos). Solo describe; NO alimenta las decisiones del día ni los rangos de 28 días.

Un día sin dato se deja vacío: nunca se rellena ni se interpola.
"""
from __future__ import annotations

import argparse
import base64
import csv
import os
import statistics
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Madrid")
FILE = Path("history") / "daily_longterm.csv"
FIELDS = ["date", "hrv_ms", "resting_hr", "sleep_hours", "sleep_score", "sleep_context", "stress_avg",
          "body_battery_high", "body_battery_low", "source", "fetched_at"]
METRICS = [  # (campo, nombre, unidad, decimales, ¿más alto es mejor?)
    ("hrv_ms", "HRV nocturna", "ms", 0, True),
    ("resting_hr", "FC en reposo", "lpm", 0, False),
    ("sleep_hours", "Sueño", "h", 1, True),
    ("sleep_score", "Puntuación de sueño", "", 0, True),
    ("stress_avg", "Estrés medio", "", 0, False),
    ("body_battery_high", "Body Battery máx.", "", 0, True),
]
DEFAULT_START = "2026-03-01"
MIN_DAYS_PER_MONTH = 10  # una mediana mensual con menos días no se muestra


def _num(v, low=None, high=None):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    if x != x or (low is not None and x < low) or (high is not None and x > high):
        return None
    return x


def read(path: str | Path) -> dict[str, dict]:
    p = Path(path)
    if not p.exists():
        return {}
    with p.open(encoding="utf-8", newline="") as fh:
        return {r["date"]: r for r in csv.DictReader(fh) if r.get("date")}


def write(path: str | Path, rows: dict[str, dict]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".csv.tmp")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        for k in sorted(rows):
            w.writerow({f: ("" if rows[k].get(f) is None else rows[k].get(f)) for f in FIELDS})
    tmp.replace(p)


def extract_day(day: str, hrv_raw, stats_raw, sleep_raw, generated_at: str) -> dict:
    """Convierte las tres respuestas de Garmin de un día en una fila; lo que no cuadra queda vacío."""
    from .garmin_sleep_history import extract_sleep
    row: dict = {"date": day, "source": "Garmin Connect (historial largo)", "fetched_at": generated_at}
    summ = (hrv_raw or {}).get("hrvSummary") if isinstance(hrv_raw, dict) else None
    hrv = _num((summ or {}).get("lastNightAvg"), 5, 250)
    row["hrv_ms"] = int(round(hrv)) if hrv is not None else None
    st = stats_raw if isinstance(stats_raw, dict) else {}
    for field, key, lo, hi in (("resting_hr", "restingHeartRate", 25, 120), ("stress_avg", "averageStressLevel", 0, 100),
                               ("body_battery_high", "bodyBatteryHighestValue", 0, 100),
                               ("body_battery_low", "bodyBatteryLowestValue", 0, 100)):
        v = _num(st.get(key), lo, hi)
        row[field] = int(round(v)) if v is not None else None
    sl = extract_sleep(sleep_raw, date.fromisoformat(day), generated_at) if isinstance(sleep_raw, dict) else None
    if sl:
        row["sleep_hours"], row["sleep_score"], row["sleep_context"] = sl["sleep_hours"], sl["sleep_score"], sl["sleep_context"]
    return row


def _has_data(row: dict) -> bool:
    return any(row.get(f) not in (None, "") for f, *_ in METRICS)


def pending_days(existing: dict, start: str, end: str, limit: int) -> list[str]:
    d, last, out = date.fromisoformat(start), date.fromisoformat(end), []
    while d <= last and len(out) < limit:
        if d.isoformat() not in existing:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def backfill(root: str | Path, api, start: str, end: str, limit: int = 400, pause: float = 0.6, now: datetime | None = None) -> dict:
    root = Path(root)
    rows = read(root / FILE)
    generated_at = (now or datetime.now(TZ)).isoformat(timespec="seconds")
    todo = pending_days(rows, start, end, limit)
    errors, empty = {}, []
    for day in todo:
        got = {}
        for label, fn in (("hrv", lambda d=day: api.get_hrv_data(d)), ("stats", lambda d=day: api.get_stats(d)),
                          ("sleep", lambda d=day: api.get_sleep_data(d))):
            try:
                got[label] = fn()
            except Exception as exc:  # noqa: BLE001 — un fallo de un día no para el resto
                errors[f"{day}:{label}"] = f"{type(exc).__name__}: {str(exc)[:120]}"
                got[label] = None
            time.sleep(pause)
        row = extract_day(day, got["hrv"], got["stats"], got["sleep"], generated_at)
        if _has_data(row):
            rows[day] = row
        elif not any(k.startswith(day) for k in errors):
            empty.append(day)  # Garmin no tiene nada ese día: no se escribe, se informa
    write(root / FILE, rows)
    return {"requested": len(todo), "written": sum(1 for d in todo if d in rows), "empty_days": empty,
            "errors": len(errors), "error_sample": dict(list(errors.items())[:5]), "total_rows": len(rows)}


def combined(root: str | Path) -> dict[str, dict]:
    """Historial largo + daily.csv; si un día está en ambos manda daily.csv (es el dato de la cadena)."""
    root = Path(root)
    out = {k: dict(v) for k, v in read(root / FILE).items()}
    for k, v in read(root / "history" / "daily.csv").items():
        base = out.setdefault(k, {"date": k})
        for f, *_ in METRICS:
            if v.get(f) not in (None, ""):
                base[f] = v[f]
        if v.get("sleep_context"):
            base["sleep_context"] = v["sleep_context"]
    return out


def monthly(root: str | Path) -> list[dict]:
    """Mediana por mes de cada métrica; el sueño solo de noches (no sueños de día tras guardia)."""
    by_month: dict[str, dict[str, list[float]]] = {}
    for k, r in combined(root).items():
        m = by_month.setdefault(k[:7], {})
        for f, *_ in METRICS:
            if f in ("sleep_hours", "sleep_score") and r.get("sleep_context") == "day_sleep":
                continue
            v = _num(r.get(f))
            if v is not None:
                m.setdefault(f, []).append(v)
    out = []
    for month in sorted(by_month):
        vals = by_month[month]
        row = {"month": month, "days": max((len(v) for v in vals.values()), default=0)}
        for f, *_ in METRICS:
            xs = vals.get(f) or []
            row[f] = statistics.median(xs) if len(xs) >= MIN_DAYS_PER_MONTH else None
            row[f + "_n"] = len(xs)
        out.append(row)
    return out


def _login():
    token_b64 = os.environ.get("GARMIN_TOKENS_B64", "").strip()
    if not token_b64:
        raise SystemExit("Falta GARMIN_TOKENS_B64")
    token_dir = Path.home() / ".garminconnect"
    token_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    f = token_dir / "garmin_tokens.json"
    f.write_bytes(base64.b64decode(token_b64))
    f.chmod(0o600)
    from garminconnect import Garmin
    api = Garmin()
    api.login(str(token_dir))
    return api


def main(argv=None) -> int:
    import json
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default=DEFAULT_START)
    ap.add_argument("--end", default=None, help="por defecto, hace 2 días")
    ap.add_argument("--limit", type=int, default=400)
    a = ap.parse_args(argv)
    end = a.end or (datetime.now(TZ).date() - timedelta(days=2)).isoformat()
    res = backfill(".", _login(), a.start, end, a.limit)
    print(json.dumps(res, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
