"""Carreras: todos los datos de Garmin e Intervals y comparación con carreras parecidas (V8.8). Módulo puro.

Fuentes, por este orden: ``running_history.json`` (Garmin Connect, se conserva aunque pasen los días y trae los parciales
por km) y ``activities.json`` (Intervals.icu: carga, TRIMP, desacople y, si Garmin aún no la tiene, el resto). Se unen
por el ID de Garmin (``external_id`` en Intervals). El RPE y el nombre salen de la hoja.

Solo se muestran cifras que constan. Las derivadas son aritmética sobre ellas y se nombran como tales: ritmo
(min/km), metros por latido (velocidad en m/min ÷ FC media: más metros por latido = mismo ritmo con menos pulsaciones)
y desacople aeróbico por parciales (cuánto cae la relación ritmo/FC de la primera mitad a la segunda). Las
comparaciones son descriptivas: el calor, el desnivel, el cansancio previo o el sensor también influyen.
"""
from __future__ import annotations

from datetime import date, timedelta

from .garmin_insights import TE_LABEL_ES

MIN_KM = 1.0          # fragmentos más cortos (p. ej. una vuelta suelta de 1,8 min) no son carreras
SIMILAR = 0.25        # ±25 % de distancia para comparar
MIN_COMPARE_KM = 3.0
INTERVALS_SPORTS = {"Run", "TrailRun", "VirtualRun", "Treadmill"}


def _num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _r(v, d=1):
    return round(v, d) if v is not None else None


def pace_text(s_km) -> str:
    if s_km is None:
        return "—"
    s = int(round(s_km))
    return f"{s // 60}:{s % 60:02d}"


def duration_text(seconds) -> str:
    if seconds is None:
        return "—"
    s = int(round(seconds))
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _from_garmin(g: dict) -> dict:
    stride = _num(g.get("stride_cm"))
    vo = _num(g.get("vertical_oscillation_cm"))
    return {"garmin_id": g.get("garmin_id"), "date": g.get("date"), "start_local": g.get("start_local"), "name": g.get("name"),
            "distance_m": _num(g.get("distance_m")), "moving_s": _num(g.get("moving_s")) or _num(g.get("duration_s")),
            "elapsed_s": _num(g.get("elapsed_s")) or _num(g.get("duration_s")),
            "avg_speed_ms": _num(g.get("avg_speed_ms")), "max_speed_ms": _num(g.get("max_speed_ms")),
            "gap_speed_ms": _num(g.get("gap_speed_ms")), "avg_hr": _num(g.get("avg_hr")), "max_hr": _num(g.get("max_hr")),
            "cadence_spm": _num(g.get("cadence_spm")), "max_cadence_spm": _num(g.get("max_cadence_spm")),
            "stride_m": (stride / 100 if stride > 10 else stride) if stride else None,
            "vertical_oscillation_cm": (vo / 10 if vo > 30 else vo) if vo else None,
            "ground_contact_ms": _num(g.get("ground_contact_ms")), "vertical_ratio_pct": _num(g.get("vertical_ratio_pct")),
            "elev_gain_m": _num(g.get("elev_gain_m")), "elev_loss_m": _num(g.get("elev_loss_m")),
            "avg_power_w": _num(g.get("avg_power_w")), "norm_power_w": _num(g.get("norm_power_w")),
            "calories": _num(g.get("calories")), "vo2max": _num(g.get("vo2max")),
            "aerobic_te": _num(g.get("aerobic_te")), "anaerobic_te": _num(g.get("anaerobic_te")),
            "te_label": TE_LABEL_ES.get(str(g.get("te_label")), None), "garmin_load": _num(g.get("garmin_load")),
            "fastest_1k_s": _num(g.get("fastest_1k_s")), "fastest_5k_s": _num(g.get("fastest_5k_s")),
            "hr_zone_s": g.get("hr_zone_s") if isinstance(g.get("hr_zone_s"), list) else None,
            "min_temp_c": _num(g.get("min_temp_c")), "max_temp_c": _num(g.get("max_temp_c")),
            "splits_raw": g.get("splits") if isinstance(g.get("splits"), list) else [], "sources": ["Garmin"]}


def _intervals_fields(a: dict) -> dict:
    """Lo que añade Intervals (y, si Garmin no tiene la carrera, todo lo demás)."""
    cad = _num(a.get("average_cadence"))
    vo = _num(a.get("average_vertical_oscillation"))
    start = str(a.get("start_date_local") or "")
    return {"intervals_id": str(a.get("id")), "date": start[:10], "start_local": start[:19], "name": a.get("name"),
            "distance_m": _num(a.get("distance")) or _num(a.get("icu_distance")), "moving_s": _num(a.get("moving_time")),
            "elapsed_s": _num(a.get("elapsed_time")), "avg_speed_ms": _num(a.get("average_speed")),
            "max_speed_ms": _num(a.get("max_speed")), "gap_speed_ms": _num(a.get("gap")),
            "avg_hr": _num(a.get("average_heartrate")), "max_hr": _num(a.get("max_heartrate")),
            "cadence_spm": cad * 2 if cad else None,  # Intervals da la cadencia por pierna
            "stride_m": _num(a.get("average_stride")),
            "vertical_oscillation_cm": (vo / 10 if vo > 30 else vo) if vo else None,
            "ground_contact_ms": _num(a.get("average_stance_time")), "vertical_ratio_pct": _num(a.get("average_vertical_ratio")),
            "elev_gain_m": _num(a.get("total_elevation_gain")), "elev_loss_m": _num(a.get("total_elevation_loss")),
            "avg_power_w": _num(a.get("icu_average_watts")), "calories": _num(a.get("calories")),
            "intervals_load": _num(a.get("icu_training_load")), "trimp": _num(a.get("trimp")),
            "decoupling_intervals_pct": _num(a.get("decoupling")), "efficiency_factor": _num(a.get("icu_efficiency_factor"))}


def _splits(raw: list) -> list[dict]:
    out = []
    for s in raw or []:
        dist, secs = _num(s.get("distance_m")), _num(s.get("moving_s")) or _num(s.get("duration_s"))
        if not dist or not secs:
            continue
        out.append({"lap": s.get("lap"), "distance_m": round(dist), "seconds": round(secs, 1),
                    "pace_s_km": round(secs / (dist / 1000), 1), "avg_hr": _num(s.get("avg_hr")),
                    "cadence_spm": _num(s.get("cadence_spm")), "elev_gain_m": _num(s.get("elev_gain_m")),
                    "elev_loss_m": _num(s.get("elev_loss_m"))})
    return out


def decoupling_from_splits(splits: list[dict]) -> float | None:
    """Desacople aeróbico (%): caída de velocidad/FC de la primera mitad a la segunda, solo con vueltas de ~1 km."""
    full = [s for s in splits if s["distance_m"] >= 950 and s.get("avg_hr")]
    if len(full) < 4:
        return None
    half = len(full) // 2

    def ef(rows):
        dist = sum(r["distance_m"] for r in rows)
        secs = sum(r["seconds"] for r in rows)
        hr = sum(r["avg_hr"] * r["seconds"] for r in rows) / secs
        return (dist / secs) / hr
    a, b = ef(full[:half]), ef(full[half:])
    return round((a - b) / a * 100, 1)


def _derive(r: dict) -> dict:
    dist, mov = r.get("distance_m"), r.get("moving_s")
    speed = (dist / mov) if dist and mov else r.get("avg_speed_ms")
    r["distance_km"] = _r(dist / 1000 if dist else None, 2)
    r["pace_s_km"] = _r(1000 / speed if speed else None, 1)
    r["gap_pace_s_km"] = _r(1000 / r["gap_speed_ms"] if r.get("gap_speed_ms") else None, 1)
    r["m_per_beat"] = _r(speed * 60 / r["avg_hr"] if speed and r.get("avg_hr") else None, 3)
    r["splits"] = _splits(r.pop("splits_raw", []) or [])
    r["decoupling_pct"] = r.get("decoupling_intervals_pct")
    if r["decoupling_pct"] is None:
        r["decoupling_pct"] = decoupling_from_splits(r["splits"])
    return r


def compare(cur: dict, prev: dict) -> dict:
    d_pace = _r(cur["pace_s_km"] - prev["pace_s_km"], 0) if cur.get("pace_s_km") and prev.get("pace_s_km") else None
    d_hr = _r(cur["avg_hr"] - prev["avg_hr"], 0) if cur.get("avg_hr") and prev.get("avg_hr") else None
    d_eff = _r(cur["m_per_beat"] - prev["m_per_beat"], 3) if cur.get("m_per_beat") and prev.get("m_per_beat") else None
    d_cad = _r(cur["cadence_spm"] - prev["cadence_spm"], 0) if cur.get("cadence_spm") and prev.get("cadence_spm") else None
    bits = []
    if d_pace is not None:
        bits.append(f"{abs(int(d_pace))} s/km más rápido" if d_pace <= -3 else f"{int(d_pace)} s/km más lento" if d_pace >= 3
                    else "mismo ritmo")
    if d_hr is not None:
        bits.append("misma FC media" if abs(d_hr) < 2 else f"FC media {'+' if d_hr > 0 else '−'}{abs(int(d_hr))} lpm")
    eff = None
    if d_eff is not None:
        eff = ("más metros por latido: más eficiente" if d_eff >= 0.02 else "menos metros por latido: menos eficiente"
               if d_eff <= -0.02 else "eficiencia parecida")
    when = f"{prev['date'][8:10]}/{prev['date'][5:7]}"
    text = f"Frente a la del {when} ({str(prev['distance_km']).replace('.', ',')} km): " + ", ".join(bits) + (f"; {eff}" if eff else "") + "."
    return {"vs_date": prev["date"], "vs_key": prev["key"], "vs_distance_km": prev["distance_km"], "d_pace_s": d_pace,
            "d_hr": d_hr, "d_m_per_beat": d_eff, "d_cadence": d_cad, "text": text}


def build(history: dict | None, activities: list | None, today: str, rpe: dict | None = None, labels: dict | None = None) -> dict:
    """``rpe`` y ``labels``: {id de Intervals: RPE / nombre en la hoja}."""
    runs: dict[str, dict] = {}
    for gid, g in ((history or {}).get("runs") or {}).items():
        if isinstance(g, dict):
            runs[str(gid)] = _from_garmin(g)
    for a in activities or []:
        if not isinstance(a, dict) or a.get("type") not in INTERVALS_SPORTS:
            continue
        iv = _intervals_fields(a)
        key = str(a.get("external_id") or iv["intervals_id"])
        if key in runs:  # Garmin manda; Intervals rellena huecos y añade lo suyo
            base = runs[key]
            for k, v in iv.items():
                if base.get(k) is None and v is not None:
                    base[k] = v
            base["sources"] = sorted(set(base["sources"]) | {"Intervals"})
        else:
            runs[key] = dict(iv, sources=["Intervals"], splits_raw=[])
    out = []
    for key, r in runs.items():
        r["key"] = key
        _derive(r)
        if not r.get("date") or r["date"] > today or (r.get("distance_km") or 0) < MIN_KM:
            continue
        iid = r.get("intervals_id")
        r["rpe"] = (rpe or {}).get(iid) if iid else None
        r["title"] = (labels or {}).get(iid) or r.get("name") or "Carrera"
        out.append(r)
    out.sort(key=lambda x: x.get("start_local") or x["date"])
    for i, r in enumerate(out):
        prev = [p for p in out[:i] if p.get("distance_km") and r.get("distance_km") and r["distance_km"] >= MIN_COMPARE_KM
                and abs(p["distance_km"] - r["distance_km"]) / r["distance_km"] <= SIMILAR]
        r["comparison"] = compare(r, prev[-1]) if prev else None
    t = date.fromisoformat(today)
    c28 = [r for r in out if r["date"] >= (t - timedelta(days=27)).isoformat()]
    out.reverse()
    return {"available": bool(out), "runs": out,
            "summary": {"count": len(out), "km": _r(sum(r["distance_km"] for r in out), 1),
                        "count_28d": len(c28), "km_28d": _r(sum(r["distance_km"] for r in c28), 1),
                        "since": out[-1]["date"] if out else None}}


def load(root, result: dict) -> dict:
    """Lee ``running_history.json``, ``activities.json`` y el RPE/nombre de la hoja y construye las carreras."""
    import json
    from pathlib import Path
    root = Path(root)

    def read(name, default):
        try:
            return json.loads((root / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return default
    acts = read("activities.json", [])
    fb = read("training_feedback.json", {})
    rpe_map, labels = {}, {}
    for k, v in ((fb or {}).get("activities") or {}).items() if isinstance(fb, dict) else []:
        if isinstance(v, dict):
            if isinstance(v.get("rpe"), (int, float)):
                rpe_map[str(k)] = v["rpe"]
            if v.get("activity"):
                labels[str(k)] = v["activity"]
    for x in (result or {}).get("sessions_28d") or []:
        if isinstance(x, dict) and x.get("id"):
            if x.get("rpe") is not None:
                rpe_map[str(x["id"])] = x["rpe"]
            if x.get("label"):
                labels[str(x["id"])] = x["label"]
    return build(read("running_history.json", None), acts if isinstance(acts, list) else [],
                 str((result or {}).get("date") or date.today().isoformat()), rpe_map, labels)


def to_markdown(run: dict, limit: int = 6) -> str:
    runs = (run or {}).get("runs") or []
    if not runs:
        return "Sin carreras registradas."

    def n(v, d=0):
        return "—" if v is None else (f"{v:.{d}f}".replace(".", ",") if d else f"{round(v):d}")
    lines = ["| Fecha | km | Tiempo | Ritmo (min/km) | FC media / máx. | m/latido | Cadencia (ppm) | Desnivel + | RPE |",
             "|---|--:|--:|--:|--:|--:|--:|--:|--:|"]
    for r in runs[:limit]:
        lines.append(f"| {r['date'][8:10]}/{r['date'][5:7]} | {n(r.get('distance_km'), 2)} | {duration_text(r.get('moving_s'))} | "
                     f"{pace_text(r.get('pace_s_km'))} | {n(r.get('avg_hr'))} / {n(r.get('max_hr'))} | {n(r.get('m_per_beat'), 2)} | "
                     f"{n(r.get('cadence_spm'))} | {n(r.get('elev_gain_m'))} m | {n(r.get('rpe'), 1) if r.get('rpe') is not None else '—'} |")
    out = "\n".join(lines)
    if runs[0].get("comparison"):
        out += "\n\n" + runs[0]["comparison"]["text"]
    return out + ("\n\nMetros por latido = velocidad (m/min) ÷ FC media. Comparaciones descriptivas entre carreras de distancia "
                  "parecida (±25 %); el calor, el desnivel, el cansancio previo y el sensor también influyen.")
