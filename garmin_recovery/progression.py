"""Progresión por ejercicio (V7.15).

Lee los bloques de fuerza de crossfit_insights.json (detail_json confirmado por el atleta), acumula un historial
propio en exercise_history.json —para que las sesiones no desaparezcan al salir de la ventana de Garmin— y compara
cada ejercicio repetido entre sesiones. Es descriptivo: no atribuye causas ni estima 1RM.

Las funciones son puras (no leen reloj ni red); solo `main` toca ficheros.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

SCHEMA_VERSION = 1
HISTORY = Path("exercise_history.json")
SOURCE = Path("crossfit_insights.json")
UNITS = {
    "kg_total_barra": "barra",
    "kg_indicado_maquina": "máquina",
    "kg_total_dos_mancuernas": "mancuernas (total)",
    "kg_total_dos_lados": "máquina (dos lados)",
}
SKIP_UNITS = {"peso_corporal"}  # sin carga externa: no se compara por kilos
SKIP_TYPES = {"metcon", "warmup", "skill"}
EPS = 0.01


def norm(text) -> str:
    t = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", t)).strip()


def _num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _reps(s: dict):
    r = _num(s.get("reps"))
    if r is not None:
        return r
    parts = [_num(v) for k, v in s.items() if k.endswith("_reps")]
    parts = [p for p in parts if p is not None]
    return sum(parts) if parts else None


def _sets(raw) -> tuple[list[dict], bool]:
    """Series con carga conocida (se excluye la barra vacía de calentamiento). `complete` = ninguna serie sin dato."""
    out, complete = [], True
    for s in raw or []:
        if not isinstance(s, dict) or s.get("bar_empty"):
            continue
        load, reps = _num(s.get("load_kg")), _reps(s)
        count = _num(s.get("count")) or 1
        if load is None or reps is None or load <= 0:
            complete = False
            continue
        out.append({"reps": reps, "load": load, "count": count})
    return out, complete


def _containers(detail: dict):
    """Rinde (nombre, unidad, series_crudas, rpe) de cada ejercicio de fuerza que aparezca en el detalle."""
    if not isinstance(detail, dict) or detail.get("type") in SKIP_TYPES:
        return
    for ex in detail.get("exercises") or []:
        if isinstance(ex, dict):
            yield ex.get("name"), ex.get("load_unit"), ex.get("sets"), ex.get("rpe")
    if isinstance(detail.get("exercise"), str) and isinstance(detail.get("sets"), list) and detail.get("type") != "skill":
        yield detail["exercise"], detail.get("load_unit"), detail["sets"], detail.get("rpe")
    for block in detail.get("blocks") or []:
        if isinstance(block, dict):
            for ex in block.get("exercises") or []:
                if isinstance(ex, dict):
                    yield ex.get("name"), ex.get("load_unit"), ex.get("sets"), ex.get("rpe", block.get("rpe"))


def extract_entries(crossfit: dict) -> tuple[dict[str, dict], set[str]]:
    """(entradas por clave, ids de actividad vistos). Una entrada = un ejercicio en una sesión."""
    entries: dict[str, dict] = {}
    seen: set[str] = set()
    for act in (crossfit or {}).get("activities") or []:
        if not isinstance(act, dict) or not act.get("date"):
            continue
        aid = str(act.get("activity_id") or "")
        seen.add(aid)
        for bi, block in enumerate(act.get("manual_blocks") or []):
            detail = block.get("detail_json") if isinstance(block, dict) else None
            for name, unit, raw, rpe in _containers(detail):
                if not name or unit in SKIP_UNITS or "calentamiento" in norm(name):
                    continue
                sets, complete = _sets(raw)
                if not sets:
                    continue
                key = f"{act['date']}|{aid}|{bi}|{norm(name)}|{unit}"
                prev = entries.get(key)
                if prev:  # mismo ejercicio dos veces en el mismo bloque: se suman las series
                    sets = prev["sets"] + sets
                    complete = complete and prev["volume_complete"]
                top = max(sets, key=lambda s: (s["load"], s["reps"]))
                entries[key] = {
                    "date": act["date"], "activity_id": aid, "activity": (block.get("activity") or "")[:200],  # V8.7: se recorta al mostrarlo, con «…»
                    "exercise": str(name), "key": norm(name), "unit": unit or "", "unit_label": UNITS.get(unit or "", unit or "sin unidad"),
                    "top_load": top["load"], "top_reps": top["reps"],
                    "volume": round(sum(s["load"] * s["reps"] * s["count"] for s in sets), 1),
                    "volume_complete": complete, "work_sets": int(sum(s["count"] for s in sets)),
                    "sets": sets, "rpe": _num(rpe),
                }
    return entries, seen


def merge(old: dict[str, dict] | None, new: dict[str, dict], seen_ids: set[str]) -> dict[str, dict]:
    """Las actividades vigentes sustituyen a sus entradas anteriores (por si se corrigió el registro); el resto se conserva."""
    kept = {k: v for k, v in (old or {}).items() if str(v.get("activity_id") or "") not in seen_ids}
    kept.update(new)
    return dict(sorted(kept.items()))


def series(entries: dict[str, dict]) -> list[dict]:
    """Un ejercicio (nombre + unidad) con sus puntos por fecha; si hay dos bloques el mismo día se combinan."""
    groups: dict[tuple[str, str], dict] = {}
    for e in entries.values():
        g = groups.setdefault((e["key"], e["unit"]), {"name": e["exercise"], "unit": e["unit_label"], "by_date": {}})
        d = g["by_date"].get(e["date"])
        if d is None:
            g["by_date"][e["date"]] = {"date": e["date"], "top_load": e["top_load"], "top_reps": e["top_reps"],
                                      "volume": e["volume"], "volume_complete": e["volume_complete"],
                                      "work_sets": e["work_sets"], "rpe": e["rpe"], "activity": e["activity"]}
        else:
            if (e["top_load"], e["top_reps"]) > (d["top_load"], d["top_reps"]):
                d["top_load"], d["top_reps"] = e["top_load"], e["top_reps"]
            d["volume"] = round(d["volume"] + e["volume"], 1)
            d["volume_complete"] = d["volume_complete"] and e["volume_complete"]
            d["work_sets"] += e["work_sets"]
    out = []
    for g in groups.values():
        pts = sorted(g["by_date"].values(), key=lambda p: p["date"])
        out.append(_judge({"name": g["name"], "unit": g["unit"], "points": pts}))
    out.sort(key=lambda s: (len(s["points"]) < 2, -len(s["points"]), s["name"]))
    return out


def _judge(s: dict) -> dict:
    pts = s["points"]
    s["sessions"] = len(pts)
    s["comparable"] = len(pts) >= 2
    s["best_load"] = max(p["top_load"] for p in pts)
    s["state"] = None
    if s["comparable"]:
        last, prev = pts[-1], pts[-2]
        delta = round(last["top_load"] - prev["top_load"], 2)
        s["delta_prev"] = delta
        s["delta_first"] = round(last["top_load"] - pts[0]["top_load"], 2)
        s["state"] = "up" if delta > EPS else "down" if delta < -EPS else "flat"
        s["new_best"] = last["top_load"] > max(p["top_load"] for p in pts[:-1]) + EPS
        s["rep_scheme_differs"] = abs((last["top_reps"] or 0) - (prev["top_reps"] or 0)) >= 2
        if last["volume_complete"] and prev["volume_complete"] and prev["volume"] > 0:
            s["volume_change_pct"] = round((last["volume"] - prev["volume"]) / prev["volume"] * 100)
        else:
            s["volume_change_pct"] = None
    return s


def summary(items: list[dict]) -> dict:
    comp = [s for s in items if s["comparable"]]
    up = sum(1 for s in comp if s["state"] == "up")
    down = sum(1 for s in comp if s["state"] == "down")
    flat = len(comp) - up - down
    text = None
    if comp:
        text = (f"{len(comp)} ejercicio{'s' if len(comp) != 1 else ''} con más de una sesión: {up} suben, {flat} igual, {down} bajan "
                "su mejor carga frente a la sesión anterior.")
    return {"available": bool(comp), "exercises": len(items), "comparable": len(comp), "up": up, "flat": flat, "down": down,
            "text": text,
            "caution": ("Con pocas sesiones por ejercicio es una comparación puntual, no una tendencia; distintas series y repeticiones "
                        "hacen que la mejor carga no siempre sea comparable. Descriptivo: sin causas." if comp else None)}


def build(history: dict | None, crossfit: dict | None = None) -> dict:
    """Historial guardado + sesiones vigentes de crossfit_insights → ejercicios con su comparación."""
    entries = dict((history or {}).get("entries") or {})
    if crossfit:
        new, seen = extract_entries(crossfit)
        entries = merge(entries, new, seen)
    items = series(entries)
    return {"entries": entries, "items": items, "summary": summary(items)}


def main() -> None:
    def load(p: Path):
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
    cf = load(SOURCE) or {}
    built = build(load(HISTORY), cf)
    out = {"schema_version": SCHEMA_VERSION, "generated_at": cf.get("generated_at"),
           "note": "Historial de ejercicios de fuerza confirmados por el atleta; se acumula y no se borra al salir de la ventana de Garmin.",
           "entries": built["entries"]}
    HISTORY.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    s = built["summary"]
    print(json.dumps({"entries": len(built["entries"]), "exercises": s["exercises"], "comparable": s["comparable"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
