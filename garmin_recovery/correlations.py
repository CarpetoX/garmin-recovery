"""Diario de correlaciones: ¿cambia tu HRV del día siguiente según un factor del día anterior?

Compara medias con y sin el factor (mín. 5 y 5 días en 90). Sin causalidad ni significación estadística.
"""
from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path
from statistics import mean

MIN_GROUP = 5
WINDOW_DAYS = 90
MIN_DIFF_MS = 4.0

FACTORS = (
    ("trained", "Día anterior con sesión registrada", lambda r: (_num(r.get("sessions")) or 0) > 0),
    ("night_shift", "Día anterior con turno de noche (TN)", lambda r: (r.get("shift") or "").strip() == "TN"),
    ("short_sleep", "Noche anterior de menos de 6,5 h", lambda r: (_num(r.get("sleep_hours")) or 99) < 6.5),
)


def _num(v):
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def load(root) -> list[dict]:
    try:
        with (Path(root) / "history" / "daily.csv").open(encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))
    except OSError:
        return []


def compute(rows: list[dict], today: str) -> dict:
    t = date.fromisoformat(today)
    lo = (t - timedelta(days=WINDOW_DAYS)).isoformat()
    by = {r["date"]: r for r in rows if lo <= r.get("date", "") <= today}
    out = []
    for key, label, pred in FACTORS:
        a, b = [], []
        for d, r in by.items():
            nxt = by.get((date.fromisoformat(d) + timedelta(days=1)).isoformat())
            hrv = _num(nxt.get("hrv_ms")) if nxt else None
            # el factor solo se evalúa con datos que lo midan; un hueco no cuenta como "sin factor"
            if hrv is None or (key == "short_sleep" and _num(r.get("sleep_hours")) is None) \
                    or (key == "night_shift" and not (r.get("shift") or "").strip()):
                continue
            (a if pred(r) else b).append(hrv)
        item = {"key": key, "label": label, "n_with": len(a), "n_without": len(b)}
        if len(a) >= MIN_GROUP and len(b) >= MIN_GROUP:
            diff = round(mean(a) - mean(b), 1)
            item.update(ok=True, with_ms=round(mean(a), 1), without_ms=round(mean(b), 1), diff_ms=diff, notable=abs(diff) >= MIN_DIFF_MS)
        else:
            item["ok"] = False
        out.append(item)
    return {"window_days": WINDOW_DAYS, "factors": out}


def to_markdown(r: dict) -> str:
    f = lambda v: f"{v:.1f}".replace(".", ",")  # noqa: E731
    lines = ["| Factor | Con | Sin | HRV siguiente día (con / sin) | Diferencia |", "|---|---|---|---|---|"]
    for i in r["factors"]:
        if i["ok"]:
            diff = ("**" + ("+" if i["diff_ms"] > 0 else "") + f(i["diff_ms"]).rstrip("0").rstrip(",") + " ms**") if i["notable"] \
                else ("+" if i["diff_ms"] > 0 else "") + f(i["diff_ms"]) + " ms (pequeña)"
            lines.append(f"| {i['label']} | {i['n_with']} | {i['n_without']} | {f(i['with_ms'])} / {f(i['without_ms'])} ms | {diff} |")
        else:
            lines.append(f"| {i['label']} | {i['n_with']} | {i['n_without']} | — | datos insuficientes (mín. {MIN_GROUP} y {MIN_GROUP}) |")
    return "\n".join(lines) + ("\n\nSon asociaciones en tus propios datos de los últimos 90 días, sin causalidad ni prueba estadística; "
                               "con pocos días pueden ser casualidad.")
