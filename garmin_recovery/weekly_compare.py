"""Comparación semana a semana (lunes a domingo) a partir de ``trend_28d`` y las sesiones publicadas.

Reglas: la semana en curso se muestra aparte y nunca se compara; entre semanas completas solo se calcula la
diferencia si ambas tienen cobertura suficiente, y el porcentaje únicamente con 7 de 7 días. La carga solo se
compara si la cobertura de RPE es suficiente y la semana es posterior al primer registro de sesiones. Sin
causalidad: son diferencias descriptivas.
"""
from __future__ import annotations

from datetime import date, timedelta
from statistics import mean

from .config import DEFAULTS

MIN_SRPE_COV = DEFAULTS["min_srpe_coverage_pct"]
BARS = "▁▂▃▄▅▆▇█"
MIN_DAYS = 5   # días con dato para dar una media semanal comparable
# clave, etiqueta, unidad, decimales, "mejor" (+1 sube, -1 baja, 0 neutro), umbral de cambio relevante, ¿porcentaje?
PHYSIO = [
    ("hrv_ms", "HRV nocturna", "ms", 0, +1, 5.0, True),
    ("resting_hr", "FC en reposo", "lpm", 1, -1, 2.0, False),
    ("sleep_hours", "Sueño", "h", 1, +1, 0.5, False),
    ("sleep_score", "Puntuación de sueño", "", 0, +1, 5.0, False),
]


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _fmt(v, d):
    return "—" if v is None else f"{v:.{d}f}".replace(".", ",")


def _signed(v, d, unit=""):
    s = f"{abs(v):.{d}f}".replace(".", ",")
    return f"{'+' if v > 0 else '−' if v < 0 else '±'}{s}{(' ' + unit) if unit else ''}"


def _spark(values):
    pts = [v for v in values if v is not None]
    if not pts:
        return "·" * len(values)
    lo, hi = min(pts), max(pts)
    return "".join("·" if v is None else BARS[3 if hi == lo else round((v - lo) / (hi - lo) * 7)] for v in values)


def weeks(trend: list[dict], today: str, count: int = 4) -> list[dict]:
    """Últimas ``count`` semanas; la última contiene ``today`` y puede estar incompleta."""
    end = date.fromisoformat(today)
    mon = end - timedelta(days=end.weekday())
    by_date = {t["date"]: t for t in trend if isinstance(t, dict) and t.get("date")}
    out = []
    for k in range(count - 1, -1, -1):
        a = mon - timedelta(weeks=k)
        days = [(a + timedelta(days=i)) for i in range(7)]
        elapsed = [d for d in days if d <= end]
        rows = [by_date.get(d.isoformat()) for d in elapsed]
        out.append({"start": a.isoformat(), "elapsed": len(elapsed), "complete": len(elapsed) == 7,
                    "in_window": all(r is not None for r in rows) if rows else False,
                    "rows": [r for r in rows if r is not None], "have_rows": sum(r is not None for r in rows)})
    return out


def _mean(week, key):
    vals = [_num(r.get(key)) for r in week["rows"]]
    vals = [v for v in vals if v is not None]
    return (mean(vals), len(vals)) if vals else (None, 0)


def _first_session_monday(sessions):
    firsts = [(s.get("date") or "")[:10] for s in sessions if isinstance(s, dict) and (s.get("date") or "")[:10]]
    if not firsts:
        return None
    f = date.fromisoformat(min(firsts))
    return (f - timedelta(days=f.weekday())).isoformat()


def compare(trend, sessions, today, coverage_pct=None) -> dict:
    ws = weeks(trend, today)
    cur, prev, before = ws[-1], ws[-2], ws[-3]
    first_mon = _first_session_monday(sessions)
    rows = []
    for key, label, unit, dec, good, thr, pct in PHYSIO:
        vals = [_mean(w, key) for w in ws]
        a, na = vals[-2]
        b, nb = vals[-3]
        item = {"key": key, "label": label, "unit": unit, "dec": dec, "spark": _spark([v if n >= MIN_DAYS or w is cur else None
                                                                                       for (v, n), w in zip(vals, ws, strict=True)]),
                "prev": a, "prev_n": na, "before": b, "before_n": nb, "current": vals[-1][0], "current_n": vals[-1][1],
                "delta": None, "pct": None, "verdict": None}
        if a is not None and b is not None and na >= MIN_DAYS and nb >= MIN_DAYS:
            item["delta"] = a - b
            if pct and na == 7 and nb == 7 and b:
                item["pct"] = (a / b - 1) * 100
            change = abs(item["delta"] / b * 100) if pct and b else abs(item["delta"])
            item["verdict"] = "stable" if change < thr else ("better" if (item["delta"] > 0) == (good > 0) else "worse")
        rows.append(item)
    load_ok = (coverage_pct is not None and coverage_pct >= MIN_SRPE_COV and first_mon is not None
               and before["start"] >= first_mon)
    load = None
    if load_ok:
        def agg(w):
            rs = w["rows"]
            return {"sessions": sum(_num(r.get("sessions")) or 0 for r in rs),
                    "srpe": round(sum(_num(r.get("srpe")) or 0 for r in rs)),
                    "days": sum(1 for r in rs if (_num(r.get("sessions")) or 0) > 0)}
        a, b = agg(prev), agg(before)
        load = {"prev": a, "before": b, "current": agg(cur),
                "srpe_pct": ((a["srpe"] / b["srpe"] - 1) * 100) if prev["have_rows"] == 7 and before["have_rows"] == 7 and b["srpe"] else None,
                "spark": _spark([agg(w)["srpe"] if w["have_rows"] >= (w["elapsed"] if not w["complete"] else 7) else None for w in ws])}
    return {"weeks": [{k: w[k] for k in ("start", "elapsed", "complete", "have_rows")} for w in ws],
            "physio": rows, "load": load, "load_reason": None if load_ok else (
                "cobertura de RPE insuficiente" if coverage_pct is None or coverage_pct < MIN_SRPE_COV
                else "una de las semanas es anterior al inicio del historial de sesiones"),
            "comparable": prev["complete"] and before["complete"] and prev["have_rows"] == 7 and before["have_rows"] == 7,
            "coverage_pct": coverage_pct}


def _label(start):
    d = date.fromisoformat(start)
    return f"{d.day:02d}/{d.month:02d}"


def to_markdown(c: dict) -> str:
    w = c["weeks"]
    prev, before, cur = w[-2], w[-3], w[-1]
    L = ["\n### Semana a semana\n",
         f"Última semana completa (lunes {_label(prev['start'])}) frente a la anterior (lunes {_label(before['start'])}). "
         f"La semana en curso ({cur['elapsed']} de 7 días, hoy incluido) se muestra aparte y no se compara. Son diferencias descriptivas, "
         "no explican causas.\n",
         f"| Métrica | Sem. {_label(before['start'])} | Sem. {_label(prev['start'])} | Cambio | En curso | 4 semanas |",
         "|---|---|---|---|---|---|"]
    icon = {"better": "✅", "worse": "⚠️", "stable": "≈", None: "ℹ️"}
    for r in c["physio"]:
        if r["delta"] is None:
            change = "datos insuficientes"
        else:
            change = f"{icon[r['verdict']]} {_signed(r['delta'], r['dec'], r['unit'])}"
            if r["pct"] is not None:
                change += f" ({_signed(r['pct'], 0)} %)"
        L.append(f"| {r['label']} | {_fmt(r['before'], r['dec'])} ({r['before_n']} d) | {_fmt(r['prev'], r['dec'])} ({r['prev_n']} d) | "
                 f"{change} | {_fmt(r['current'], r['dec'])} ({r['current_n']} d) | `{r['spark']}` |")
    ld = c["load"]
    if ld:
        pct = f" ({_signed(ld['srpe_pct'], 0)} %)" if ld["srpe_pct"] is not None else ""
        for lab, key in (("Sesiones", "sessions"), ("Días con actividad", "days"), ("sRPE total", "srpe")):
            d = ld["prev"][key] - ld["before"][key]
            extra = pct if key == "srpe" else ""
            L.append(f"| {lab} | {ld['before'][key]} | {ld['prev'][key]} | {_signed(d, 0)}{extra} | {ld['current'][key]} | "
                     + (f"`{ld['spark']}`" if key == "srpe" else "") + " |")
    else:
        L.append("| Carga (sesiones, sRPE) | — | — | no comparable | — | — |")
        L.append(f"\n_Carga sin comparar: {c['load_reason']}. Una sesión sin registro no demuestra un día de descanso._")
    if not c["comparable"]:
        L.append("\n_Faltan días en alguna de las dos semanas: no se muestran porcentajes y las diferencias exigen al menos "
                 f"{MIN_DAYS} días con dato._")
    L.append("\n_Barras: ▁ valor más bajo, █ más alto de las últimas 4 semanas; «·» sin datos suficientes._")
    return "\n".join(L) + "\n"
