"""Necesidad y deuda de sueño con siestas (heurística transparente, no validada).

El sueño principal de cada día cuenta aunque sea diurno (tras una TN). Si ese día hubo dos episodios, solo consta
el principal de Garmin y la deuda puede sobrestimarse; las siestas registradas se descuentan.

necesidad de esta noche = base + recargo por carga de ayer + recargo por deuda reciente − siesta de hoy
Funciones puras: no leen la fecha del sistema.
"""
from __future__ import annotations

LOAD_ADD_MAX = 0.5   # h, a partir del sRPE de ayer relativo al p90 de 28 días
DEBT_SHARE = 0.5     # parte de la deuda de las últimas 3 noches que se recarga
DEBT_ADD_MAX = 1.0   # h
NIGHT_WINDOW = 7


def _num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def nap_minutes(ext_days: dict, date: str):
    d = (ext_days or {}).get(date)
    sd = d.get("sleep_detail") if isinstance(d, dict) else None
    return _num(sd.get("nap_minutes")) if isinstance(sd, dict) else None


def _percentile(values, q):
    vs = sorted(values)
    if not vs:
        return None
    k = (len(vs) - 1) * q
    lo = int(k)
    hi = min(lo + 1, len(vs) - 1)
    return vs[lo] + (vs[hi] - vs[lo]) * (k - lo)


def compute(trend: list, ext_days: dict, today: str, base: float = 7.5) -> dict:
    rows = [t for t in trend if isinstance(t, dict) and t.get("date", "") <= today]
    # Cuenta el sueño principal de cada día, también el diurno tras un turno de noche: es el único de ese ciclo.
    nights = [t for t in rows if _num(t.get("sleep_hours")) is not None][-NIGHT_WINDOW:]
    if len(nights) < 4:
        return {"available": False, "reason": "Hacen falta al menos 4 noches con sueño medido."}
    items = []
    for t in nights:
        nap = nap_minutes(ext_days, t["date"])
        total = t["sleep_hours"] + (nap or 0) / 60
        items.append({"date": t["date"], "night_h": t["sleep_hours"], "nap_min": nap or 0.0,
                      "shortfall_h": round(max(0.0, base - total), 2)})
    debt = round(sum(i["shortfall_h"] for i in items), 2)
    debt3 = sum(i["shortfall_h"] for i in items[-3:])
    # la misma ventana de 3 noches sin descontar siestas: es la deuda que cuenta el modelo de disponibilidad (v3)
    debt3_raw = round(sum(max(0.0, base - i["night_h"]) for i in items[-3:]), 2)
    debt_add = round(min(DEBT_ADD_MAX, DEBT_SHARE * debt3), 2)
    # carga de ayer frente al p90 de los sRPE de 28 días
    sr = [_num(t.get("srpe")) for t in rows[-28:]]
    sr = [v for v in sr if v]
    p90 = _percentile(sr, 0.9)
    prev = next((t for t in reversed(rows) if t["date"] < today), None)
    prev_sr = _num(prev.get("srpe")) if prev else None
    load_add = 0.0
    if p90 and prev_sr and len(sr) >= 5:
        load_add = round(min(LOAD_ADD_MAX, LOAD_ADD_MAX * prev_sr / p90), 2)
    nap_today = nap_minutes(ext_days, today)
    nap_h = round((nap_today or 0) / 60, 2)
    need = round(max(base - 1.0, base + load_add + debt_add - nap_h), 2)
    return {"available": True, "base_h": base, "load_add_h": load_add, "debt_add_h": debt_add,
            "nap_today_h": nap_h, "need_tonight_h": need, "debt_7n_h": debt, "debt_3n_h": round(debt3, 2),
            "debt_3n_model_h": debt3_raw, "nights": items,
            "naps_known": nap_today is not None}


def to_markdown(r: dict) -> str:
    if not r.get("available"):
        return f"Necesidad de sueño: {r.get('reason', 'sin datos')}"
    f = lambda v: f"{v:.1f}".replace(".", ",")  # noqa: E731
    rows = [("Base configurada", f(r["base_h"])), ("Recargo por carga de ayer", "+" + f(r["load_add_h"])),
            ("Recargo por deuda de las últimas 3 noches", "+" + f(r["debt_add_h"])),
            ("Siesta de hoy", "−" + f(r["nap_today_h"]) if r["naps_known"] else "sin dato"),
            ("**Necesidad estimada esta noche**", f"**{f(r['need_tonight_h'])} h**"),
            ("Deuda de las últimas 3 noches (siestas descontadas)", f(r["debt_3n_h"]) + " h"),
            ("Deuda de 7 noches (siestas descontadas)", f(r["debt_7n_h"]) + " h")]
    out = ["| Componente | Horas |", "|---|---|"] + [f"| {a} | {b} |" for a, b in rows]
    return ("\n".join(out) + "\n\nEs una estimación heurística, no validada; los recargos tienen tope y no sustituyen "
            "tu percepción. Solo cuentan siestas registradas por Garmin. El modelo de disponibilidad (v3) usa solo las últimas 3 noches y "
            f"no descuenta siestas: por eso su deuda ({f(r['debt_3n_model_h'])} h) puede ser mayor que la de 3 noches de esta tabla.")
