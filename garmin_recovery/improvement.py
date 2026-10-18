"""Análisis de mejora física y recuperación a partir de los datos publicados (sin IA, sin cifras nuevas).

Reglas simples y explícitas sobre los últimos 28 días: tendencia de HRV y FC en reposo, cantidad y regularidad del
sueño, distribución de la intensidad, respuesta a las sesiones duras, fuerza y huecos de registro. Cada hallazgo
lleva su evidencia numérica; si no hay datos suficientes lo dice y no concluye. Son criterios generales de
entrenamiento y descanso, no un diagnóstico médico ni un plan clínico.
"""
from __future__ import annotations

import csv
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import mean, median, pstdev

from . import shift_calendar, sleep_need, week_plan, weekly_compare
from .config import DEFAULTS

NEED = DEFAULTS["sleep_need_hours"]
HARD_RPE = 8
MIN_SRPE_COV = DEFAULTS["min_srpe_coverage_pct"]


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _f(v, d=0):
    return "—" if v is None else f"{v:.{d}f}".replace(".", ",")


def _ext_days(root) -> dict:
    try:
        d = json.loads((Path(root) / "garmin_extended.json").read_text(encoding="utf-8")).get("days")
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError, AttributeError):
        return {}


def _csv(root: Path, name: str) -> list[dict]:
    try:
        with (Path(root) / "history" / name).open(encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))
    except OSError:
        return []


def _finding(key, area, severity, observed, why, action, evidence=""):
    return {"key": key, "area": area, "severity": severity, "observed": observed, "why": why, "action": action,
            "evidence": evidence}


def _hrv(trend, today):
    rows = [t for t in trend if t["date"] <= today and _num(t.get("hrv_ms")) is not None]
    recent, prior = [t["hrv_ms"] for t in rows[-7:]], [t["hrv_ms"] for t in rows[:-7]]
    if len(recent) < 4 or len(prior) < 8:
        return _finding("hrv", "HRV", 0, "Datos insuficientes para comparar la última semana con tu referencia.",
                        "Hacen falta al menos 4 noches recientes y 8 anteriores.", "Mantén el reloj puesto por la noche.")
    d = (mean(recent) / median(prior) - 1) * 100
    obs = f"HRV media de los últimos {len(recent)} días: {_f(mean(recent))} ms frente a una referencia de {_f(median(prior))} ms ({'+' if d > 0 else ''}{_f(d)} %)."
    if d <= -10:
        return _finding("hrv", "HRV", 3, obs, "Una HRV sostenida por debajo de tu referencia suele acompañar a más fatiga o menos descanso.",
                        "Baja la intensidad unos días, protege el sueño y reevalúa en una semana.", obs)
    if d <= -5:
        return _finding("hrv", "HRV", 2, obs, "Tendencia algo por debajo de tu referencia.",
                        "Evita acumular días muy exigentes seguidos y vigila el sueño.", obs)
    if d >= 5:
        return _finding("hrv", "HRV", 0, obs, "Tendencia por encima de tu referencia: buena señal de recuperación.",
                        "Puedes sostener la carga actual si el sueño acompaña.", obs)
    return _finding("hrv", "HRV", 0, obs, "Estable respecto a tu referencia.", "Sin cambios necesarios.", obs)


def _rhr(trend, today):
    rows = [t for t in trend if t["date"] <= today and _num(t.get("resting_hr")) is not None]
    recent, prior = [t["resting_hr"] for t in rows[-7:]], [t["resting_hr"] for t in rows[:-7]]
    if len(recent) < 4 or len(prior) < 8:
        return None
    d = mean(recent) - median(prior)
    obs = f"FC en reposo de los últimos {len(recent)} días: {_f(mean(recent), 1)} lpm frente a {_f(median(prior), 1)} de referencia ({'+' if d > 0 else ''}{_f(d, 1)} lpm)."
    if d >= 5:
        return _finding("rhr", "FC en reposo", 3, obs, "Una FC en reposo claramente más alta que la tuya suele indicar fatiga acumulada, estrés o poco descanso.",
                        "Reduce la carga y prioriza el sueño; si se mantiene, consulta con un profesional.", obs)
    if d >= 3:
        return _finding("rhr", "FC en reposo", 2, obs, "Algo más alta que tu referencia.", "Vigila sueño y estrés; evita encadenar esfuerzos máximos.", obs)
    return _finding("rhr", "FC en reposo", 0, obs, "En línea con tu referencia.", "Sin cambios necesarios.", obs)


def _sleep(trend, today, ext_days=None):
    nights = [t for t in trend if t["date"] <= today and _num(t.get("sleep_hours")) is not None and t.get("sleep_context") != "day_sleep"][-7:]
    if len(nights) < 4:
        return _finding("sleep", "Sueño", 0, "Datos insuficientes de la última semana.", "Hacen falta al menos 4 noches.", "Duerme con el reloj puesto.")
    hs = [t["sleep_hours"] for t in nights]
    sn = sleep_need.compute(trend, ext_days or {}, today, NEED)
    debt = sn["debt_7n_h"] if sn.get("available") else sum(max(0.0, NEED - h) for h in hs)
    short = sum(1 for h in hs if h < NEED - 0.5)
    obs = (f"Media de {len(hs)} noches: {_f(mean(hs), 1)} h (necesidad configurada {_f(NEED, 1)} h); "
           f"{short} de {len(hs)} noches más de media hora por debajo; deuda acumulada {_f(debt, 1)} h (cuenta también el sueño diurno tras turno y descuenta las siestas registradas).")
    why = "El sueño es el principal factor de recuperación y de adaptación al entrenamiento."
    if debt >= 7:
        return _finding("sleep", "Sueño", 3, obs, why, "Recupera la deuda poco a poco: 30–45 min más cada noche, no una sola noche larga.", obs)
    if debt >= 3:
        return _finding("sleep", "Sueño", 2, obs, why, "Adelanta la hora de acostarte 30–45 min esta semana, sobre todo antes de un turno.", obs)
    return _finding("sleep", "Sueño", 0, obs, why, "Mantén la rutina.", obs)


def _bed_minutes(iso):
    try:
        t = datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return None
    return (t.hour * 60 + t.minute - 12 * 60) % 1440


def _regularity(root, today):
    rows = [r for r in _csv(root, "daily.csv") if r.get("date", "") <= today and r.get("sleep_context") == "night_sleep"][-14:]
    mins = [m for m in (_bed_minutes(r.get("sleep_start_local")) for r in rows) if m is not None]
    if len(mins) < 6:
        return None
    sd = pstdev(mins)
    tn = sum(1 for r in _csv(root, "daily.csv") if today >= r.get("date", "") >= (date.fromisoformat(today) - timedelta(days=13)).isoformat() and r.get("shift") == "TN")
    h, m = divmod(int(round(median(mins))) + 12 * 60, 60)
    obs = f"Hora de acostarte (mediana {h % 24:02d}:{m:02d}) con una variación típica de ±{_f(sd)} min en {len(mins)} noches; {tn} turnos TN en los últimos 14 días."
    why = "Un horario irregular reduce la calidad del sueño; con turnos rotativos es difícil, pero el ancla (hora de despertar o de la siesta) ayuda."
    if sd >= 75:
        return _finding("regularity", "Regularidad del sueño", 2, obs, why, "Fija una hora de acostarte para los días sin turno de noche y una rutina corta de siesta antes del TN.", obs)
    return _finding("regularity", "Regularidad del sueño", 0, obs, why, "Mantén el horario.", obs)


def _by_day(sessions):
    days: dict[str, float | None] = {}
    for s in sessions:
        if s.get("removed") in (1, "1", True):
            continue
        d = (s.get("date") or "")[:10]
        r = _num(s.get("rpe"))
        days[d] = max(days.get(d) or 0, r) if r is not None else days.setdefault(d, None)
    return days


def _intensity(sessions, today, coverage):
    start = (date.fromisoformat(today) - timedelta(days=27)).isoformat()
    ss = [s for s in sessions if (s.get("date") or "") >= start and s.get("removed") in (0, "0", None, False)]
    rpes = [_num(s.get("rpe")) for s in ss if _num(s.get("rpe")) is not None]
    if len(rpes) < 5:
        return _finding("intensity", "Intensidad", 0, "Pocas sesiones con RPE en 28 días para valorar la distribución.", "Hacen falta al menos 5.", "Registra el RPE de cada sesión.")
    hard = sum(1 for r in rpes if r >= HARD_RPE)
    share = hard / len(rpes) * 100
    days = _by_day(ss)
    pairs = sum(1 for d, r in days.items() if (r or 0) >= HARD_RPE and (days.get((date.fromisoformat(d) + timedelta(days=1)).isoformat()) or 0) >= HARD_RPE)
    obs = f"{hard} de {len(rpes)} sesiones con RPE registrado fueron de RPE ≥ {HARD_RPE} ({_f(share)} %); {pairs} veces hubo dos días duros seguidos."
    why = "Una parte alta de sesiones muy duras, sobre todo en días consecutivos, deja poco margen de recuperación y limita la mejora."
    cov = "" if coverage is None or coverage >= MIN_SRPE_COV else f" (cobertura de RPE {_f(coverage)} %: lectura limitada)"
    if share > 50 or pairs >= 2:
        return _finding("intensity", "Distribución de la intensidad", 2, obs + cov, why,
                        "Intercala sesiones de RPE 5–6 entre las duras y deja ≥ 48 h entre dos esfuerzos máximos.", obs)
    return _finding("intensity", "Distribución de la intensidad", 0, obs + cov, why, "Buena distribución; mantén al menos una sesión suave por semana.", obs)


def _weekly(sessions, today):
    mon = date.fromisoformat(today) - timedelta(days=date.fromisoformat(today).weekday())
    out = []
    firsts = [(s.get("date") or "")[:10] for s in sessions if (s.get("date") or "")[:10]]
    first = min(firsts) if firsts else None
    first_mon = (date.fromisoformat(first) - timedelta(days=date.fromisoformat(first).weekday())).isoformat() if first else None
    for k in range(3, -1, -1):
        a, b = mon - timedelta(weeks=k), mon - timedelta(weeks=k - 1)
        ss = [s for s in sessions if a.isoformat() <= (s.get("date") or "") < b.isoformat() and s.get("removed") in (0, "0", None, False)]
        out.append({"week": a.isoformat(), "no_data": first_mon is None or a.isoformat() < first_mon, "sessions": len(ss), "days": len({s["date"][:10] for s in ss}),
                    "srpe": round(sum(_num(s.get("srpe")) or 0 for s in ss))})
    return out


def _response(trend, sessions, today):
    byd = _by_day([s for s in sessions])
    hrv = {t["date"]: _num(t.get("hrv_ms")) for t in trend}
    after_hard, after_other = [], []
    for d, r in byd.items():
        nxt = (date.fromisoformat(d) + timedelta(days=1)).isoformat()
        if r is None or nxt > today or hrv.get(nxt) is None:
            continue
        (after_hard if r >= HARD_RPE else after_other).append(hrv[nxt])
    if len(after_hard) < 3 or len(after_other) < 3:
        return _finding("response", "Respuesta a las sesiones duras", 0,
                        f"Datos insuficientes: {len(after_hard)} días tras sesión dura y {len(after_other)} tras otras (hacen falta 3 de cada).",
                        "Sin más días no se puede ver cómo responde tu HRV.", "Se calculará solo cuando haya datos.")
    d = mean(after_hard) - mean(after_other)
    obs = (f"HRV la mañana siguiente: {_f(mean(after_hard))} ms tras sesión de RPE ≥ {HARD_RPE} (n={len(after_hard)}) "
           f"frente a {_f(mean(after_other))} ms tras las demás (n={len(after_other)}); diferencia {'+' if d > 0 else ''}{_f(d)} ms.")
    why = "Es una relación descriptiva con pocos días, no demuestra causa."
    if d <= -5:
        return _finding("response", "Respuesta a las sesiones duras", 2, obs, why, "Tras un día muy duro, planifica el siguiente suave.", obs)
    return _finding("response", "Respuesta a las sesiones duras", 0, obs, why, "Tu HRV recupera bien al día siguiente.", obs)


def _strength(crossfit):
    rows = [r for r in ((crossfit or {}).get("muscle_load") or {}).get("strength_exercises") or []
            if isinstance(r, dict) and r.get("equipment") == "barbell"]
    series: dict[str, dict[str, float]] = {}
    for r in rows:
        v = _num(r.get("e1rm_min_kg")) or _num(r.get("peak_declared_load_kg"))
        if v:
            series.setdefault(r["exercise"], {})[r["date"]] = v
    if not series:
        return _finding("strength", "Fuerza", 0, "No hay ejercicios de barra con carga registrada en 28 días.",
                        "Sin cargas no se puede seguir la fuerza.", "Apunta las cargas y repeticiones de tus series base.")
    top = sorted(((k, max(v.values())) for k, v in series.items()), key=lambda kv: -kv[1])[:3]
    obs = "Mejor valor registrado en 28 días: " + "; ".join(f"{k} {_f(v)} kg" for k, v in top) + "."
    return _finding("strength", "Fuerza", 0, obs,
                    "Es un mínimo estimado (Epley sin RIR) o la carga máxima declarada: solo se comparan series con las mismas repeticiones.",
                    "Repite 1–2 ejercicios base cada 1–2 semanas con las mismas repeticiones para medir progresión.")


def _logging(root, trend, sessions, today):
    rows = [r for r in _csv(root, "daily.csv") if r.get("date", "") <= today][-14:]
    fields = ("soreness", "fatigue", "stress_subjective", "mood", "motivation")
    filled = sum(1 for r in rows if any((r.get(f) or "").strip() for f in fields))
    no_rpe = sum(1 for s in sessions if s.get("removed") in (0, "0", None, False) and _num(s.get("rpe")) is None
                 and (s.get("date") or "") >= (date.fromisoformat(today) - timedelta(days=27)).isoformat())
    hrv_days = sum(1 for t in trend[-14:] if _num(t.get("hrv_ms")) is not None)
    obs = f"Sensaciones (fatiga, agujetas, estrés, ánimo, motivación) registradas en {filled} de los últimos {len(rows)} días."
    extra = f"Además: {no_rpe} sesiones de 28 días sin RPE y HRV con dato en {hrv_days} de 14 días."
    why = "Las sensaciones son el contraste más barato frente a los números del reloj: sin ellas, la app solo ve la parte objetiva."
    f = _finding("logging", "Registro de sensaciones", 2, obs, why, "Apunta cada mañana en Intervals 1–5 de fatiga, agujetas y ánimo (20 segundos).", obs)
    if rows and filled == 0:
        f["extra"] = extra
        return f
    if no_rpe:
        f = _finding("logging", "Registro de RPE", 1, obs, why, "Completa el RPE de las sesiones pendientes.", obs)
    else:
        f = _finding("logging", "Registro", 0, obs, why, "Sigue así.", obs)
    f["extra"] = extra
    return f


def _plan(root, result, today, sessions):
    """Plan de 7 días; vacío si no hay calendario de turnos o falla algo (nunca rompe el análisis)."""
    try:
        cal = shift_calendar.load_calendar(Path(root) / "shift_calendar.json")
        if not cal.get("source_available"):
            return []
        start = datetime.fromisoformat(today).date() if isinstance(today, str) else today
        shifts = {(start + timedelta(days=i)).isoformat(): shift_calendar.resolve_day((start + timedelta(days=i)).isoformat(), cal)
                  for i in range(8)}
        dec = result.get("decision") or {}
        legs = None
        try:
            from . import muscle_recovery
            cf = json.loads((Path(root) / "crossfit_insights.json").read_text(encoding="utf-8"))
            legs = muscle_recovery.compute(cf, today).get("legs")
        except (OSError, ValueError, KeyError, TypeError):
            legs = None  # sin detalle de ejercicios: el plan sigue siendo válido sin este margen
        return week_plan.plan(today, shifts, sessions, dec.get("zone"), (dec.get("guidance") or {}).get("rpe_max"), legs)
    except (OSError, ValueError, KeyError):
        return []


def analyze(root, result: dict, crossfit: dict | None = None) -> dict:
    root = Path(root)
    today = result.get("date") or datetime.now().date().isoformat()
    trend = [t for t in result.get("trend_28d") or [] if isinstance(t, dict)]
    sessions = [s for s in result.get("sessions_28d") or result.get("recent_sessions") or [] if isinstance(s, dict)]
    coverage = _num((result.get("load") or {}).get("srpe_coverage_28d_pct"))
    items = [_hrv(trend, today), _rhr(trend, today), _sleep(trend, today, _ext_days(root)), _regularity(root, today),
             _intensity(sessions, today, coverage), _response(trend, sessions, today), _strength(crossfit),
             _logging(root, trend, sessions, today)]
    findings = [f for f in items if f]
    priorities = sorted((f for f in findings if f["severity"] >= 1), key=lambda f: -f["severity"])[:3]
    good = [f for f in findings if f["severity"] == 0 and f["key"] in ("hrv", "rhr", "sleep", "regularity", "intensity", "response")
            and not f["observed"].startswith("Datos insuf") and not f["observed"].startswith("Pocas")]
    guidance = ((result.get("decision") or {}).get("guidance") or {})
    return {"findings": findings, "priorities": priorities, "good": good, "weekly": _weekly(sessions, today),
            "compare": weekly_compare.compare(trend, sessions, today, coverage),
            "plan": _plan(root, result, today, sessions),
            "rpe_max": guidance.get("rpe_max"), "label": guidance.get("label"),
            "coverage_pct": coverage}


def to_markdown(a: dict) -> str:
    L = ["## 8. Análisis de mejora física y recuperación\n"]
    L.append("Reglas explícitas sobre tus últimos 28 días, sin IA. Son criterios generales de entrenamiento y descanso, no un diagnóstico médico. "
             "Cuando los datos no bastan, lo dice y no concluye.\n")
    if a["priorities"]:
        L.append("### Prioridades\n")
        L.append("| # | Área | Qué muestran tus datos | Qué hacer |\n|---|---|---|---|")
        for i, f in enumerate(a["priorities"], 1):
            L.append(f"| {i} | {f['area']} | {f['observed']} | {f['action']} |")
    else:
        L.append("No hay señales de mejora prioritarias con los datos disponibles.\n")
    L.append("\n### Detalle por área\n")
    icon = {0: "✅", 1: "⚠️", 2: "⚠️", 3: "🔴"}
    for f in a["findings"]:
        ic = "ℹ️" if f["observed"].startswith(("Datos insuf", "Pocas")) else icon[f["severity"]]
        L.append(f"- {ic} **{f['area']}.** {f['observed']} {f['why']}" + (f" {f['extra']}" if f.get("extra") else ""))
    wk = a["weekly"]
    if any(w["sessions"] for w in wk if not w["no_data"]):
        L.append("\n### Constancia semanal (últimas 4 semanas)\n")
        L.append("| Semana (lunes) | Sesiones | Días con actividad | sRPE |\n|---|---|---|---|")
        for w in wk:
            lab = f"{w['week'][8:]}/{w['week'][5:7]}"
            L.append(f"| {lab} | — | — | — |" if w["no_data"] else f"| {lab} | {w['sessions']} | {w['days']} | {w['srpe']} |")
        if any(w["no_data"] for w in wk):
            L.append("\n_«—»: semanas anteriores al inicio del historial de sesiones._")
        cov = a.get("coverage_pct")
        if cov is None or cov < MIN_SRPE_COV:
            L.append(f"\n_Cobertura de RPE {_f(cov)} %: no se interpretan variaciones entre semanas._")
        else:
            L.append("\n_La semana en curso está incompleta; compara solo semanas completas._")
    if a.get("compare"):
        L.append(weekly_compare.to_markdown(a["compare"]).rstrip())
    if a.get("plan"):
        L.append("\n### Plan orientativo de 7 días\n")
        L.append(week_plan.to_markdown(a["plan"]))
    rpe = a.get("rpe_max")
    L.append("\n### Reglas para los próximos 7 días\n")
    L.append(f"1. **Hoy:** respeta la decisión del día ({a.get('label') or '—'}, RPE máx. {_f(rpe)}).")
    L.append("2. **Esfuerzos máximos:** como mucho 2–3 sesiones de RPE ≥ 8 en la semana y separadas ≥ 48 h.")
    L.append("3. **Sueño:** suma 30–45 min cada noche en lugar de una sola noche larga; antes de un turno de noche, siesta corta.")
    L.append("4. **Registro:** fatiga, agujetas y ánimo cada mañana en Intervals; RPE de cada sesión el mismo día.")
    L.append("5. **Reevaluación:** dentro de 7 días compara tu HRV media y tu FC en reposo con la referencia de 28 días.")
    L.append("\n_Los puntos 2 y 3 son criterios generales de entrenamiento y descanso, no una prescripción personalizada._")
    return "\n".join(L) + "\n"


def run(root, result: dict) -> str:
    try:
        crossfit = json.loads((Path(root) / "crossfit_insights.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        crossfit = {}
    return to_markdown(analyze(root, result, crossfit))
