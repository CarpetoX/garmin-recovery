"""V8.13: progresión del atleta más allá de la sesión anterior.

- Benchmarks: WOD o pruebas marcadas en la hoja (``"benchmark": "<nombre>"`` en el Detalle JSON) o WOD idénticos
  repetidos (mismo nombre de actividad). Se comparan solo consigo mismos.
- Máximos estimados: límite inferior del 1RM por Epley (sin RIR) a partir de series de 1–10 repeticiones con barra,
  junto al mejor single real. Nunca se estima desde el RPE de la sesión (invariante 5).
- Gimnasia y técnica: hitos y sesiones de técnica en una línea de tiempo.
- Historial de carga: aviso mientras haya menos de 42 días de datos (la carga crónica aún no es fiable).
Todo es descriptivo: solo cifras presentes en la hoja o en ``exercise_history.json``.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

EPLEY_MAX_REPS = 10
LOAD_HISTORY_DAYS = 42


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _read(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def sheet_rows(root: Path) -> list[dict]:
    """Filas A:H de la hoja RPE (instantánea de ``training_feedback.json``) con el Detalle JSON ya leído."""
    tf = _read(Path(root) / "training_feedback.json") or {}
    out = []
    for r in tf.get("source_rows_AH") or []:
        if not isinstance(r, dict) or not r.get("Fecha"):
            continue
        try:
            detail = json.loads(r.get("Detalle JSON") or "{}")
        except ValueError:
            detail = {}
        out.append({"date": str(r["Fecha"])[:10], "id": r.get("ID actividad") or "", "name": str(r.get("Actividad") or "").strip(),
                    "rpe": r.get("RPE") or "", "notes": r.get("Notas") or "", "detail": detail if isinstance(detail, dict) else {}})
    return out


def _result(detail: dict):
    """(valor, mejor, texto) del resultado de un WOD o prueba; mejor ∈ lower | higher."""
    perf = detail.get("performed") if isinstance(detail.get("performed"), dict) else {}
    t = _num(detail.get("finish_time_seconds"))
    if t is not None and perf.get("completed", True) is not False:
        return t, "lower", f"{int(t // 60)}:{int(t % 60):02d}"
    reps = _num(perf.get("total_reps"))
    if reps is not None:
        rounds = _num(perf.get("rounds_complete"))
        extra = _num(perf.get("extra_reps"))
        txt = f"{rounds:g} rondas" + (f" + {extra:g}" if extra else "") + f" · {reps:g} reps" if rounds is not None else f"{reps:g} reps"
        return reps, "higher", txt
    load = _num(detail.get("benchmark_load_kg"))
    if load is not None:
        return load, "higher", f"{load:g} kg"
    return None, None, None


def benchmarks(rows: list[dict]) -> list[dict]:
    groups: dict[str, list] = {}
    for r in rows:
        d = r["detail"]
        name = d.get("benchmark") if isinstance(d.get("benchmark"), str) and d["benchmark"].strip() else None
        if not name and d.get("type") == "metcon":
            name = r["name"]  # WOD idéntico repetido: el nombre incluye movimientos y cargas
        if not name:
            continue
        value, better, text = _result(d)
        if value is None:
            continue
        groups.setdefault(name.strip(), []).append({"date": r["date"], "value": value, "better": better, "text": text,
                                                    "rpe": r["rpe"], "marked": bool(d.get("benchmark"))})
    out = []
    for name, pts in groups.items():
        pts.sort(key=lambda p: p["date"])
        marked = any(p["marked"] for p in pts)
        if len(pts) < 2 and not marked:
            continue  # un WOD hecho una vez no es aún una referencia
        better = pts[-1]["better"]
        best = (min if better == "lower" else max)(p["value"] for p in pts)
        state = None
        if len(pts) >= 2:
            a, b = pts[-2]["value"], pts[-1]["value"]
            state = "flat" if a == b else ("up" if (b < a if better == "lower" else b > a) else "down")
        out.append({"name": name, "points": pts, "better": better, "state": state, "best": best,
                    "is_best": pts[-1]["value"] == best and len(pts) >= 2, "marked": marked})
    out.sort(key=lambda b: b["points"][-1]["date"], reverse=True)
    return out


def estimated_max(entries) -> list[dict]:
    """Por ejercicio de barra: mejor 1RM mínimo (Epley) y mejor single real, con su fecha."""
    items = entries.values() if isinstance(entries, dict) else entries or []
    by: dict[str, dict] = {}
    for e in items:
        if not isinstance(e, dict) or e.get("unit") != "kg_total_barra":
            continue
        name = str(e.get("exercise") or "").strip().lower()
        if not name or "+" in name or "complex" in name:
            continue  # un complex no es un levantamiento aislado: Epley no aplica
        cur = by.setdefault(name, {"name": name, "e1rm": None, "e1rm_from": None, "single": None, "single_date": None, "sessions": set()})
        cur["sessions"].add(e.get("date"))
        for s in e.get("sets") or []:
            w, reps = _num(s.get("load")), _num(s.get("reps"))
            if not w or not reps or reps < 1:
                continue
            if reps <= EPLEY_MAX_REPS:
                est = w * (1 + reps / 30) if reps > 1 else w
                if cur["e1rm"] is None or est > cur["e1rm"]:
                    cur["e1rm"], cur["e1rm_from"] = est, {"date": e.get("date"), "load": w, "reps": reps}
            if reps == 1 and (cur["single"] is None or w > cur["single"]):
                cur["single"], cur["single_date"] = w, e.get("date")
    out = []
    for c in by.values():
        if c["e1rm"] is None:
            continue
        c["e1rm"] = round(c["e1rm"] * 2) / 2  # al medio kilo
        c["sessions"] = len(c["sessions"])
        out.append(c)
    out.sort(key=lambda c: -c["e1rm"])
    return out


_TECH = re.compile(r"^t[ée]cnica\s*-\s*(.+)$", re.I)
_HITO = re.compile(r"^hito\s*-\s*(.+)$", re.I)


def skills(rows: list[dict]) -> list[dict]:
    """Hitos y sesiones de técnica, del más reciente al más antiguo."""
    out = []
    for r in rows:
        d = r["detail"]
        m_h, m_t = _HITO.match(r["name"]), _TECH.match(r["name"])
        if d.get("milestone") or m_h:
            perf = d.get("performed") if isinstance(d.get("performed"), dict) else {}
            reps = _num(perf.get("reps"))
            sub = (f"{reps:g} repeticiones" if reps else "") + (" enlazadas" if perf.get("unbroken") else " sueltas" if reps and perf.get("unbroken") is False else "")
            out.append({"date": r["date"], "kind": "hito", "title": d.get("milestone") or m_h.group(1), "sub": sub.strip()})
        elif m_t or d.get("type") == "skill":
            ex = d.get("exercise") or (m_t.group(1) if m_t else r["name"])
            prog = d.get("progression")
            out.append({"date": r["date"], "kind": "tecnica", "title": str(ex)[:1].upper() + str(ex)[1:],
                        "sub": f"progresión: {prog}" if isinstance(prog, str) and prog else ""})
    out.sort(key=lambda x: (x["date"], x["kind"] == "hito"), reverse=True)
    return out


def load_history(activity_dates: list[str], today: str) -> dict:
    ds = sorted(d for d in activity_dates if isinstance(d, str) and len(d) >= 10)
    if not ds:
        return {"available": False}
    days = (date.fromisoformat(today) - date.fromisoformat(ds[0][:10])).days + 1
    reliable = days >= LOAD_HISTORY_DAYS
    return {"available": True, "first": ds[0][:10], "days": days, "reliable": reliable,
            "note": None if reliable else (f"Solo hay {days} días de historial (desde el {ds[0][8:10]}/{ds[0][5:7]}): la carga crónica (CTL) "
                                           f"arranca de cero y la relación aguda/crónica sale exagerada hasta tener unos {LOAD_HISTORY_DAYS} días. "
                                           "No es que estés en baja forma.")}


def build(root: str | Path, today: str) -> dict:
    root = Path(root)
    rows = sheet_rows(root)
    hist = _read(root / "exercise_history.json") or {}
    acts = _read(root / "activities.json")
    dates = [str(a.get("date") or a.get("start_date_local") or "")[:10] for a in acts if isinstance(a, dict)] if isinstance(acts, list) else []
    return {"benchmarks": benchmarks(rows), "maxes": estimated_max(hist.get("entries")), "skills": skills(rows),
            "load_history": load_history(dates, today)}
