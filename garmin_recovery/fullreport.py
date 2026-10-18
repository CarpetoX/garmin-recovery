"""Informe completo del ciclo (``app/informe_completo.md``): el cierre detallado, sin IA.

Todo sale de los archivos que ya publica la cadena; no se calcula ni se estima nada nuevo. Si un dato
no consta, la línea lo dice. Las notas de las sesiones se citan tal como están registradas.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import DEFAULTS

TZ = ZoneInfo("Europe/Madrid")
ZONE_ICON = {"green": "🟢", "yellow": "🟡", "red": "🔴", "unavailable": "⚪"}
DAYS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
MONTHS = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
          "octubre", "noviembre", "diciembre")
BAR = "█"


def _read(root: Path, name: str):
    try:
        return json.loads((Path(root) / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _d(obj, *path, default=None):
    for key in path:
        if isinstance(obj, dict):
            obj = obj.get(key)
        elif isinstance(obj, list) and isinstance(key, int) and -len(obj) <= key < len(obj):
            obj = obj[key]
        else:
            return default
    return default if obj is None else obj


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def n(v, dec=0, unit=""):
    v = _num(v)
    if v is None:
        return "—"
    s = f"{v:,.{dec}f}".replace(",", "§").replace(".", ",").replace("§", ".") if abs(v) >= 10000 else f"{v:.{dec}f}".replace(".", ",")
    return s + unit


def hm(minutes):
    m = _num(minutes)
    if m is None:
        return "—"
    m = round(m)
    return f"{m // 60} h {m % 60:02d} min" if m >= 60 else f"{m} min"


def pct_diff(value, ref):
    value, ref = _num(value), _num(ref)
    if value is None or not ref:
        return None
    return (value - ref) / ref * 100


def long_date(iso: str) -> str:
    d = date.fromisoformat(iso[:10])
    return f"{DAYS[d.weekday()].capitalize()}, {d.day} de {MONTHS[d.month - 1]} de {d.year}"


def short_date(iso: str) -> str:
    d = date.fromisoformat(iso[:10])
    return f"{d.day} {MONTHS[d.month - 1][:3]}"


def slot_title(when: datetime, cycle_id: str = "") -> str:
    h = int(cycle_id[-4:-2]) if len(cycle_id or "") >= 4 and cycle_id[-4:].isdigit() else when.hour
    return "Cierre matinal" if h < 12 else "Informe de tarde" if h < 20 else "Cierre nocturno"


def table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def _last_day(store: dict):
    days = (store or {}).get("days") or {}
    key = max(days) if days else None
    return key, (days.get(key) if key else None) or {}


def _clean(text, limit=420):
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def build_full_report(root, result: dict, report_id: str = "", charts_dir=None) -> str:
    root = Path(root)
    charts_ok = {p.name for p in Path(charts_dir).glob("*.svg")} if charts_dir and Path(charts_dir).is_dir() else set()
    now = datetime.fromisoformat(result["generated_at"]).astimezone(TZ) if result.get("generated_at") else datetime.now(TZ)
    today = result.get("date") or now.date().isoformat()
    dec = result.get("decision") or {}
    zone = dec.get("zone") or "unavailable"
    guidance = dec.get("guidance") or {}
    cert = (result.get("certificate") or {}).get("cycle") or {}
    ra = _read(root, "recovery_assessment.json")
    cur, base = ra.get("current") or {}, ra.get("baseline_28d") or {}
    adv = _read(root, "advanced_analytics.json")
    dq = _read(root, "data_quality.json")
    sleep_hist = _read(root, "garmin_sleep_history.json")
    hr = _read(root, "garmin_heart_rate.json")
    ext = _read(root, "garmin_extended.json")
    stress = _read(root, "garmin_stress.json")
    bb = _read(root, "garmin_body_battery.json")
    cf = _read(root, "crossfit_insights.json")
    ready = _read(root, "report_ready.json")
    cycles = _read(root, "report_cycles.json")
    shifts = (_read(root, "shift_calendar.json").get("days")) or {}
    registry = {m.get("id"): m for m in dec.get("registry") or [] if isinstance(m, dict)}
    v2, hyb = registry.get("recovery_assessment_v2", {}), registry.get("readiness_hybrid", {})
    tr = _d(ext, "days", today, "training_readiness", default={}) or _d(_last_day(ext)[1], "training_readiness", default={})
    rec_time = _d(_last_day(ext)[1], "recovery_time", default={})
    hrv_pct = pct_diff(cur.get("hrv_ms"), _d(base, "hrv_ms", "median"))
    L: list[str] = []
    add = L.append

    def img(name, alt):
        if name in charts_ok:
            add(f"\n![{alt}](charts/{name})")

    slot_id = (_read(root, "report_ready.json").get("cycle_id") or cert.get("cycle_id") or "")
    add(f"# Garmin Recovery · {slot_title(now, slot_id)}")
    add(f"\n{long_date(today)} · {now.strftime('%H:%M')}" + (f" · `{report_id}`" if report_id else ""))
    cards = [("Decisión", guidance.get("label") or dec.get("zone_es") or "—", f"RPE máx. {n(guidance.get('rpe_max'))}", zone),
             ("Recuperación v2", f"{n(v2.get('score'))}/100", f"confianza {v2.get('confidence') or '—'}", v2.get("zone") or "unavailable"),
             ("HRV", f"{n(cur.get('hrv_ms'))} ms", (f"{'+' if hrv_pct > 0 else ''}{n(hrv_pct)} % vs mediana" if hrv_pct is not None else "sin dato hoy"),
              "red" if hrv_pct is not None and hrv_pct <= -10 else "yellow" if hrv_pct is not None and hrv_pct <= -5 else "green" if hrv_pct is not None else "unavailable"),
             ("Sueño", hm(_num(cur.get("sleep_hours")) * 60 if _num(cur.get("sleep_hours")) is not None else None), f"puntuación {n(cur.get('sleep_score'))}", "unavailable"),
             ("FC en reposo", f"{n(cur.get('resting_hr'))} lpm", f"mediana {n(_d(base, 'resting_hr', 'median'))}", "unavailable"),
             ("Carga 7 días", f"{n(_d(result, 'load', 'week_sessions'))} sesiones", f"sRPE {n(_d(result, 'load', 'week_srpe'))}", "unavailable")]
    add("\n```cards\n" + "\n".join("|".join(str(x) for x in c) for c in cards) + "\n```")
    add("\n## Resumen ejecutivo\n")
    chain = cert.get("chain") or {}
    ok_stages = sum(1 for s in chain.values() if (s or {}).get("conclusion") in ("success", "publishing_in_same_job"))
    cert_ok = cert.get("status") == "ready"
    add(f"- {'🟢' if cert_ok else '🟠'} **Certificación:** ciclo {cert.get('cycle_id') or '—'} "
        f"{'validado' if cert_ok else 'sin certificar'}; {ok_stages} de {len(chain) or 4} procesos finalizados correctamente.")
    add(f"- {ZONE_ICON.get(zone, '⚪')} **Recuperación:** {n(v2.get('score'))}/100 (v2, confianza {v2.get('confidence') or '—'}). "
        f"Híbrido: {n(hyb.get('score'))}/100. **Decisión: {guidance.get('label') or dec.get('zone_es') or '—'}**, RPE máx. {n(guidance.get('rpe_max'))}.")
    add(f"- 🌙 **Sueño:** {hm(_num(cur.get('sleep_hours')) * 60 if _num(cur.get('sleep_hours')) is not None else None)}, "
        f"puntuación {n(cur.get('sleep_score'))}/100.")
    alert = []
    if hrv_pct is not None:
        alert.append(f"HRV {n(cur.get('hrv_ms'))} ms, {n(abs(hrv_pct), 1)} % {'por debajo' if hrv_pct < 0 else 'por encima'} de tu mediana de 28 días")
    nh, nm = _num(cur.get("night_hr")), _num(_d(base, "night_hr", "median"))
    if nh is not None and nm is not None and nh - nm >= 3:
        alert.append(f"FC nocturna {n(nh, 1)} lpm ({n(nh - nm, 1)} sobre la mediana)")
    if alert:
        add("- ❤️ **Principal alerta:** " + "; ".join(alert) + ".")
    add(f"- 🏋️ **Qué hacer:** {guidance.get('text') or '—'}")

    # 1 ------------------------------------------------------------------
    add("\n## 1. Certificación y calidad\n")
    cyc_id = ready.get("cycle_id") or cert.get("cycle_id")
    entry = next((c for c in (cycles.get("cycles") or []) if isinstance(c, dict) and c.get("cycle_id") == cyc_id), None)
    names = {"sync": "Sync", "heart": "Heart Rate", "advanced": "Advanced Analytics", "crossfit": "CrossFit Insights"}
    concl = {"success": "Correcto", "publishing_in_same_job": "Correcto (publicando en este mismo ciclo)"}
    rows = [["Ciclo", cyc_id or "—"], ["Estado del certificado", str(ready.get("status") or cert.get("status") or "—").upper()]]
    for key, label in names.items():
        c = chain.get(key) or {}
        rows.append([label, concl.get(c.get("conclusion"), c.get("conclusion") or "—")])
    rows += [["Certificado generado", (ready.get("verified_at") or cert.get("verified_at") or "—")[11:19] or "—"],
             ["Instantánea inmutable (SHA-256)", "Disponible" if entry and entry.get("snapshot_sha256") else "No consta"],
             ["Confianza de recuperación", ra.get("confidence") or "—"],
             ["Calidad fisiológica de los datos", f"{n(dq.get('score'))}/100 ({dq.get('status') or '—'})"]]
    add(table(["Comprobación", "Resultado"], rows))
    missed = (_d(result, "certificate", "execution_health", "missed_slots", default=[]) or [])
    if missed:
        add(f"\n⚠️ Franjas de Sync sin ejecutar o recuperadas tarde: {', '.join(str(m)[5:16].replace('T', ' ') for m in missed)}.")
    add("\nLa calidad describe los datos disponibles, no el software. No se han incorporado mediciones posteriores al ciclo.")
    try:
        from . import source_health
        add(source_health.to_markdown(source_health.collect(root)).rstrip())
    except Exception as exc:  # noqa: BLE001 - el estado de fuentes nunca debe impedir el informe
        add(f"\n_Estado de las fuentes no disponible en este ciclo ({type(exc).__name__})._")

    # 2 ------------------------------------------------------------------
    add("\n## 2. Recuperación fisiológica\n")
    rows = []
    for label, key, dec_, unit in (("HRV", "hrv_ms", 0, " ms"), ("FC en reposo", "resting_hr", 0, " lpm"),
                                   ("FC nocturna", "night_hr", 1, " lpm"), ("Puntuación de sueño", "sleep_score", 0, "")):
        rows.append([label, n(cur.get(key), dec_, unit), n(_d(base, key, "median"), dec_, unit), n(_d(base, key, "n"))])
    sh = _num(cur.get("sleep_hours"))
    rows.insert(3, ["Duración del sueño", hm(sh * 60) if sh is not None else "—",
                    hm(_d(base, "sleep_hours", "median") * 60) if _num(_d(base, "sleep_hours", "median")) is not None else "—",
                    n(_d(base, "sleep_hours", "n"))])
    add(table(["Indicador", "Hoy", "Mediana fusionada 28 días", "Días"], rows))
    add("\nLas referencias son medianas históricas, no objetivos.")
    notes = []
    if hrv_pct is not None:
        notes.append(f"La HRV está {n(abs(hrv_pct), 0)} % {'por debajo' if hrv_pct < 0 else 'por encima'} de su mediana")
    rhr, rhm = _num(cur.get("resting_hr")), _num(_d(base, "resting_hr", "median"))
    if rhr is not None and rhm is not None:
        notes.append(f"la FC en reposo está {n(abs(rhr - rhm))} lpm {'por encima' if rhr > rhm else 'por debajo'}" if rhr != rhm else "la FC en reposo coincide con su mediana")
    if notes:
        add("\n" + "; ".join(notes) + ".")
    img("hrv.svg", "HRV nocturna con tu rango normal")
    img("readiness.svg", "Disponibilidad: oficial frente a v3")
    add("\n### Modelos de recuperación\n")
    rows = [[m.get("label"), f"{ZONE_ICON.get(m.get('zone'), '⚪')} {n(m.get('score'))}/100" if m.get("score") is not None else "—", m.get("role") or "—"]
            for m in dec.get("registry") or [] if isinstance(m, dict)]
    if not any("Training Readiness" in str(r[0]) for r in rows):
        rows.append(["Garmin Training Readiness", f"{n(tr.get('score'))}/100 ({tr.get('level') or '—'})", "contexto"])
    rows.append(["Tiempo de recuperación Garmin", n(rec_time.get("hours"), 1, " h"), "contexto"])
    pri = adv.get("personal_recovery_index") or {}
    rows.append(["Índice personal experimental", f"{n(pri.get('score'))}/100", "provisional"])
    add(table(["Modelo", "Resultado", "Papel"], rows))
    if dec.get("divergence"):
        dv = dec["divergence"]
        add("\n_Divergencia entre modelos:_ " + _clean(dv if isinstance(dv, str) else " ".join(str(x) for x in (dv if isinstance(dv, list) else [dv])), 300))
    try:
        from . import why_changed
        add("\n**Qué ha cambiado desde ayer**\n\n" + why_changed.to_markdown(why_changed.compute(result.get("trend_28d") or [], today)))
    except Exception:  # noqa: BLE001 — bloque opcional
        pass
    add("\nLas puntuaciones no son equivalentes entre sí. La decisión es la zona más conservadora entre v2 (oficial), híbrido y v3; "
        "un rojo prevalece. El índice personal es provisional y no es una medida clínica.")

    # 3 ------------------------------------------------------------------
    add("\n## 3. Sueño y recuperación nocturna\n")
    skey, sday = _last_day(sleep_hist)
    if sday and sday.get("sleep_start_local"):
        add(f"Episodio confirmado: {long_date(sday['sleep_start_local']).split(',')[1].strip()}, {sday['sleep_start_local'][11:16]} → "
            f"{long_date(sday['sleep_end_local']).split(',')[1].strip()}, {sday['sleep_end_local'][11:16]}"
            + ("." if sday.get("window_confirmed") else " (ventana sin confirmar)."))
        total = _num(sday.get("sleep_hours"))
        rows = [["Duración efectiva", hm(total * 60) if total is not None else "—"], ["Puntuación", f"{n(sday.get('sleep_score'))}/100"]]
        for label, key in (("Sueño profundo", "deep_minutes"), ("Sueño REM", "rem_minutes")):
            rows.append([label, hm(sday.get(key))])
        add("\n" + table(["Dato", "Valor"], rows))
        rem, tot_min = _num(sday.get("rem_minutes")), (total or 0) * 60
        if rem is not None and tot_min:
            add(f"\nEl REM representa un {n(rem / tot_min * 100)} % y el sueño profundo un {n((_num(sday.get('deep_minutes')) or 0) / tot_min * 100)} % del episodio.")
        sp, sm = _num(cur.get("sleep_score")), _num(_d(base, "sleep_score", "median"))
        if total is not None and sp is not None and sm is not None and _num(_d(base, "sleep_hours", "median")):
            if total * 60 >= _d(base, "sleep_hours", "median") * 60 and sp < sm:
                add("La duración supera tu referencia, pero la puntuación queda por debajo: más horas no se acompañan de una recuperación igual de favorable.")
    else:
        add("No consta un episodio de sueño confirmado en los datos de este ciclo.")
    img("sleep.svg", "Sueño por noche frente a tu necesidad")
    img("sleep_stages.svg", "Sueño por fases")
    try:
        from . import sleep_need
        add("\n**Necesidad y deuda de sueño**\n\n" + sleep_need.to_markdown(
            sleep_need.compute(result.get("trend_28d") or [], ext.get("days") or {}, today,
                               DEFAULTS["sleep_need_hours"])))
    except Exception:  # noqa: BLE001 — el informe no depende de este bloque
        pass
    add("\nNo se incorporan siestas no confirmadas.")

    # 4 ------------------------------------------------------------------
    add("\n## 4. Frecuencia cardíaca y tendencias\n")
    hday = _d(hr, "days", today, default={}) or _last_day(hr)[1]
    rolling = hr.get("rolling") or {}
    rows = [["Hoy" + ("*" if hday.get("partial_day") else ""), n(hday.get("daytime_avg_hr"), 1, " lpm"), n(hday.get("nighttime_avg_hr"), 1, " lpm")]]
    for label, key in (("3 días", "3d"), ("7 días", "7d"), ("28 días", "28d")):
        w = rolling.get(key) or {}
        rows.append([label, n(w.get("daytime_avg_hr"), 1, " lpm"), n(w.get("nighttime_avg_hr"), 1, " lpm")])
    add(table(["Ventana", "FC diurna", "FC nocturna"], rows))
    if hday.get("partial_day"):
        add("\n\\* La FC diurna de hoy es de un día parcial: no es FC en reposo.")
    cov = adv.get("recovery_data_coverage") or {}
    add("\nCobertura histórica fusionada (días con dato de 28):\n")
    add(table(["Indicador", "Datos disponibles"], [[label, f"{n(_d(cov, k, 'days_present'))}/{n(_d(cov, k, 'days_expected', default=28))} días"]
                                                   for label, k in (("HRV", "hrv_ms"), ("Sueño", "sleep_hours"), ("Puntuación de sueño", "sleep_score"), ("FC en reposo", "resting_hr"))]))
    img("rhr.svg", "FC en reposo y nocturna")
    add("\n### Estrés y Body Battery\n")
    _, sd = _last_day(stress)
    avg_s, max_s = (_num(sd.get("avgStressLevel")), _num(sd.get("maxStressLevel")))
    add(f"- Estrés medio: {n(avg_s) if avg_s is not None and avg_s >= 0 else '—'}, máximo {n(max_s) if max_s is not None and max_s >= 0 else '—'}.")
    _, bd = _last_day(bb)
    arr = [p for p in (bd.get("bodyBatteryValuesArray") or []) if isinstance(p, list) and len(p) >= 2 and p[1] is not None]
    if arr:
        ts = datetime.fromtimestamp(arr[-1][0] / 1000, TZ)
        late = (now - ts).total_seconds() / 60
        add(f"- Body Battery: último valor {n(arr[-1][1])}/100, medido a las {ts.strftime('%H:%M')}"
            + (f" (hace {hm(late)}: no es una medición nueva)." if late > 90 else "."))
    hrr = _d(adv, "heart_rate_recovery", "trends", "last_7_sessions", "metrics", "hrr_1min", default={})
    if hrr.get("n"):
        add(f"- Recuperación de FC a 1 min tras el ejercicio: {n(hrr.get('n'))} observaciones recientes, mediana {n(hrr.get('median'), 1)} lpm"
            + (" (insuficientes para una tendencia robusta)." if hrr.get("n", 0) < 5 else "."))

    # 5 ------------------------------------------------------------------
    add("\n## 5. Rendimiento CrossFit\n")
    wr = cf.get("weekly_report") or {}
    sess7 = [s for s in result.get("sessions_28d") or [] if isinstance(s, dict) and (s.get("date") or "") >= (date.fromisoformat(today) - timedelta(days=6)).isoformat()]
    add(f"Última actividad registrada: {short_date(cf['latest_activity_date']) if cf.get('latest_activity_date') else '—'}. "
        "Un día sin registro no demuestra que fuera de descanso.")
    rows = [["Sesiones registradas", n(wr.get("activities", len(sess7)))],
            ["Días con actividad", n(_d(adv, "weekly_load", "active_days"))],
            ["RPE medio", n(wr.get("mean_rpe"), 2)],
            ["Sesiones de RPE ≥ 8", n(sum(1 for s in sess7 if (_num(s.get("rpe")) or 0) >= 8))],
            ["Minutos grabados (Garmin)", n(sum(_num(s.get("duration_min")) or 0 for s in sess7), 1, " min")],
            ["sRPE por duración registrada", n(wr.get("recorded_srpe_sum"))],
            ["TRIMP", n(sum(_num(s.get("trimp")) or 0 for s in sess7), 1)],
            ["Carga de actividades (Intervals)", n(sum(_num(s.get("load")) or 0 for s in sess7))],
            ["Volumen externo mínimo verificado", n(wr.get("minimum_verified_strength_volume_kg"), 0, " kg")]]
    img("sessions.svg", "Sesiones de los últimos 14 días")
    img("rpe.svg", "RPE frente al máximo del día")
    img("load.svg", "Carga diaria, ATL y CTL")
    add("\n### Últimos 7 días\n\n" + table(["Métrica", "Resultado"], rows))
    add("\nEl volumen es un mínimo cuantificable, no un tonelaje comparable entre barra, mancuernas y máquinas.")
    s28 = [s for s in result.get("sessions_28d") or [] if isinstance(s, dict)]
    rp28 = [_num(s.get("rpe")) for s in s28 if _num(s.get("rpe")) is not None]
    add(f"\nÚltimos 28 días: {len(s28)} sesiones, RPE medio {n(sum(rp28) / len(rp28), 2) if rp28 else '—'}, "
        f"TRIMP {n(sum(_num(s.get('trimp')) or 0 for s in s28), 1)} y {n(sum(_num(s.get('duration_min')) or 0 for s in s28), 1)} minutos grabados.")
    daily = _d(adv, "weekly_load", "daily_load", default={}) or {}
    if daily:
        top = max((v for v in daily.values() if _num(v) is not None), default=0) or 1
        add("\n### sRPE diario registrado\n\n```")
        for day in sorted(daily):
            v = daily[day]
            bar = BAR * max(1, round((v or 0) / top * 12)) if (v or 0) > 0 else "—"
            add(f"{short_date(day):<7}{bar:<14}{n(v) if (v or 0) > 0 else 'sin registro'}")
        add("```")
        peak = max(daily, key=lambda k: daily[k] or 0)
        if (daily[peak] or 0) > 0:
            add(f"\nEl {short_date(peak)} concentra la mayor carga sRPE de la semana. La relación con las señales de recuperación es descriptiva, no causal.")
    if _num(_d(adv, "weekly_load", "monotony")) is not None and _d(adv, "weekly_load", "valid_for_interpretation"):
        add(f"\nMonotonía {n(_d(adv, 'weekly_load', 'monotony'), 1)} · strain {n(_d(adv, 'weekly_load', 'strain'))} (descriptores de contexto, sin umbral médico).")

    # 6 ------------------------------------------------------------------
    add("\n## 6. Fuerza, halterofilia y metcons\n")
    lo = (date.fromisoformat(today) - timedelta(days=6)).isoformat()
    shown = 0
    for a in cf.get("activities") or []:
        if not isinstance(a, dict) or (a.get("date") or "") < lo:
            continue
        for b in a.get("manual_blocks") or []:
            if not isinstance(b, dict) or not (b.get("notes") or b.get("detail_json")):
                continue
            head = f"**{short_date(a['date'])} — {_clean(b.get('activity'), 90)}**"
            bits = [f"RPE {n(b.get('rpe'), 1).replace(',0', '')}" if b.get("rpe") is not None else None]
            vol = _num(b.get("minimum_verified_volume_kg"))
            if vol:
                bits.append(f"volumen de barra cuantificado {n(vol, 0, ' kg')}" + ("" if b.get("volume_complete") else " (parcial)"))
            add(f"- {head}" + (" · " + " · ".join(x for x in bits if x) if any(bits) else ""))
            if b.get("notes"):
                add(f"  {_clean(b['notes'])}")
            shown += 1
    if not shown:
        add("No hay sesiones con detalle registrado en los últimos 7 días.")
    best = (_d(cf, "muscle_load", "best_estimated_1rm_by_exercise") or {})
    if isinstance(best, dict) and best:
        top = sorted(((k, v) for k, v in best.items() if isinstance(v, dict)), key=lambda kv: -(_num(kv[1].get("e1rm_min_kg")) or _num(kv[1].get("kg")) or 0))[:3]
        if top:
            add("\n1RM mínimo estimado (Epley, ≤ 10 repeticiones, sin RIR): " + "; ".join(
                f"{k} {n(_num(v.get('e1rm_min_kg')) or _num(v.get('kg')), 0, ' kg')}" for k, v in top) + ".")
    add("\nNo se atribuyen desgloses no confirmados ni se comparan récords no equivalentes; se conserva la diferencia entre cronómetro oficial y reloj.")

    # 7 ------------------------------------------------------------------
    add("\n## 7. Balance y orientación\n")
    tomorrow = (date.fromisoformat(today) + timedelta(days=1)).isoformat()
    add(f"Turno: hoy {shifts.get(today, 'sin dato')}, mañana {shifts.get(tomorrow, 'sin dato')}.")
    good, bad = [], []
    sh_ = _num(cur.get("sleep_hours"))
    if sh_ is not None and _num(_d(base, "sleep_hours", "median")) and sh_ >= _d(base, "sleep_hours", "median"):
        good.append("duración del sueño igual o superior a tu referencia")
    if hrv_pct is not None:
        (bad if hrv_pct <= -10 else good if hrv_pct >= 0 else []).append("HRV " + ("baja" if hrv_pct <= -10 else "en rango") + " respecto a tu historial")
    if nh is not None and nm is not None and nh - nm >= 3:
        bad.append("FC nocturna elevada")
    if _num(tr.get("score")) is not None and tr["score"] < 40:
        bad.append(f"Training Readiness de Garmin bajo ({n(tr['score'])}/100)")
    if arr and arr[-1][1] < 25:
        bad.append(f"Body Battery bajo ({n(arr[-1][1])}/100)")
    if good:
        add("- Señales favorables: " + "; ".join(good) + ".")
    if bad:
        add("- Señales adversas: " + "; ".join(bad) + ".")
    add("\n### Recomendaciones\n")
    recs = [f"**{guidance.get('label') or 'Sigue la decisión del día'}** — {guidance.get('text') or ''}".strip(" —")]
    if now.hour >= 20:
        recs.append("Prioriza el próximo sueño y comprueba al despertar si HRV, FC en reposo y puntuación de sueño se acercan a tus referencias.")
    else:
        recs.append("Ajusta la sesión de hoy con las reglas por tipo del informe del ciclo (`app/informe.md`).")
    recs.append("Registra sensaciones y fatiga percibida en Intervals: ayudan a contextualizar la recuperación tras varios entrenamientos exigentes.")
    for i, r in enumerate(recs, 1):
        add(f"{i}. {r}")
    img("strength.svg", "Progresión de fuerza")
    from . import improvement
    try:
        add("\n" + improvement.run(root, result).rstrip())
    except Exception as exc:  # noqa: BLE001 — el análisis de mejora nunca debe bloquear el informe
        add(f"\n## 8. Análisis de mejora física y recuperación\n\n_No se pudo calcular en este ciclo ({type(exc).__name__})._")
    add("\n## Conclusión\n")
    add(f"Datos {'suficientes' if v2.get('state') in ('assessed', None) and zone != 'unavailable' else 'insuficientes'} para evaluar la recuperación de hoy: "
        f"la decisión es **{ZONE_ICON.get(zone, '')} {guidance.get('label') or dec.get('zone_es') or '—'}**. "
        "No es un diagnóstico médico. Que el informe esté publicado no prueba que se haya leído una notificación.")
    add("\n---\n")
    add(f"Traza: {slot_title(now, slot_id).lower()} · ciclo {cyc_id or '—'} · generado {now.strftime('%d/%m/%Y %H:%M')} Europe/Madrid · "
        f"certificado {str(ready.get('status') or '—').upper()} · sync_run_id {_d(chain, 'sync', 'run_id') or '—'}.")
    return "\n".join(L) + "\n"
