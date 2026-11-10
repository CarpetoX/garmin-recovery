"""Criterio de entrenamiento sobre el historial completo (V9.1). Funciones puras salvo `load_*`.

- Carga estimada de sesiones sin RPE: TRIMP × tu relación mediana sRPE/TRIMP (de tus sesiones con RPE). Se muestra
  aparte y marcada como estimada; no cambia el sRPE oficial ni tu decisión de no puntuar esas sesiones.
- Semanas completas (lunes–domingo) con carga oficial + estimada y aviso orientativo de semana de descarga.
- Días post-TN: comparación mes a mes de recuperación y RPE frente al resto de días, y aviso para hoy.
- Tests de referencia periódicos (tests_registro.json): catálogo, mejor marca, cambio y próximo test sugerido.
"""
from __future__ import annotations

import csv
import json
from datetime import date as _date, timedelta
from pathlib import Path
from statistics import median

RATIO_MIN_N = 8          # sesiones con RPE y TRIMP necesarias para estimar
LIGHT_WEEK = 0.70        # semana ligera: ≤ 70 % de tu semana media
HEAVY_RUN = 3            # semanas seguidas sin semana ligera para sugerir descarga
TEST_EVERY_DAYS = 56     # repetir cada test hacia las 8 semanas


def _f(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if x == x else None


def _d(v):
    s = str(v or "")[:10]
    try:
        _date.fromisoformat(s)
    except ValueError:
        return None
    return s


def load_sessions(root: str | Path) -> list[dict]:
    p = Path(root) / "history" / "sessions.csv"
    try:
        with p.open(encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
    except OSError:
        return []
    out = []
    for r in rows:
        if str(r.get("removed") or "").strip().lower() in ("1", "1.0", "true", "yes") or not _d(r.get("date")):
            continue
        out.append({"id": r.get("id"), "date": _d(r["date"]), "label": r.get("label") or r.get("name"),
                    "minutes": _f(r.get("duration_min")), "trimp": _f(r.get("trimp")), "rpe": _f(r.get("rpe")), "srpe": _f(r.get("srpe"))})
    return out


def load_daily(root: str | Path) -> dict[str, dict]:
    p = Path(root) / "history" / "daily.csv"
    try:
        with p.open(encoding="utf-8", newline="") as fh:
            return {r["date"]: r for r in csv.DictReader(fh) if _d(r.get("date"))}
    except (OSError, KeyError):
        return {}


# ---------------------------------------------------------------- carga

def srpe_trimp_ratio(sessions: list[dict]) -> dict | None:
    rs = [s["srpe"] / s["trimp"] for s in sessions if s.get("rpe") is not None and (s.get("srpe") or 0) > 0 and (s.get("trimp") or 0) > 0]
    if len(rs) < RATIO_MIN_N:
        return None
    return {"ratio": median(rs), "n": len(rs)}


def with_estimate(sessions: list[dict], ratio: dict | None) -> list[dict]:
    """Cada sesión con `load_official` (sRPE) y `load_estimated` (solo sin RPE y con TRIMP)."""
    out = []
    for s in sessions:
        est = None
        if s.get("rpe") is None and ratio and (s.get("trimp") or 0) > 0:
            est = s["trimp"] * ratio["ratio"]
        out.append(dict(s, load_official=(s.get("srpe") or 0) if s.get("rpe") is not None else 0, load_estimated=est))
    return out


def complete_weeks(sessions: list[dict], today: str, n: int = 8) -> list[dict]:
    """Semanas lunes–domingo completas y cubiertas por el historial (nunca la semana en curso)."""
    t = _date.fromisoformat(today)
    monday = t - timedelta(days=t.weekday())
    first = min((s["date"] for s in sessions), default=None)
    out = []
    for i in range(n, 0, -1):
        mon = monday - timedelta(days=7 * i)
        sun = mon + timedelta(days=6)
        if not first or mon.isoformat() < first:
            continue
        ws = [s for s in sessions if mon.isoformat() <= s["date"] <= sun.isoformat()]
        off = sum(s.get("load_official") or 0 for s in ws)
        est = sum(s.get("load_estimated") or 0 for s in ws)
        out.append({"monday": mon.isoformat(), "sessions": len(ws), "days": len({s["date"] for s in ws}),
                    "official": round(off), "estimated": round(est), "total": round(off + est),
                    "hard": sum(1 for s in ws if (s.get("rpe") or 0) >= 8), "unscored": sum(1 for s in ws if s.get("rpe") is None)})
    return out


def deload(weeks: list[dict]) -> dict:
    """Sugerencia orientativa: ≥ 3 semanas completas seguidas sin semana ligera (≤ 70 % de tu media)."""
    if len(weeks) < 4:
        return {"status": "insufficient", "weeks": len(weeks)}
    mean = sum(w["total"] for w in weeks) / len(weeks)
    if mean <= 0:
        return {"status": "insufficient", "weeks": len(weeks)}
    light = [w for w in weeks if w["total"] <= LIGHT_WEEK * mean]
    last_light = light[-1]["monday"] if light else None
    run = 0
    for w in reversed(weeks):
        if w["total"] <= LIGHT_WEEK * mean:
            break
        run += 1
    return {"status": "due" if run >= HEAVY_RUN else "ok", "run": run, "mean": round(mean), "last_light": last_light,
            "threshold": round(LIGHT_WEEK * mean), "weeks": len(weeks)}


# ---------------------------------------------------------------- post-TN

def post_tn_months(daily: dict[str, dict], sessions: list[dict], context_of) -> list[dict]:
    """Por mes: días post-TN frente al resto (recuperación oficial media y RPE medio de las sesiones de esos días)."""
    rpe_by_day: dict[str, list] = {}
    for s in sessions:
        if s.get("rpe") is not None:
            rpe_by_day.setdefault(s["date"], []).append(s["rpe"])
    months: dict[str, dict] = {}
    for d, r in daily.items():
        ctx = context_of(d)
        if ctx is None:
            continue
        m = months.setdefault(d[:7], {"post": {"score": [], "rpe": []}, "rest": {"score": [], "rpe": []}})
        g = m["post" if ctx == "post-TN" else "rest"]
        sc = _f(r.get("v2_score"))
        if sc is not None:
            g["score"].append(sc)
        g["rpe"] += rpe_by_day.get(d, [])
    out = []
    for m in sorted(months):
        row = {"month": m}
        for k in ("post", "rest"):
            g = months[m][k]
            row[k] = {"days_scored": len(g["score"]), "score": round(sum(g["score"]) / len(g["score"])) if g["score"] else None,
                      "rpe": round(sum(g["rpe"]) / len(g["rpe"]), 1) if g["rpe"] else None, "sessions": len(g["rpe"]),
                      "score_sum": sum(g["score"]), "rpe_sum": sum(g["rpe"])}  # sumas sin redondear para juntar meses
        if row["post"]["days_scored"] or row["post"]["sessions"]:
            out.append(row)
    return out


def post_tn_today(months: list[dict]) -> dict | None:
    """Resumen de todos los meses para el aviso de hoy (solo si hay al menos 3 días post-TN con puntuación)."""
    def pooled(group, total, count):
        n = sum(r[group][count] for r in months)
        return (round(sum(r[group][total] for r in months) / n, 1) if n else None), n
    score, n = pooled("post", "score_sum", "days_scored")
    if n < 3:
        return None
    rpe, n_rpe = pooled("post", "rpe_sum", "sessions")
    rest, n_rest = pooled("rest", "score_sum", "days_scored")
    return {"days": n, "score": score, "rpe": rpe, "rpe_sessions": n_rpe, "rest_score": rest, "rest_days": n_rest}


# ---------------------------------------------------------------- tests

TESTS = {  # clave: (nombre, unidad, mejor = "low" | "high", descripción)
    "fran": ("Fran", "s", "low", "21-15-9 thrusters 43 kg + dominadas"),
    "grace": ("Grace", "s", "low", "30 clean & jerk 61 kg"),
    "helen": ("Helen", "s", "low", "3 rondas: 400 m carrera, 21 swings 24 kg, 12 dominadas"),
    "remo_500": ("Remo 500 m", "s", "low", "500 m a máxima intensidad"),
    "dominadas_max": ("Dominadas estrictas", "reps", "high", "máximo seguido, sin kipping"),
    "sentadilla_3rm": ("Sentadilla trasera 3RM", "kg", "high", "3 repeticiones máximas"),
    "peso_muerto_3rm": ("Peso muerto 3RM", "kg", "high", "3 repeticiones máximas"),
    "banca_3rm": ("Press banca 3RM", "kg", "high", "3 repeticiones máximas"),
}
TESTS_FILE = "tests_registro.json"


def load_tests(root: str | Path) -> list[dict]:
    try:
        data = json.loads((Path(root) / TESTS_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    e = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(e, list):
        return []
    out = []
    for x in e:
        v = _f(x.get("value")) if isinstance(x, dict) else None
        if isinstance(x, dict) and x.get("test") in TESTS and _d(x.get("date")) and v is not None and abs(v) < 1e7:
            out.append(dict(x, date=_d(x["date"]), value=v, scaled=x.get("scaled") if isinstance(x.get("scaled"), str) else ""))
    return out


def record_test(root: str | Path, day: str, test: str, value: float, note: str | None = None, scaled: str | None = None) -> dict:
    if test not in TESTS:
        raise ValueError(f"test desconocido: {test}")
    if not _d(day) or _f(value) is None or abs(_f(value)) >= 1e7:
        raise ValueError("fecha o valor no válidos")
    p = Path(root) / TESTS_FILE
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
            raise ValueError
    except (OSError, ValueError):
        data = {"_comentario": "Tests de referencia periódicos (cada 6–8 semanas). Tiempos en segundos, cargas en kg.", "entries": []}
    entry = {"date": _d(day), "test": test, "value": float(value)}
    if scaled:
        entry["scaled"] = scaled  # p. ej. «thrusters 35 kg»: solo se compara con la misma versión
    if note:
        entry["note"] = note
    data["entries"].append(entry)
    data["entries"].sort(key=lambda e: (str(e.get("date")), str(e.get("test"))))
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return entry


def tests_summary(entries: list[dict], today: str) -> list[dict]:
    """Por test (y versión): última marca, la anterior, la mejor, el cambio y si toca repetirlo."""
    t = _date.fromisoformat(today)
    groups: dict[tuple, list] = {}
    for e in entries:
        groups.setdefault((e["test"], e.get("scaled") or ""), []).append(e)
    out = []
    for (key, scaled), es in groups.items():
        es = sorted(es, key=lambda e: e["date"])
        name, unit, better, desc = TESTS[key]
        vals = [_f(e["value"]) for e in es]
        best = min(vals) if better == "low" else max(vals)
        last, prev = es[-1], (es[-2] if len(es) >= 2 else None)
        change = (_f(last["value"]) - _f(prev["value"])) if prev else None
        improved = None if change is None or change == 0 else ((change < 0) if better == "low" else (change > 0))
        days_since = (t - _date.fromisoformat(last["date"])).days
        out.append({"test": key, "name": name, "unit": unit, "better": better, "scaled": scaled, "desc": desc,
                    "last": _f(last["value"]), "last_date": last["date"], "prev": _f(prev["value"]) if prev else None,
                    "prev_date": prev["date"] if prev else None, "best": best, "change": change, "improved": improved,
                    "count": len(es), "due": days_since >= TEST_EVERY_DAYS, "days_since": days_since})
    out.sort(key=lambda r: list(TESTS).index(r["test"]))
    return out


def fmt_value(v, unit: str) -> str:
    if v is None:
        return "—"
    if unit == "s":
        v = int(round(v))
        return f"{v // 60}:{v % 60:02d}"
    s = f"{v:.1f}".rstrip("0").rstrip(".")
    return s.replace(".", ",") + (" kg" if unit == "kg" else "")
