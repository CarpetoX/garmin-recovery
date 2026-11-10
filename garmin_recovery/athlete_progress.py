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
        per = cur.setdefault("per_date", {})
        for s in e.get("sets") or []:
            w, reps = _num(s.get("load")), _num(s.get("reps"))
            if not w or not reps or reps < 1:
                continue
            if reps <= EPLEY_MAX_REPS:
                est = w * (1 + reps / 30) if reps > 1 else w
                d = str(e.get("date") or "")[:10]
                if d and est > per.get(d, 0):
                    per[d] = est
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
        # V8.16: mejor 1RM estimado de cada sesión, para ver la tendencia aunque cambien series y repeticiones
        c["series"] = [{"date": d, "e1rm": round(v * 2) / 2} for d, v in sorted((c.pop("per_date", None) or {}).items())]
        c["delta"] = (c["series"][-1]["e1rm"] - c["series"][-2]["e1rm"]) if len(c["series"]) >= 2 else None
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
        for ms in d.get("milestones") if isinstance(d.get("milestones"), list) else []:  # V8.16: varios hitos en una sesión
            if isinstance(ms, str) and ms.strip():
                out.append({"date": r["date"], "kind": "hito", "title": ms.strip()[:1].upper() + ms.strip()[1:], "sub": "",
                            "skill": skill_of(ms)})
        if d.get("milestone") or m_h:
            perf = d.get("performed") if isinstance(d.get("performed"), dict) else {}
            reps = _num(perf.get("reps"))
            sub = (f"{reps:g} repeticiones" if reps else "") + (" enlazadas" if perf.get("unbroken") else " sueltas" if reps and perf.get("unbroken") is False else "")
            title = d.get("milestone") or m_h.group(1)
            out.append({"date": r["date"], "kind": "hito", "title": title, "sub": sub.strip(),
                        "skill": skill_of(d.get("exercise") or title)})
        elif m_t or d.get("type") == "skill":
            ex = d.get("exercise") or (m_t.group(1) if m_t else r["name"])
            out.append({"date": r["date"], "kind": "tecnica", "title": str(ex)[:1].upper() + str(ex)[1:],
                        "sub": level_of(d), "skill": skill_of(ex)})
    seen, uniq = set(), []  # V8.16: un hito declarado en «milestone» y en «milestones» cuenta una vez
    for x in out:
        k = (x["date"], x["kind"], x["title"].lower())
        if k not in seen:
            seen.add(k)
            uniq.append(x)
    uniq.sort(key=lambda x: (x["date"], x["kind"] == "hito"), reverse=True)
    return uniq


SKILLS = [("Pino caminando", r"handstand walk|pino caminando"), ("Pino estático", r"handstand hold|pino est"),
          ("Handstand push-up", r"handstand|hspu"), ("Bar muscle up", r"bar muscle|\bbmu\b"),
          ("Ring muscle up", r"ring muscle"), ("Toes to bar", r"toes[ -]?to[ -]?bar|t2b"),
          ("Comba", r"double[ -]?under|crossover|comba|single[ -]?under|jump rope|saltar a la comba"), ("Pistol", r"pistol"),
          ("Rope climb", r"rope climb|trepa|cuerda")]


def skill_of(text) -> str:
    """Habilidad a la que pertenece un ejercicio o hito (agrupa «HSPU», «HSPU en déficit»…)."""
    t = str(text or "").lower()
    for name, rx in SKILLS:
        if re.search(rx, t):
            return name
    t = t.strip()
    return t[:1].upper() + t[1:] if t else "Otra"


def level_of(d: dict) -> str:
    """Nivel declarado en una sesión de técnica: déficit, repeticiones máximas o progresión, tal como constan."""
    bits = []
    deficit = d.get("deficit") if isinstance(d.get("deficit"), dict) else None
    if deficit:
        label = deficit.get("label") or " + ".join(f'disco {p["load_kg"]:g} kg' for p in deficit.get("plates") or []
                                                    if isinstance(p, dict) and _num(p.get("load_kg")) is not None)
        if label:
            bits.append(f"déficit {label}")
    reps = _num(d.get("max_reps_declared"))
    if reps:
        bits.append(f"hasta {reps:g} repeticiones")
    prog = d.get("progression")
    if isinstance(prog, str) and prog.strip():
        bits.append(f"progresión: {prog.strip()}")
    return " · ".join(bits)


def skill_groups(items: list[dict]) -> list[dict]:
    """Resumen por habilidad: sesiones, primera y última fecha, hitos y último nivel declarado."""
    groups: dict[str, dict] = {}
    for x in sorted(items, key=lambda i: i["date"]):
        g = groups.setdefault(x.get("skill") or x["title"], {"skill": x.get("skill") or x["title"], "sessions": set(),
                                                             "first": x["date"], "last": x["date"], "hitos": [], "level": None,
                                                             "level_date": None, "levels": []})
        g["last"] = x["date"]
        if x["kind"] == "hito":
            if not any(h["date"] == x["date"] and h["title"].lower() == x["title"].lower() for h in g["hitos"]):
                g["hitos"].append({"date": x["date"], "title": x["title"]})
        else:
            g["sessions"].add(x["date"])
            if x.get("sub"):
                g["level"], g["level_date"] = x["sub"], x["date"]
                g["levels"].append({"date": x["date"], "level": x["sub"]})
    out = [dict(g, sessions=len(g["sessions"])) for g in groups.values()]
    out.sort(key=lambda g: g["last"], reverse=True)
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
    sk = skills(rows)
    return {"benchmarks": benchmarks(rows), "maxes": estimated_max(hist.get("entries")), "skills": sk,
            "skill_groups": skill_groups(sk), "load_history": load_history(dates, today)}
