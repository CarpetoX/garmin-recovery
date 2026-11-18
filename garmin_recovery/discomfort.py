"""V9.7: seguimiento de molestias por zona. Puro, sin red.

Lee las zonas que el atleta marca en la encuesta («Rodilla derecha», «Hombro»…) cuando dice tener molestias, las
agrupa por articulación y las sigue en el tiempo. Lo cruza con las sesiones de los dos días anteriores que llevan
movimientos que cargan esa zona. Solo describe coincidencias: no prueba que una sesión cause la molestia.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date as _date, timedelta

from . import sensations as sn

PERSISTENT_DAYS = 3  # días con molestia en la misma zona, en 7, para avisar de que se repite
LOOKBACK_DAYS = 2  # sesiones previas que se miran antes de cada día con molestia
LEVELS = dict((k, labels) for k, _, labels in sn.ITEMS)["molestias"]

# Movimientos que cargan cada articulación (orientativo). Claves = primera palabra de la zona, sin tildes.
LOADS = {
    "rodilla": r"squat|sentadilla|snatch|clean|lunge|zancada|box|jump|salto|wall ?ball|thruster|pistol|split|bulgara|prensa"
               r"|cuadriceps|step|carrera|run|burpee|double ?under|comba",
    "hombro": r"press|jerk|snatch|hspu|handstand|push|pull|dominad|chin|muscle|toes|ring|dip|banca|bench|wall ?walk|overhead"
              r"|thruster|jalon|apertura",
    "espalda": r"deadlift|peso muerto|clean|snatch|swing|row\b|remo|good ?morning|squat|sentadilla|devil",
    "muneca": r"front squat|clean|snatch|hspu|handstand|push-?up|wall ?walk|burpee|dip|press|devil",
    "codo": r"pull|chin|dominad|curl|press|muscle|dip|triceps|jalon",
    "tobillo": r"jump|salto|carrera|run|double ?under|comba|box|squat|sentadilla|snatch|clean",
    "cadera": r"squat|sentadilla|deadlift|peso muerto|lunge|zancada|snatch|clean|swing|hip|carrera|run|v-?sit|sit-?up|toes",
}


def norm(text) -> str:
    s = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s).strip()


def joint_of(zone) -> str:
    """Articulación de una zona: «Rodilla derecha» → «rodilla»; «Espalda baja» → «espalda»."""
    words = norm(zone).split()
    return words[0] if words else ""


def zone_history(entries: list[dict], today: str, days: int = 28) -> list[dict]:
    """Por articulación: días con molestia en 7 y en 28 días, último día, nivel máximo y fechas (28 días)."""
    t = _date.fromisoformat(today)
    since28, since7 = (t - timedelta(days=days - 1)).isoformat(), (t - timedelta(days=6)).isoformat()
    by: dict[str, dict] = {}
    for d, e in sn.by_date(entries, today).items():
        lv = sn.level(e, "molestias")
        if not lv or d < since28 or d > today:
            continue
        for z in sn.zones_of(e):
            j = joint_of(z)
            if not j:
                continue
            g = by.setdefault(j, {"joint": j, "label": z, "dates": set(), "max_level": 0, "last": d})
            g["dates"].add(d)
            g["max_level"] = max(g["max_level"], lv)
            g["last"] = max(g["last"], d)
            if len(z) > len(g["label"]):
                g["label"] = z  # la etiqueta más concreta («Rodilla derecha» mejor que «Rodilla»)
    out = []
    for g in by.values():
        ds = sorted(g["dates"])
        out.append({"joint": g["joint"], "label": g["label"], "dates": ds, "days_28": len(ds),
                    "days_7": sum(1 for d in ds if d >= since7), "last": g["last"], "max_level": g["max_level"],
                    "max_label": LEVELS[g["max_level"]]})
    out.sort(key=lambda g: (-g["days_7"], -g["days_28"], g["joint"]))
    return out


def _session_text(s: dict) -> str:
    parts = [s.get("label"), s.get("name")]
    for b in s.get("blocks") or []:
        if isinstance(b, dict):
            parts.append(b.get("activity"))
            det = b.get("detail_json") if isinstance(b.get("detail_json"), dict) else {}
            for k in ("exercises", "prescribed_round", "performed_round", "skills", "complex"):
                for x in det.get(k) or []:
                    if isinstance(x, dict):
                        parts.append(x.get("name"))
                        for y in x.get("exercises") or []:
                            if isinstance(y, dict):
                                parts.append(y.get("name"))
            parts.append(det.get("exercise"))
    return norm(" · ".join(str(p) for p in parts if p))


def loading_sessions(joint: str, dates: list[str], sessions: list[dict]) -> list[dict]:
    """Sesiones de los 2 días previos (y el mismo día) a cada molestia con movimientos que cargan esa zona."""
    pat = LOADS.get(joint)
    if not pat or not dates:
        return []
    rx = re.compile(pat)
    want = set()
    for d in dates:
        t = _date.fromisoformat(d)
        want.update((t - timedelta(days=i)).isoformat() for i in range(0, LOOKBACK_DAYS + 1))
    out, seen = [], set()
    for s in sessions:
        d = str(s.get("date") or "")[:10]
        if d not in want or s.get("id") in seen:
            continue
        hits = sorted(set(m.group(0) for m in rx.finditer(_session_text(s))))
        if hits:
            seen.add(s.get("id"))
            out.append({"date": d, "id": s.get("id"), "label": s.get("label") or s.get("name"), "rpe": s.get("rpe"), "moves": hits[:6]})
    out.sort(key=lambda x: x["date"], reverse=True)
    return out


def sessions_from(crossfit_insights: dict, sessions_28d: list[dict]) -> list[dict]:
    """Sesiones de 28 días con su detalle de la hoja (bloques de crossfit_insights) para buscar movimientos."""
    blocks = {str(a.get("activity_id")): a.get("manual_blocks") or [] for a in (crossfit_insights or {}).get("activities") or []
              if isinstance(a, dict)}
    out = []
    for s in sessions_28d or []:
        if isinstance(s, dict) and not s.get("removed"):
            out.append(dict(s, blocks=blocks.get(str(s.get("id")), [])))
    return out


def observation(history: list[dict]) -> list[dict]:
    """Avisos para la tarjeta de sensaciones: una zona con molestias que se repite."""
    obs = []
    for g in history:
        if g["days_7"] >= PERSISTENT_DAYS:
            obs.append({"level": "warn", "text": f"Molestia en {g['label'].lower()} {g['days_7']} de los últimos 7 días: se repite. "
                                                 "Reduce lo que carga esa zona y, si sigue, consúltalo con un profesional."})
    return obs
