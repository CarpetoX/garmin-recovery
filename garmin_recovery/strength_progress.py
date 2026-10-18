"""Progresión de fuerza por ejercicio de barra (kg totales de barra), por semana ISO.

Solo compara ejercicios con la misma unidad (kg_total_barra). El 1RM es el límite inferior (Epley sin RIR)
que ya calcula muscle_load; no se estima desde el RPE. Una mejora entre semanas es una diferencia observada.
"""
from __future__ import annotations

from datetime import date, timedelta

WEEKS = 8
MAX_ROWS_PER_EXERCISE = 4


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _week(d: str) -> str:
    y, w, _ = date.fromisoformat(d).isocalendar()
    return f"{y}-S{w:02d}"


def compute(rows, today: str) -> dict:
    since = (date.fromisoformat(today) - timedelta(days=WEEKS * 7 - 1)).isoformat()
    seen, acc = set(), []
    for r in rows if isinstance(rows, list) else []:
        if not isinstance(r, dict) or r.get("load_unit") != "kg_total_barra" or r.get("equipment") not in (None, "barbell"):
            continue
        d, name = str(r.get("date") or ""), str(r.get("exercise") or "").strip().lower()
        if not d or d > today or d < since or not name or _num(r.get("top_set_kg")) is None:
            continue
        key = (r.get("activity_id"), d, name)
        if key in seen:
            continue
        seen.add(key)
        acc.append((name, d, r))
    by: dict = {}
    for name, d, r in acc:
        wk = by.setdefault(name, {}).setdefault(_week(d), {"best_kg": 0.0, "best_reps": None, "e1rm": None, "days": set()})
        kg, reps = r["top_set_kg"], r.get("top_set_reps")
        if kg > wk["best_kg"] or (kg == wk["best_kg"] and (_num(reps) or 0) > (wk["best_reps"] or 0)):
            wk["best_kg"], wk["best_reps"] = kg, reps
        e = _num(r.get("e1rm_min_kg"))
        if e is not None and (wk["e1rm"] is None or e > wk["e1rm"]):
            wk["e1rm"] = e
        wk["days"].add(d)
    out = {}
    for name, weeks in by.items():
        keys = sorted(weeks)[-MAX_ROWS_PER_EXERCISE:]
        out[name] = [dict(week=k, best_kg=weeks[k]["best_kg"], best_reps=weeks[k]["best_reps"], e1rm=weeks[k]["e1rm"],
                          sessions=len(weeks[k]["days"])) for k in keys]
    return out


def _kg(v):
    return f"{v:.1f}".rstrip("0").rstrip(".").replace(".", ",")


def to_markdown(res: dict) -> str:
    if not res:
        return "No hay series de barra con carga total registradas en las últimas 8 semanas."
    lines = ["| Ejercicio | Semana | Mejor serie | 1RM mínimo | Sesiones |", "|---|---|---|---|---|"]
    notes = []
    for name in sorted(res):
        rows = res[name]
        for r in rows:
            reps = f" × {int(r['best_reps'])}" if _num(r["best_reps"]) else ""
            e = f"{_kg(r['e1rm'])} kg" if r["e1rm"] is not None else "—"
            lines.append(f"| {name} | {r['week']} | {_kg(r['best_kg'])} kg{reps} | {e} | {r['sessions']} |")
        if len(rows) >= 2 and rows[-1]["e1rm"] is not None and rows[-2]["e1rm"] is not None:
            d = rows[-1]["e1rm"] - rows[-2]["e1rm"]
            notes.append(f"{name}: 1RM mínimo {'+' if d > 0 else ''}{_kg(d)} kg entre {rows[-2]['week']} y {rows[-1]['week']}")
    text = "\n".join(lines)
    if notes:
        text += "\n\nDiferencias entre las dos últimas semanas con datos: " + "; ".join(notes) + "."
    return text + ("\n\nSolo barra con carga total. El 1RM es un límite inferior (Epley sin RIR) y no se deduce del RPE; "
                   "las semanas sin registro no implican que no se entrenara ese ejercicio.")
