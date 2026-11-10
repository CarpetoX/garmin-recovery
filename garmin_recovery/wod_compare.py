"""WODs parecidos y repetidos (V8.15). Funciones puras.

Cada metcon se reduce a sus familias de movimiento (snatch, dominadas, wall ball…) a partir de lo que consta en
`detail_json`. Dos metcons son «parecidos» si comparten al menos dos familias y la mitad de todas las que aparecen;
son «repetidos» si además tienen el mismo formato y los mismos movimientos con las mismas cargas. La comparación es
orientativa: formato, cargas y variantes (butterfly frente a chest to bar) cambian el esfuerzo, y se muestran tal cual.
"""
from __future__ import annotations

import re
import unicodedata

FAMILIES: list[tuple[str, str]] = [
    ("db snatch", r"(dumbbell|db|mancuerna).*snatch|snatch.*(dumbbell|mancuerna)"),
    ("snatch", r"snatch|arrancada"),
    ("clean", r"clean|cargada"),
    ("jerk", r"jerk|envion|shoulder to overhead|s2oh"),
    ("push press", r"push press"),
    ("thruster", r"thruster"),
    ("dominadas", r"pull[ -]?up|chest[ -]?to[ -]?bar|c2b|butterfly|dominada|muscle[ -]?up"),
    ("toes to bar", r"toes[ -]?to[ -]?bar|t2b"),
    ("hspu", r"handstand|hspu"),
    ("burpee", r"burpee"),
    ("wall ball", r"wall[ -]?ball"),
    ("box jump", r"box[ -]?jump|cajon"),
    ("step up", r"step[ -]?up"),
    ("swing", r"swing"),
    ("high pull", r"high pull"),
    ("peso muerto", r"deadlift|peso muerto"),
    ("sentadilla", r"squat|sentadilla"),
    ("devil press", r"devil press"),
    ("sit-up", r"sit[ -]?up|abdominal"),
    ("v-sit", r"v[ -]?sit"),
    ("double unders", r"double[ -]?under|comba"),
    ("carrera", r"carrera|\brun(ning)?\b"),
    ("remo", r"\bremo\b|(?<!ring )(?<!over )(?<!upright )\brow(er|ing)?\b"),
    ("skierg", r"\bski(erg|\b)"),
    ("bici", r"bike|bici|assault|echo"),
    ("farmer", r"farmer"),
]
_COMPILED = [(f, re.compile(p)) for f, p in FAMILIES]


def _plain(text) -> str:
    t = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", t).strip()


def family(name) -> str | None:
    t = _plain(name)
    for fam, rx in _COMPILED:
        if rx.search(t):
            return fam
    return None


def _items(d: dict) -> list[dict]:
    """Movimientos declarados (nombre y carga) en cualquiera de las formas que usa detail_json."""
    out: list[dict] = []
    for key in ("prescribed_round", "exercises"):
        for x in d.get(key) or []:
            if not isinstance(x, dict):
                continue
            if isinstance(x.get("exercises"), list):  # E2MO2M: intervalos con varios ejercicios
                out += [e for e in x["exercises"] if isinstance(e, dict)]
            else:
                out.append(x)
    for r in (d.get("rounds") if isinstance(d.get("rounds"), list) else [])[:1]:
        if isinstance(r, dict):
            for r2 in d["rounds"]:
                if isinstance(r2, dict) and r2.get("machine"):
                    out.append({"name": r2["machine"]})
            for k in r:
                if k.endswith("_sync_reps") or k.endswith("_reps"):
                    out.append({"name": k.replace("_sync_reps", "").replace("_reps", "").replace("_", " "),
                                "load_kg": r.get("dumbbell_kg") if "dumbbell" in k else None})
    if isinstance(d.get("exercise"), str):
        out.append({"name": d["exercise"], "load_kg": d.get("load_kg")})
    return [x for x in out if x.get("name") and _plain(x["name"]) != "descanso"]


def signature(d: dict | None) -> dict:
    d = d if isinstance(d, dict) else {}
    items = _items(d)
    fams = sorted({f for f in (family(x["name"]) for x in items) if f})
    exact = sorted({(_plain(x["name"]), x.get("load_kg") if isinstance(x.get("load_kg"), (int, float)) else None)
                    for x in items}, key=lambda t: (t[0], t[1] if t[1] is not None else -1))
    return {"families": fams, "exact": exact, "format": _plain(d.get("format")),
            "rounds": tuple(d.get("prescribed_rounds") or ()), "duration": d.get("duration_minutes") or d.get("time_cap_minutes")}


def similarity(a: dict, b: dict) -> float:
    fa, fb = set(a["families"]), set(b["families"])
    if not fa or not fb:
        return 0.0
    shared = fa & fb
    return len(shared) / len(fa | fb) if len(shared) >= 2 else 0.0


def is_repeat(a: dict, b: dict) -> bool:
    return bool(a["exact"]) and a["exact"] == b["exact"] and a["format"] == b["format"] \
        and a["rounds"] == b["rounds"] and a["duration"] == b["duration"]


def annotate(metcons: list[dict], details: dict[str, dict], limit: int = 3) -> list[dict]:
    """Añade a cada metcon `similar` (los más parecidos, más recientes primero) y `repeat_of` (repeticiones exactas).

    `details` va de activity_id + fecha a detail_json. No toca nada más del metcon.
    """
    sigs = [signature(details.get(m.get("key") or m.get("activity_id"))) for m in metcons]
    for i, m in enumerate(metcons):
        cands = []
        for j, o in enumerate(metcons):
            if i == j:
                continue
            rep = is_repeat(sigs[i], sigs[j])
            s = 1.0 if rep else similarity(sigs[i], sigs[j])
            if s >= 0.5:
                fi, fj = set(sigs[i]["families"]), set(sigs[j]["families"])
                shared = sorted(fi & fj)
                cands.append({"date": o["date"], "activity_id": o.get("activity_id"), "format": o.get("format"),
                              "title": o.get("title"), "result": o.get("result"), "rpe": o.get("rpe"),
                              "timing": o.get("timing") or [], "shared": shared, "only_this": sorted(fi - fj),
                              "only_other": sorted(fj - fi), "score": round(s, 2), "repeat": rep})
        cands.sort(key=lambda c: (c["repeat"], c["score"], c["date"]), reverse=True)
        m["similar"] = cands[:limit]
        m["repeat_of"] = [c["date"] for c in cands if c["repeat"]]
        m["families"] = sigs[i]["families"]
    return metcons
