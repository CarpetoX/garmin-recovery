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
ITEMS = [  # orden de la encuesta; nivel 0 = lo mejor, 3 = lo peor
    ("sueno", "Sueño percibido", ["Muy bien", "Bien", "Regular", "Mal"]),
    ("cansancio", "Cansancio", ["Fresco", "Algo cansado", "Cansado", "Muy cansado"]),
    ("agujetas", "Agujetas", ["Nada", "Leves", "Moderadas", "Fuertes"]),
    ("molestias", "Molestias articulares", ["Ninguna", "Leves", "Moderadas", "Fuertes"]),
    ("estres", "Estrés", ["Bajo", "Normal", "Alto", "Muy alto"]),
    ("animo", "Ánimo", ["Muy bueno", "Bueno", "Regular", "Malo"]),
    ("motivacion", "Ganas de entrenar", ["Con muchas ganas", "Normal", "Pocas ganas", "Sin ganas"]),
]
MIN_ITEMS_FOR_INDEX = len(ITEMS)  # V8.19: el índice solo con la encuesta completa, para que los días sean comparables
BASELINE_MIN = 10  # encuestas necesarias para comparar con tu propia normalidad en vez de con umbrales fijos

# Texto fijo de cada pregunta y de cada opción: preguntar siempre igual es lo que hace comparable la encuesta.
# Periodo de referencia: «antes de entrenar hoy» (o «ahora» si no hay entreno); el sueño, la última noche.
QUESTIONS = {
    "sueno": ("¿Cómo sientes que dormiste anoche?", ["Descansado, sin despertares", "Bien, algún despertar", "Regular, me cuesta arrancar", "Mal, apenas descansé"]),
    "cansancio": ("Antes de entrenar hoy (o ahora, si no entrenas), ¿cuánta fatiga general notas?",
                  ["Ninguna, fresco", "Ligera, no afecta", "Clara, me pesa", "Mucha, agotado"]),
    "agujetas": ("¿Agujetas o dolor muscular?", ["Ninguna", "Se notan, no molestan", "Molestan al moverme", "Limitan el movimiento"]),
    "molestias": ("¿Molestias en articulaciones o tendones (no agujetas)?", ["Ninguna", "Se notan, no limitan", "Limitan algún ejercicio", "Duelen al entrenar"]),
    "estres": ("¿Estrés de trabajo o vida hoy?", ["Bajo, tranquilo", "Normal", "Alto, me pesa", "Muy alto, me desborda"]),
    "animo": ("¿Ánimo en general (aparte del entreno)?", ["Muy bueno", "Bueno", "Regular", "Malo"]),
    "motivacion": ("¿Ganas de entrenar hoy?", ["Muchas", "Normales", "Pocas", "Ninguna"]),
}
MOMENTS = ("antes del entreno", "después del entreno", "sin entreno")


def load(root: str | Path) -> list[dict]:
    try:
        data = json.loads((Path(root) / FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    entries = data.get("entries") if isinstance(data, dict) else None
    return [_migrate(e) for e in entries if isinstance(e, dict)] if isinstance(entries, list) else []


def _migrate(e: dict) -> dict:
    """V8.18 guardaba las ganas de entrenar como «animo»; desde V8.19 son «motivacion» y «animo» es el ánimo general."""
    a = e.get("animo")
    if isinstance(a, dict) and a.get("label") in dict((k, labels) for k, _, labels in ITEMS)["motivacion"]:
        e = dict(e) if "motivacion" in e else dict(e, motivacion=a)
        e.pop("animo")  # un «animo» con etiquetas de ganas nunca cuenta como ánimo general
    return e


def zones_of(e: dict | None) -> list[str]:
    """Zonas como lista de textos (un texto suelto cuenta como una zona; lo demás se ignora)."""
    z = (e or {}).get("zonas")
    if isinstance(z, str):
        z = [z]
    return [str(x).strip()[:60] for x in z if isinstance(x, str) and x.strip()] if isinstance(z, list) else []


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


def record(root: str | Path, day: str, answers: dict[str, str], time: str | None = None, note: str | None = None,
           zones: list[str] | None = None, moment: str | None = None) -> dict:
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
    if moment is not None:
        if moment not in MOMENTS:
            raise ValueError(f"momento desconocido: {moment}")
        entry["moment"] = moment  # V8.19: si se responde después de entrenar, la fatiga incluye la sesión
    zs = [str(z).strip()[:60] for z in zones or [] if str(z).strip()]
    if zs:
        entry["zonas"] = zs
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
    same = [e for e in data["entries"] if isinstance(e, dict) and e.get("date") == day and e.get("time") == time]
    for old in same:  # completar una encuesta del mismo momento sin perder lo ya respondido
        for k, v in _migrate(old).items():
            entry.setdefault(k, v)
    data["entries"] = [e for e in data["entries"] if not (isinstance(e, dict) and e.get("date") == day and e.get("time") == time)]
    data["entries"].append(entry)
    data["entries"].sort(key=lambda e: (str(e.get("date")), str(e.get("time") or "")))
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return entry


def wellbeing(entry: dict | None) -> int | None:
    """Índice de bienestar 0–100 (100 = todo en lo mejor) con las respuestas que haya; None con menos de 4."""
    if not entry:
        return None
    lv = [level(entry, k) for k, _, _ in ITEMS]
    lv = [x for x in lv if x is not None]
    if len(lv) < MIN_ITEMS_FOR_INDEX:
        return None
    return round(100 - sum(lv) / (3 * len(lv)) * 100)


def personal_baseline(entries: list[dict], today: str, days: int = 60) -> dict[str, dict]:
    """Media y desviación de cada pregunta en tus encuestas previas a hoy (ventana de 60 días)."""
    t = _date.fromisoformat(today)
    since = (t - timedelta(days=days)).isoformat()
    bd = {d: e for d, e in by_date(entries, today).items() if since <= d < today}
    out = {}
    for k, _, _ in ITEMS:
        xs = [level(e, k) for e in bd.values()]
        xs = [x for x in xs if x is not None]
        if len(xs) >= BASELINE_MIN:
            m = sum(xs) / len(xs)
            sd = (sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5
            out[k] = {"n": len(xs), "mean": round(m, 2), "sd": round(sd, 2)}
    return out


def analysis(entries: list[dict], today: str, trend: list[dict] | None = None, zone: str | None = None) -> dict:
    """Lectura descriptiva de la encuesta: índice de hoy, su media de 14 días y observaciones por reglas fijas.

    Nada se presenta como causa. Las relaciones con la carga solo se describen con al menos 7 días emparejados.
    """
    bd = by_date(entries, today)
    t = _date.fromisoformat(today)
    idx_today = wellbeing(bd.get(today))
    last14 = [wellbeing(bd.get((t - timedelta(days=i)).isoformat())) for i in range(1, 15)]
    prev = [x for x in last14 if x is not None]
    mean14 = round(sum(prev) / len(prev)) if len(prev) >= 3 else None
    obs: list[dict] = []
    e = bd.get(today)
    if e:
        if (level(e, "molestias") or 0) >= 2:
            obs.append({"level": "bad", "text": "Molestias articulares moderadas o fuertes"
                        + (f" ({', '.join(zones_of(e))})" if zones_of(e) else "")
                        + ": evita cargar esa zona y, si persisten, consúltalo con un profesional."})
        elif (level(e, "molestias") or 0) == 1:
            obs.append({"level": "warn", "text": "Molestias articulares leves"
                        + (f" ({', '.join(zones_of(e))})" if zones_of(e) else "") + ": vigila que no aumenten."})
        streak = 0
        for i in range(0, 7):
            x = bd.get((t - timedelta(days=i)).isoformat())
            if x and (level(x, "agujetas") or 0) >= 2:
                streak += 1
            else:
                break
        if streak >= 2:
            obs.append({"level": "warn", "text": f"Agujetas moderadas o fuertes {streak} días seguidos."})
        elif (level(e, "agujetas") or 0) >= 2:
            obs.append({"level": "info", "text": "Agujetas moderadas o fuertes hoy; si siguen mañana, se marcará."})
        if (level(e, "cansancio") or 0) >= 2 and zone == "green":
            obs.append({"level": "info", "text": "Te notas cansado aunque los modelos dan verde: lo que sientes y lo que mide el reloj no coinciden hoy."})
        if idx_today is not None and idx_today >= 70 and zone == "red":
            obs.append({"level": "info", "text": "Te sientes bien aunque los modelos dan rojo: la decisión sigue siendo la del modelo más prudente."})
        if (level(e, "motivacion") or 0) >= 2:
            obs.append({"level": "info", "text": "Pocas ganas de entrenar: si se repite varios días, es una señal de fatiga a tener en cuenta."})
        base = personal_baseline(entries, today)
        names = {k: n.lower() for k, n, _ in ITEMS}
        worse = [names[k] for k, b in base.items() if level(e, k) is not None and level(e, k) >= b["mean"] + max(1.0, b["sd"])]
        if worse:
            obs.append({"level": "warn", "text": "Peor que tu normalidad (≥ 1 punto sobre tu media personal): " + ", ".join(worse) + "."})
        sc = next((r.get("sleep_score") for r in trend or [] if isinstance(r, dict) and r.get("date") == today), None)
        ls = level(e, "sueno")
        if isinstance(sc, (int, float)) and not isinstance(sc, bool) and ls is not None:
            if ls <= 1 and sc < 60:
                obs.append({"level": "info", "text": f"Sientes que dormiste bien, pero Garmin puntúa el sueño en {sc:g}."})
            elif ls >= 2 and sc >= 80:
                obs.append({"level": "info", "text": f"Sientes que dormiste mal, aunque Garmin puntúa el sueño en {sc:g}."})
        if e.get("moment") == "después del entreno":
            obs.append({"level": "info", "text": "Encuesta respondida después de entrenar: el cansancio y las agujetas incluyen la sesión de hoy."})
        if idx_today is not None and mean14 is not None and abs(idx_today - mean14) >= 15:
            obs.append({"level": "info", "text": f"Bienestar {'por encima' if idx_today > mean14 else 'por debajo'} de tu media de 14 días ({mean14})."})
    # relación con la carga del día anterior (solo descriptiva y con suficientes días)
    srpe = {r.get("date"): r.get("srpe") for r in trend or [] if isinstance(r, dict)}
    pairs = []
    for d, en in bd.items():
        prev_day = (_date.fromisoformat(d) - timedelta(days=1)).isoformat()
        w, s_ = wellbeing(en), srpe.get(prev_day)
        if w is not None and isinstance(s_, (int, float)) and not isinstance(s_, bool):
            pairs.append((s_, w))
    load_rel = None
    if len(pairs) >= 7:
        med = sorted(p_[0] for p_ in pairs)[len(pairs) // 2]
        hi = [w for s_, w in pairs if s_ > med]
        lo = [w for s_, w in pairs if s_ <= med]
        if hi and lo:
            load_rel = {"pairs": len(pairs), "after_high": round(sum(hi) / len(hi)), "after_low": round(sum(lo) / len(lo)),
                        "threshold_srpe": med}
    n_prev = len([d for d in bd if d < today])
    return {"today": idx_today, "mean14": mean14, "surveys_14d": len(prev) + (1 if idx_today is not None else 0),
            "observations": obs, "load_relation": load_rel,
            "calibration": {"surveys": n_prev, "needed": BASELINE_MIN, "personal": n_prev >= BASELINE_MIN}}

