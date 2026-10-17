"""Sesiones planificadas (pestaña `Planificados`) ajustadas a la decisión del día.

Fuente: ``PLANNED_CSV_URL`` (pestaña publicada como CSV, guardada como secreto
de GitHub) o, si no existe, ``planned_sessions.csv`` en la raíz del repo.

Reglas transparentes y conservadoras: el ajuste nunca supera el RPE máximo de
``decision.guidance`` y en rojo/pendiente sustituye cargas pesadas y WOD por
técnica, movilidad o zona 2. No se inventan cargas: si la prescripción no trae
cifras, el ajuste se expresa en porcentajes y RPE.
"""
from __future__ import annotations

import csv
import io
import math
import os
import re
import urllib.request
from pathlib import Path

DONE_STATES = {"REALIZADO", "REALIZADO DIFERENTE", "SUSTITUIDO", "CANCELADO", "HECHO"}
HEADERS = {
    "Fecha": "date", "Hora": "time", "Actividad": "activity", "Formato": "format",
    "Carga prevista (kg)": "load_text", "Estado": "status", "RPE real": "rpe_real", "Notas": "notes",
    "Tipo": "type", "Ejercicio principal": "main_exercise", "RPE objetivo": "rpe_target",
    "Duración (min)": "duration_min", "Unidad de carga": "load_unit", "ID actividad": "activity_id",
}
TYPES = {"fuerza": "Fuerza", "halterofilia": "Halterofilia", "wod": "WOD", "metcon": "WOD",
         "técnica": "Técnica", "tecnica": "Técnica", "skill": "Técnica", "aeróbico": "Aeróbico",
         "aerobico": "Aeróbico", "cardio": "Aeróbico", "movilidad": "Movilidad"}


def _num(text):
    try:
        return float(str(text).replace(",", ".").strip())
    except (TypeError, ValueError):
        return None


def parse_rows(text: str) -> list[dict]:
    rows = []
    for raw in csv.DictReader(io.StringIO(text)):
        row = {HEADERS.get((k or "").strip(), (k or "").strip()): (v or "").strip() for k, v in raw.items()}
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", row.get("date", "")):
            continue
        rows.append(row)
    return rows


def load_planned(root: str | Path, env: dict | None = None, opener=urllib.request.urlopen) -> tuple[list[dict], str]:
    env = os.environ if env is None else env
    url = (env.get("PLANNED_CSV_URL") or "").strip()
    if url:
        try:
            with opener(url, timeout=15) as resp:
                return parse_rows(resp.read().decode("utf-8-sig")), "planificados_en_vivo"
        except Exception as exc:  # noqa: BLE001 — la fuente es opcional, nunca bloquea
            return [], f"error_lectura:{type(exc).__name__}"
    local = Path(root) / "planned_sessions.csv"
    if local.exists():
        return parse_rows(local.read_text(encoding="utf-8-sig")), "planned_sessions.csv"
    return [], "no_configurado"


def session_type(row: dict) -> str:
    t = TYPES.get((row.get("type") or "").strip().lower())
    if t:
        return t
    from .report import categorize
    cat = categorize({"label": f"{row.get('activity', '')} {row.get('main_exercise', '')}"})
    return {"Sin detalle": "Fuerza" if row.get("load_text") else "WOD"}.get(cat, cat)


def parse_scheme(fmt: str):
    m = re.search(r"(\d+)\s*[×xX]\s*(\d+)", fmt or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def parse_load_spec(text: str) -> dict:
    """Interpreta la carga prevista sin inventar cifras.

    * ``80 % 1RM`` / ``75-80 %``      → porcentajes (relativos, no kg)
    * ``2x20`` / ``2 × 22,5``           → kg por implemento (mancuernas/kettlebells)
    * ``150–160`` · ``150,160`` · ``150/160`` · ``167,5`` → kg; la coma con 1–2 decimales es decimal
    """
    t = text or ""
    nums = [float(x.replace(",", ".")) for x in re.findall(r"\d+(?:[.,]\d{1,2})?(?!\d)", t)]
    if "%" in t:  # solo cuentan los números unidos a "%" (o rangos "75-80 %"), no series ni repeticiones
        pcts = []
        for a, b in re.findall(r"(\d+(?:[.,]\d+)?)\s*(?:[-–]\s*(\d+(?:[.,]\d+)?)\s*)?%", t):
            pcts += [float(x.replace(",", ".")) for x in (a, b) if x]
        return {"kind": "percent", "values": [n for n in pcts if 0 < n <= 100]}
    m = re.fullmatch(r"\s*(\d+)\s*[×xX]\s*(\d+(?:[.,]\d{1,2})?)\s*(kg)?\s*", t)
    if m:
        return {"kind": "per_implement", "count": int(m.group(1)), "values": [float(m.group(2).replace(",", "."))]}
    return {"kind": "kg", "values": nums}


def parse_loads(text: str) -> list[float]:
    spec = parse_load_spec(text)
    return spec["values"] if spec["kind"] == "kg" else []


def reduced_sets(sets: int) -> int:
    """75 % de las series, con al menos una serie menos cuando hay más de una."""
    if sets <= 1:
        return 1
    return max(1, min(sets - 1, int(sets * 0.75 + 0.5)))


def parse_rpe(text) -> float | None:
    """'7-8' o '7–8' → 7 (límite inferior, el más prudente)."""
    nums = [float(x.replace(",", ".")) for x in re.findall(r"\d+(?:[.,]\d+)?", str(text or ""))]
    return min(nums) if nums else None


def plate(x: float, step: float = 2.5) -> float:
    return math.floor(x / step + 1e-9) * step


def _kg(v: float) -> str:
    return (f"{v:.1f}".rstrip("0").rstrip(".")).replace(".", ",")


def adjust(row: dict, zone: str, rpe_cap: int | None) -> dict:
    kind = session_type(row)
    target = parse_rpe(row.get("rpe_target"))
    scheme = parse_scheme(row.get("format", ""))
    spec = parse_load_spec(row.get("load_text", ""))
    loads = spec["values"] if spec["kind"] == "kg" else []
    dur = _num(row.get("duration_min"))
    load_txt = row.get("load_text") or ""
    if load_txt and spec["kind"] != "percent" and "kg" not in load_txt.lower():
        load_txt += " kg"
    planned_txt = " · ".join(x for x in (row.get("activity"), row.get("format"), load_txt,
                                         f"RPE {row['rpe_target']}" if row.get("rpe_target") else "",
                                         f"{row['duration_min']} min" if row.get("duration_min") else "") if x)
    cap = rpe_cap if rpe_cap is not None else 6
    rpe = min(int(target), cap) if target else cap
    out = {"date": row.get("date"), "time": row.get("time"), "type": kind, "planned": planned_txt,
           "activity_id": row.get("activity_id") or None, "rpe_max": rpe}

    if zone == "green":
        out.update(action="mantener", adjusted="Según lo planificado.", rule="Disponibilidad verde.")
        return out

    if zone in ("red", "unavailable"):
        substitute = {
            "Fuerza": "Técnica del patrón con barra vacía o PVC (15–20 min) + movilidad. Sin cargas.",
            "Halterofilia": "Técnica con PVC o barra vacía (15–20 min): posiciones y recepciones. Sin cargas.",
            "WOD": "Zona 2 suave 30–40 min (remo, bici o caminata), pudiendo hablar.",
            "Técnica": "Técnica ligera ≤ 15 min, sin fatiga.",
            "Aeróbico": "Zona 2 suave ≤ 40 min.",
            "Movilidad": "Movilidad tal como está planificada.",
        }[kind]
        if zone == "unavailable" and kind in ("Técnica", "Movilidad", "Aeróbico"):
            substitute += " Revisa de nuevo cuando se confirme el sueño."
        action = "mantener" if kind == "Movilidad" else "reducir" if kind in ("Técnica", "Aeróbico") else "sustituir"
        out.update(action=action, adjusted=substitute,
                   rpe_max=min(rpe, 4 if zone == "red" else 6),
                   rule="Decisión roja: sin cargas pesadas ni WOD." if zone == "red"
                   else "Datos de hoy pendientes: no se autoriza intensidad alta.")
        return out

    # Ámbar
    parts = []
    if kind in ("Fuerza", "Halterofilia"):
        factor = 0.90 if kind == "Fuerza" else 0.80
        if scheme:
            sets, reps = scheme
            parts.append(f"{reduced_sets(sets)} × {reps}")
        else:
            parts.append("−25 % de series")
        if spec["kind"] == "percent" and spec["values"]:
            pcts = [p_ * factor for p_ in spec["values"]]
            rng = "–".join(f"{x:.0f}" for x in (min(pcts), max(pcts))) if len(set(round(x) for x in pcts)) > 1 else f"{pcts[0]:.0f}"
            parts.append(f"intensidad máx. {rng} % de tu referencia ({int(factor * 100)} % de lo previsto)")
        elif spec["kind"] == "per_implement" and spec["values"]:
            per = plate(spec["values"][0] * factor, 1.0 if spec["values"][0] < 30 else 2.0)
            parts.append(f"{spec['count']} × {_kg(per)} kg por implemento ({int(factor * 100)} % de lo previsto)")
        elif loads:
            adj = [plate(x * factor) for x in loads]
            rng = "–".join(_kg(x) for x in (min(adj), max(adj))) if len(set(adj)) > 1 else _kg(adj[0])
            parts.append(f"carga máx. {rng} kg ({int(factor * 100)} % de lo previsto)")
        else:
            parts.append(f"cargas al {int(factor * 100)} % de lo habitual")
        parts.append("2–3 repeticiones en reserva, sin fallo" if kind == "Fuerza" else "técnica, sin singles pesados")
    elif kind == "WOD":
        if dur:
            parts.append(f"{int(round(dur * 0.75))} min en lugar de {int(dur)}")
        else:
            parts.append("−20–30 % de volumen o tiempo")
        parts.append("ritmo controlado, sin all-out; escala cargas un 10–20 %")
    else:
        parts.append("según lo planificado, sin buscar intensidad")
    out.update(action="reducir", adjusted="; ".join(parts) + ".", rule="Decisión ámbar: entrenar con control.")
    return out


def plan_block(rows: list[dict], day: str, tomorrow: str, decision: dict, sessions: list[dict], source: str) -> dict:
    zone = decision.get("zone", "unavailable")
    cap = (decision.get("guidance") or {}).get("rpe_max")
    pending = [r for r in rows if (r.get("status") or "").upper() not in DONE_STATES]
    today = [adjust(r, zone, cap) for r in pending if r.get("date") == day]
    tomorrow_rows = [{"date": r["date"], "time": r.get("time"), "type": session_type(r),
                      "planned": " · ".join(x for x in (r.get("activity"), r.get("format"), r.get("load_text")) if x)}
                     for r in pending if r.get("date") == tomorrow]
    by_id = {s["id"]: s for s in sessions}
    done = []
    for r in (x for x in rows if x.get("date") == day):
        sid = r.get("activity_id")
        s = by_id.get(sid) if sid else None
        if s:
            exceeded = cap is not None and s.get("rpe") is not None and s["rpe"] > cap
            done.append({"planned": r.get("activity"), "activity_id": sid, "rpe": s.get("rpe"),
                         "load": s.get("load"), "rpe_cap": cap, "exceeded": exceeded})
    return {"source": source, "today": today, "tomorrow": tomorrow_rows, "done_check": done,
            "rows_loaded": len(rows)}


GENERIC_TYPES = ("Fuerza", "Halterofilia", "WOD", "Técnica", "Aeróbico", "Movilidad")


def rules_for_today(decision: dict) -> list[dict]:
    """Reglas de ajuste por tipo de sesión para quien planifica el mismo día."""
    zone = decision.get("zone", "unavailable")
    cap = (decision.get("guidance") or {}).get("rpe_max")
    out = []
    for kind in GENERIC_TYPES:
        a = adjust({"type": kind, "activity": kind}, zone, cap)
        out.append({"type": kind, "action": a["action"], "rule": a["adjusted"], "rpe_max": a["rpe_max"]})
    return out
