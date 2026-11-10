"""Encuesta diaria de sensaciones (V8.18). Puro, sin red.

El atleta responde en el chat cuatro preguntas (cansancio, agujetas, estrés, ánimo) y se guardan en
`sensaciones_registro.json`. Cada respuesta es un nivel 0–3 donde 0 es lo mejor (fresco, sin agujetas, estrés bajo,
muchas ganas) y 3 lo peor. Solo se describe lo que el atleta dice; no entra en los modelos de recuperación.
"""
from __future__ import annotations

import json
from datetime import date as _date, timedelta
from pathlib import Path

FILE = "sensaciones_registro.json"
ITEMS = [
    ("cansancio", "Cansancio", ["Fresco", "Algo cansado", "Cansado", "Muy cansado"]),
    ("agujetas", "Agujetas", ["Nada", "Leves", "Moderadas", "Fuertes"]),
    ("estres", "Estrés", ["Bajo", "Normal", "Alto", "Muy alto"]),
    ("animo", "Ánimo", ["Con muchas ganas", "Normal", "Pocas ganas", "Sin ganas"]),
]


def load(root: str | Path) -> list[dict]:
    try:
        data = json.loads((Path(root) / FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    entries = data.get("entries") if isinstance(data, dict) else None
    return [e for e in entries if isinstance(e, dict)] if isinstance(entries, list) else []


def level(entry: dict, key: str) -> int | None:
    v = (entry.get(key) or {}).get("level") if isinstance(entry.get(key), dict) else entry.get(key)
    return v if isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 3 else None


def by_date(entries: list[dict], today: str) -> dict[str, dict]:
    """Última encuesta de cada día (las fechas futuras o inválidas se ignoran)."""
    out: dict[str, dict] = {}
    for e in sorted(entries, key=lambda x: (str(x.get("date")), str(x.get("time") or ""))):
        d = str(e.get("date") or "")[:10]
        try:
            _date.fromisoformat(d)
        except ValueError:
            continue
        if d <= today:
            out[d] = e
    return out


def window(entries: list[dict], today: str, days: int = 14) -> list[dict]:
    """Una fila por día de la ventana, con el nivel de cada pregunta o None si no hubo encuesta."""
    t = _date.fromisoformat(today)
    bd = by_date(entries, today)
    rows = []
    for i in range(days - 1, -1, -1):
        d = (t - timedelta(days=i)).isoformat()
        e = bd.get(d)
        rows.append({"date": d, **{k: (level(e, k) if e else None) for k, _, _ in ITEMS}, "note": (e or {}).get("note")})
    return rows


def record(root: str | Path, day: str, answers: dict[str, str], time: str | None = None, note: str | None = None) -> dict:
    """Guarda una encuesta a partir de las etiquetas elegidas; devuelve la entrada. Rechaza etiquetas desconocidas."""
    entry: dict = {"date": day, "source": "encuesta en el chat"}
    if time:
        entry["time"] = time
    for key, _, labels in ITEMS:
        if key in answers:
            lab = answers[key]
            if lab not in labels:
                raise ValueError(f"respuesta desconocida para {key}: {lab}")
            entry[key] = {"level": labels.index(lab), "label": lab}
    if note:
        entry["note"] = note
    p = Path(root) / FILE
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
            raise ValueError
    except (OSError, ValueError):
        data = {"_comentario": ("Encuesta de sensaciones que el atleta responde en el chat. Nivel 0 = lo mejor, 3 = lo peor. "
                                "Solo describe; no entra en los modelos de recuperación."), "entries": []}
    data["entries"] = [e for e in data["entries"] if not (isinstance(e, dict) and e.get("date") == day and e.get("time") == time)]
    data["entries"].append(entry)
    data["entries"].sort(key=lambda e: (str(e.get("date")), str(e.get("time") or "")))
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return entry
