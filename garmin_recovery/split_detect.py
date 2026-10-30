"""V8.13: propone dónde partir una actividad de Garmin que parece contener dos partes (p. ej. técnica y WOD).

Busca un único punto de cambio en la curva de FC: el corte que más separa la FC media de antes y de después,
con al menos ``MIN_PART_S`` en cada lado y una diferencia de al menos ``MIN_DELTA_BPM``. Solo se propone para
actividades recientes con una sola fila en la hoja y sin tramos declarados. Es una sugerencia: el atleta confirma
y entonces se escriben los tramos (``segment``) en la hoja.
"""
from __future__ import annotations

from datetime import date, timedelta

MIN_DURATION_S = 20 * 60
MIN_PART_S = 3 * 60
EDGE_S = 3 * 60
SKIP_TYPES = ("Run", "Walk", "Ride", "Swim", "Hike")
MIN_DELTA_BPM = 25
DAYS = 7


def change_point(points: list) -> dict | None:
    pts = [(p[0], p[1]) for p in points if isinstance(p, (list, tuple)) and len(p) >= 2
           and isinstance(p[0], (int, float)) and isinstance(p[1], (int, float)) and p[1] > 0]
    if len(pts) < 10 or pts[-1][0] - pts[0][0] < MIN_DURATION_S:
        return None
    hrs = [h for _, h in pts]
    pre = [0.0]
    for h in hrs:
        pre.append(pre[-1] + h)
    n, total = len(pts), pre[-1]
    best = None
    for i in range(1, n):
        t = pts[i][0]
        if t - pts[0][0] < MIN_PART_S or pts[-1][0] - t < MIN_PART_S:
            continue
        a, b = pre[i] / i, (total - pre[i]) / (n - i)
        if best is None or abs(b - a) > abs(best[2] - best[1]):
            best = (t, a, b)
    if not best or abs(best[2] - best[1]) < MIN_DELTA_BPM:
        return None
    t, a, b = best
    # corte nítido: los 3 min de cada lado también deben diferir (descarta rampas como el inicio de una carrera)
    near_a = [h for tt, h in pts if t - EDGE_S <= tt < t]
    near_b = [h for tt, h in pts if t <= tt < t + EDGE_S]
    if not near_a or not near_b or abs(sum(near_b) / len(near_b) - sum(near_a) / len(near_a)) < MIN_DELTA_BPM:
        return None
    return {"cut_s": int(t), "cut_mmss": f"{int(t) // 60}:{int(t) % 60:02d}", "before_bpm": round(a), "after_bpm": round(b)}


def propose(curves: dict | None, rows: list[dict], today: str) -> list[dict]:
    if not isinstance(curves, dict):
        return []
    since = (date.fromisoformat(today) - timedelta(days=DAYS - 1)).isoformat()
    by_id: dict[str, list] = {}
    for r in rows:
        if r.get("id"):
            by_id.setdefault(r["id"], []).append(r)
    out = []
    for aid, c in curves.items():
        if not isinstance(c, dict) or not c.get("available") or any(k in str(c.get("type") or "") for k in SKIP_TYPES):
            continue
        d = str(c.get("date") or "")[:10]
        sheet = by_id.get(aid) or []
        if not d or d < since or len(sheet) != 1 or any("segment" in (r.get("detail") or {}) for r in sheet):
            continue
        cp = change_point(c.get("points") or [])
        if not cp:
            continue
        up = cp["after_bpm"] > cp["before_bpm"]
        out.append({"activity_id": aid, "date": d, "label": sheet[0].get("name") or c.get("name") or aid, **cp,
                    "reason": f"FC media {cp['before_bpm']} → {cp['after_bpm']} lpm" + (" (parte suave y luego intensa)" if up else " (parte intensa y luego suave)")})
    out.sort(key=lambda x: x["date"], reverse=True)
    return out
