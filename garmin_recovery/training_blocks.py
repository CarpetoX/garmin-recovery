"""Fuerza, halterofilia y metcons por separado (V7.18).

Funciones puras (sin reloj ni red) que ordenan lo confirmado por el atleta en `crossfit_insights.json` y en el
historial de ejercicios (`progression.py`) para pintarlo en tablas y gráficas. Solo se muestra lo que consta en
`detail_json`: no se inventan cargas, tiempos ni desgloses, y el cronómetro oficial y el reloj se conservan por separado.
"""
from __future__ import annotations

import re
from datetime import date as _date, timedelta

from .progression import norm

OLYMPIC = re.compile(r"\b(snatch|clean|jerk|arrancada|cargada|envion)\b")
SKIP_TYPES = {"warmup", "skill"}


def is_olympic(name: str) -> bool:
    return bool(OLYMPIC.search(norm(name)))


def clip(text, limit: int = 90) -> str:
    """Recorta en un espacio y marca el corte con «…» (V8.7: antes se cortaba a media palabra)."""
    t = " ".join(str(text or "").split())
    if len(t) <= limit:
        return t
    cut = t[:limit - 1]
    sp = cut.rfind(" ")
    return (cut[:sp] if sp > limit * 0.6 else cut).rstrip(" -/+·,;") + "…"


def _interval(seconds) -> str | None:
    if not isinstance(seconds, (int, float)) or isinstance(seconds, bool) or seconds <= 0:
        return None
    m, s = divmod(int(round(seconds)), 60)
    return f"cada {m}'" + (f'{s:02d}"' if s else "") if m else f'cada {s}"'


def complexes_of(detail: dict | None) -> list[dict]:
    """Complex tal como se hicieron (V8.7): nombre, repeticiones de cada movimiento, intervalo y cargas por serie."""
    out = []
    for c in (detail or {}).get("complexes") or []:
        if not isinstance(c, dict) or not c.get("name"):
            continue
        loads = [x for x in c.get("loads_kg") or [] if isinstance(x, (int, float)) and not isinstance(x, bool)]
        reps = c.get("reps") if isinstance(c.get("reps"), dict) else {}
        scheme = "+".join(_fmt_n(v) for v in reps.values() if isinstance(v, (int, float)))
        out.append({"name": str(c["name"]), "approach": bool(c.get("approach")), "scheme": scheme or None,
                    "interval": _interval(c.get("interval_seconds")), "loads": loads,
                    "sets": int(c["sets"]) if isinstance(c.get("sets"), int) else len(loads) or None,
                    "top": max(loads) if loads else None})
    return out


def _fmt_n(v) -> str:
    return f"{v:g}".replace(".", ",") if isinstance(v, (int, float)) else str(v)


def _mmss(seconds) -> str | None:
    if not isinstance(seconds, (int, float)) or isinstance(seconds, bool):
        return None
    s = int(round(seconds))
    return f"{s // 60}:{s % 60:02d}"


def _item(d: dict) -> str:
    name = str(d.get("name") or "").strip()
    bits = []
    if d.get("reps") is not None:
        bits.append(_fmt_n(d["reps"]))
    if d.get("distance_m") is not None:
        bits.append(f'{_fmt_n(d["distance_m"])} m')
    if d.get("calories") is not None:
        bits.append(f'{d["calories"]} cal')
    if d.get("minutes") is not None:
        bits.append(f'{_fmt_n(d["minutes"])} min')
    out = " ".join(bits + [name]).strip()
    if d.get("load_kg") is not None:
        out += f' ({_fmt_n(d["load_kg"])} kg)'
    return out


def _round_series(detail: dict) -> dict | None:
    """Repeticiones por ronda cuando constan y no son todas iguales (p. ej. EMOM con caída de repeticiones)."""
    perf = detail.get("performed") if isinstance(detail.get("performed"), dict) else {}
    rounds = perf.get("rounds") if isinstance(perf.get("rounds"), list) else []
    if len(rounds) < 3:
        return None
    keys = [k for k in rounds[0] if k.endswith("_reps") and isinstance(rounds[0][k], (int, float))]
    for k in keys:
        vals = [r.get(k) for r in rounds]
        if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in vals) and len(set(vals)) > 1:
            label = k[:-5].replace("_", " ")
            return {"label": f"{label} por ronda", "values": [float(v) for v in vals]}
    return None


UPPER = {"db", "kb", "s2oh", "hspu", "t2b", "c2b", "du", "wb"}


def _totals(perf: dict) -> list[str]:
    """Totales declarados del metcon («120 cal», «1.400 m», «160 DB hang clean S2OH»), tal como constan (V8.7)."""
    tot = perf.get("totals") if isinstance(perf.get("totals"), dict) else {}
    out = []
    for k, v in tot.items():
        if not isinstance(v, (int, float)) or isinstance(v, bool) or v <= 0:
            continue
        if k == "calories":
            out.append(f"{_fmt_n(v)} cal")
        elif k in ("run_m", "distance_m"):
            out.append(f"{v:,.0f}".replace(",", ".") + " m" + (" de carrera" if k == "run_m" else ""))
        elif k.endswith("_reps"):
            words = [w.upper() if w in UPPER else w for w in k[:-5].split("_")]
            out.append(f"{_fmt_n(v)} {' '.join(words)}")
    return out if len(out) >= 2 else []


def metcon_card(act: dict, block: dict) -> dict:
    d = block.get("detail_json") or {}
    perf = d.get("performed") if isinstance(d.get("performed"), dict) else {}
    fmt = d.get("format") or "Metcon"
    presc = [_item(x) for x in d.get("prescribed_round") or [] if isinstance(x, dict) and x.get("name") != "descanso"]
    if not presc and d.get("exercises"):
        presc = [_item(x) for x in d["exercises"] if isinstance(x, dict)]
        if d.get("prescribed_rounds"):
            presc = ["/".join(str(r) for r in d["prescribed_rounds"]) + " repeticiones de " + " y ".join(presc)] if presc else presc
    if not presc and isinstance(d.get("rounds"), list) and d["rounds"]:
        r0 = d["rounds"][0]
        kg = r0.get("dumbbell_kg")
        presc = []
        if r0.get("calories_shared") is not None:
            presc.append(f'{_fmt_n(r0["calories_shared"])} cal compartidas: ' + " → ".join(str(r.get("machine")) for r in d["rounds"] if r.get("machine")))
        for k in r0:
            if k.endswith("_sync_reps"):
                presc.append(f'{_fmt_n(r0[k])} {k[:-10].replace("_", " ")}' + (f" ({_fmt_n(kg)} kg)" if kg and "dumbbell" in k else "") + " sincronizados")
    result, timing = [], []
    if perf.get("rounds_complete") is not None:
        txt = f'{perf["rounds_complete"]} rondas'
        if perf.get("extra_distance_m") and perf.get("extra_reps"):  # V8.7: p. ej. 6 rondas + 200 m + 10 wall balls
            txt += f' + {_fmt_n(perf["extra_distance_m"])} m + {perf["extra_reps"]} reps'
        elif perf.get("extra_reps"):
            txt += f' + {perf["extra_reps"]} reps'
        elif perf.get("extra_distance_m"):
            txt += f' + {_fmt_n(perf["extra_distance_m"])} m de {perf.get("extra_exercise") or "la siguiente estación"}'
        result.append(txt)
    elif d.get("rounds_completed") is not None:
        result.append(f'{d["rounds_completed"]} rondas')
    elif isinstance(perf.get("rounds"), int) and not isinstance(perf.get("rounds"), bool):
        # V8.7: EMOM / E3MO3M por rondas (no AMRAP): «8 de 8 rondas completas»
        n = perf["rounds"]
        done = perf.get("all_rounds_completed")
        result.append(f"{n} de {n} rondas completas" if done is True else f"{n} rondas, alguna incompleta" if done is False
                      else f"{n} rondas")
    if perf.get("completed") and not result:
        result.append("completado")
    if perf.get("total_reps") is not None:
        result.append(f'{perf["total_reps"]} reps en total')
    elif isinstance(perf.get("totals"), dict) and perf["totals"].get("squat_clean_reps") is not None:
        result.append(f'{perf["totals"]["squat_clean_reps"]} squat clean en total')
    official = _mmss(d.get("finish_time_seconds"))
    cap = _mmss(d.get("time_cap_seconds")) or (f'{int(d["time_cap_minutes"])}:00' if isinstance(d.get("time_cap_minutes"), (int, float)) else None)
    if official:
        timing.append(f"Oficial {official}")
    if isinstance(d.get("garmin_recorded_seconds"), (int, float)):
        timing.append(f'Reloj {_mmss(d["garmin_recorded_seconds"])}')
    if cap:
        timing.append(f"Cap {cap}")
    note = None
    if perf.get("partial_round_exercise_breakdown_confirmed") is False:
        note = "El desglose de las repeticiones extra no está confirmado."
    elif perf.get("completed") and perf.get("exact_finish_time_minutes") is None and not official:
        note = "Tiempo exacto de finalización no registrado."
    minutes = d.get("recorded_garmin_minutes") if isinstance(d.get("recorded_garmin_minutes"), (int, float)) else act.get("recorded_minutes")
    return {
        "date": act["date"], "activity_id": str(act.get("activity_id") or ""), "format": str(fmt),
        "partner": bool(d.get("partner_workout")), "title": clip(block.get("activity"), 90),
        "prescription": presc, "result": " · ".join(result) or None, "totals": _totals(perf), "timing": timing,
        "rpe": d.get("rpe") if isinstance(d.get("rpe"), (int, float)) else act.get("rpe_used"),
        "minutes": round(float(minutes), 1) if isinstance(minutes, (int, float)) else None,
        "rounds": _round_series(d), "note": note,
        "hr": act.get("heart_rate") if isinstance(act.get("heart_rate"), dict) else None,
    }


def _rpe_by_activity(crossfit: dict) -> dict[str, float]:
    return {str(a.get("activity_id")): a.get("rpe_used") for a in (crossfit or {}).get("activities") or []
            if isinstance(a, dict) and isinstance(a.get("rpe_used"), (int, float))}


def _compress(sets: list[dict]) -> str:
    out = []
    for s in sets:
        txt = f'{_fmt_n(s["reps"])} @ {_fmt_n(s["load"])}'
        c = int(s.get("count") or 1)
        out.append(txt if c == 1 else f"{c}× {txt}")
    return " · ".join(out)


def olympic_sessions(entries: dict[str, dict]) -> set[str]:
    """V8.7: qué sesiones van enteras a Halterofilia (por su nombre en la hoja y sus ejercicios), sin partirlas."""
    from .session_kind import is_olympic_session
    by: dict[str, dict] = {}
    for e in entries.values():
        g = by.setdefault(str(e["activity_id"]), {"title": e.get("activity") or "", "names": []})
        g["names"].append(e["exercise"])
    return {aid for aid, g in by.items() if is_olympic_session(g["title"], g["names"])}


def lift_sessions(entries: dict[str, dict], rpe_map: dict[str, float], olympic: bool, limit: int = 12,
                  complexes: dict[str, list] | None = None) -> list[dict]:
    """Sesiones de fuerza (olympic=False) u halterofilia (olympic=True) con sus ejercicios, de más reciente a más antigua.
    V8.7: la sesión va entera a un lado u otro (un complex con front squat no se parte) y lleva sus complex si constan."""
    oly = olympic_sessions(entries)
    by: dict[tuple[str, str], dict] = {}
    for e in entries.values():
        if (str(e["activity_id"]) in oly) != olympic:
            continue
        s = by.setdefault((e["date"], e["activity_id"]), {"date": e["date"], "activity_id": e["activity_id"], "title": clip(e["activity"], 140),
                                                          "rpe": rpe_map.get(e["activity_id"]), "exercises": [],
                                                          "complexes": (complexes or {}).get(str(e["activity_id"])) or []})
        s["exercises"].append({"name": e["exercise"], "unit": e["unit_label"], "top_load": e["top_load"], "top_reps": e["top_reps"],
                               "sets": _compress(e["sets"]), "work_sets": e["work_sets"], "volume": e["volume"],
                               "volume_complete": e["volume_complete"], "rpe": e.get("rpe"),
                               "reps": sum(x["reps"] * int(x.get("count") or 1) for x in e["sets"])})
    for s in by.values():
        bar = [x for x in s["exercises"] if x["unit"] == "barra"]
        s["total_reps"] = round(sum(x["reps"] for x in s["exercises"]))
        s["bar_volume"] = round(sum(x["volume"] for x in bar)) if bar else None
        s["bar_volume_complete"] = all(x["volume_complete"] for x in bar)
    out = sorted(by.values(), key=lambda s: (s["date"], s["activity_id"]), reverse=True)
    return out[:limit]


def weekly_volume(entries: dict[str, dict], olympic: bool, today: str, weeks: int = 6) -> list[dict]:
    """Volumen mínimo verificado de barra (kg·reps con carga registrada) por semana natural, incluida la actual.
    V8.7: cada sesión suma entera a Fuerza o a Halterofilia, igual que en sus tarjetas."""
    t = _date.fromisoformat(today)
    monday = t - timedelta(days=t.weekday())
    starts = [monday - timedelta(weeks=i) for i in range(weeks - 1, -1, -1)]
    out = [{"start": s.isoformat(), "volume": 0.0, "sessions": set(), "complete": True} for s in starts]
    oly = olympic_sessions(entries)
    for e in entries.values():
        if (str(e["activity_id"]) in oly) != olympic or e["unit"] != "kg_total_barra":
            continue
        d = _date.fromisoformat(e["date"])
        for w in out:
            s = _date.fromisoformat(w["start"])
            if s <= d < s + timedelta(days=7):
                w["volume"] += e["volume"]
                w["sessions"].add(e["activity_id"])
                w["complete"] = w["complete"] and e["volume_complete"]
    res = [{"start": w["start"], "volume": round(w["volume"]), "sessions": len(w["sessions"]), "complete": w["complete"],
            "current": i == len(out) - 1} for i, w in enumerate(out)]
    while len(res) > 3 and res[0]["volume"] == 0:  # semanas anteriores al primer registro: no se muestran
        res.pop(0)
    return res


def build(crossfit: dict | None, entries: dict[str, dict] | None, today: str) -> dict:
    crossfit = crossfit or {}
    entries = entries or {}
    rpe_map = _rpe_by_activity(crossfit)
    metcons, other = [], []
    cx: dict[str, list] = {}
    for act in crossfit.get("activities") or []:
        if not isinstance(act, dict) or not act.get("date"):
            continue
        for block in act.get("manual_blocks") or []:
            d = block.get("detail_json") if isinstance(block, dict) else None
            if not isinstance(d, dict):
                continue
            if d.get("type") == "metcon":
                metcons.append(metcon_card(act, block))
            elif complexes_of(d):
                cx.setdefault(str(act.get("activity_id") or ""), []).extend(complexes_of(d))
    metcons.sort(key=lambda m: (m["date"], m["activity_id"]), reverse=True)
    t = _date.fromisoformat(today)
    last7 = (t - timedelta(days=6)).isoformat()
    fz = lift_sessions(entries, rpe_map, False, complexes=cx)
    hl = lift_sessions(entries, rpe_map, True, complexes=cx)
    # V7.29: toda actividad sin tarjeta de fuerza, halterofilia o metcon sale en «Técnica y otras» (calentamientos,
    # técnica y sesiones sin detalle estructurado), para que ningún entrenamiento quede fuera de Entrenos.
    shown = {str(x["activity_id"]) for x in fz + hl + metcons}
    runs7, run_ids = 0, []
    for act in crossfit.get("activities") or []:
        aid = str((act or {}).get("activity_id") or "") if isinstance(act, dict) else ""
        if not aid or aid in shown or not act.get("date"):
            continue
        blocks = [b for b in act.get("manual_blocks") or [] if isinstance(b, dict)]
        b = blocks[0] if blocks else {}
        from .session_kind import categorize
        if categorize(b.get("activity"), act.get("name")) == "Carrera":  # V8.8: las carreras tienen su pestaña
            runs7 += act["date"] >= (_date.fromisoformat(today) - timedelta(days=6)).isoformat()
            run_ids.append(aid)
            continue
        d = b.get("detail_json") if isinstance(b.get("detail_json"), dict) else {}
        kind = d.get("type") if d.get("type") in SKIP_TYPES else "other"
        other.append({"date": act["date"], "activity_id": aid, "kind": kind,
                      "title": clip(b.get("activity") or act.get("name") or "Sesión", 90),
                      "rpe": act.get("rpe_used") if isinstance(act.get("rpe_used"), (int, float)) else None,
                      "minutes": act.get("recorded_minutes"), "note": (b.get("notes") or "")[:400]})
    mc7 = [m for m in metcons if m["date"] >= last7]
    rp = [m["rpe"] for m in mc7 if isinstance(m["rpe"], (int, float))]
    fv = weekly_volume(entries, False, today)
    hv = weekly_volume(entries, True, today)
    return {
        "fuerza": {"sessions": fz, "weekly": fv},
        "halterofilia": {"sessions": hl, "weekly": hv},
        "metcons": metcons, "otros": sorted(other, key=lambda o: (o["date"], o["activity_id"]), reverse=True),
        "carrera_ids": run_ids,  # V8.8: su tarjeta está en la pestaña Carrera (running.py)
        "summary7": {
            "fuerza": len({s["activity_id"] for s in fz if s["date"] >= last7}),
            "halterofilia": len({s["activity_id"] for s in hl if s["date"] >= last7}),
            "metcons": len(mc7), "otros": len([o for o in other if o["date"] >= last7]), "carrera": runs7,
            "metcon_rpe_mean": round(sum(rp) / len(rp), 1) if rp else None,
            "barbell_volume_kg": fv[-1]["volume"] + hv[-1]["volume"] if fv and hv else None,
        },
    }
