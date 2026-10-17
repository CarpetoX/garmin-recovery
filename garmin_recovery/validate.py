"""Validación de las salidas publicadas (JSON, Markdown, SVG e historial).

Se ejecuta en la cadena justo después de generar el informe. Si falla, el
workflow restaura la versión anterior de ``app/`` e ``history/`` para que nunca
se publique un informe roto o incoherente, y deja constancia en
``app/validation.json``.
"""
from __future__ import annotations

import csv
import json
import re
import xml.dom.minidom
from pathlib import Path

GR_RE = re.compile(r"^GR-\d{4}-\d{2}-\d{2}-\d{4}-[0-9a-f]{6}$")
ZONES = {"green", "yellow", "red", "unavailable"}


def _check(errors: list, cond: bool, msg: str) -> None:
    if not cond:
        errors.append(msg)


def validate(root: str | Path = ".") -> dict:
    root = Path(root)
    app, hist = root / "app", root / "history"
    errors: list[str] = []
    checks = 0

    # 1) Contrato JSON
    try:
        data = json.loads((app / "readiness_v3.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"status": "failed", "errors": [f"readiness_v3.json ilegible: {type(exc).__name__}"], "checks": 1}
    for key, typ in (("schema_version", int), ("app_version", str), ("date", str), ("generated_at", str),
                     ("decision", dict), ("readiness", dict), ("load", dict), ("certificate", dict),
                     ("training_integrity", dict), ("trend_28d", list)):
        checks += 1
        _check(errors, isinstance(data.get(key), typ), f"json: '{key}' ausente o de tipo incorrecto")
    dec = data.get("decision") or {}
    g = dec.get("guidance") or {}
    checks += 4
    _check(errors, dec.get("zone") in ZONES, "json: decision.zone inválida")
    _check(errors, isinstance(g.get("rpe_max"), int) and 0 <= g["rpe_max"] <= 10, "json: guidance.rpe_max fuera de rango")
    _check(errors, bool(g.get("text")), "json: guidance.text vacío")
    voting = [m for m in dec.get("registry") or [] if m.get("used_in_decision")]
    order = {"unavailable": 0, "red": 1, "yellow": 2, "green": 3}
    if voting and dec.get("zone") in order and all(m.get("zone") in order for m in voting):
        _check(errors, order[dec["zone"]] == min(order[m["zone"]] for m in voting),
               "json: la decisión no es la más conservadora de los modelos")
    for p in (data.get("planned") or {}).get("today") or []:
        checks += 1
        _check(errors, p.get("rpe_max") is not None and p["rpe_max"] <= g.get("rpe_max", 10),
               "json: un ajuste del plan supera el RPE máximo de la decisión")
    dates = [t.get("date") for t in data.get("trend_28d") or []]
    checks += 1
    _check(errors, dates == sorted(dates) and len(set(dates)) == len(dates) and (not dates or dates[-1] == data.get("date")),
           "json: fechas de tendencia desordenadas, duplicadas o sin el día actual")
    checks += 1
    _check(errors, "NaN" not in json.dumps(data), "json: contiene NaN")

    # 2) Informe Markdown + identificador GR
    md_path = app / "informe.md"
    report_id = None
    if md_path.exists():
        md = md_path.read_text(encoding="utf-8")
        m = re.search(r"`(GR-[^`]+)`", md)
        report_id = m.group(1) if m else None
        checks += 5
        _check(errors, bool(report_id and GR_RE.match(report_id)), "md: identificador GR ausente o mal formado")
        _check(errors, report_id is not None and md.count(report_id) >= 2, "md: el identificador no aparece en cabecera y certificado")
        _check(errors, bool(g.get("text")) and g["text"] in md, "md: la recomendación no coincide con decision.guidance")
        _check(errors, "None" not in md and "NaN" not in md, "md: contiene None/NaN")
        _check(errors, "## Certificado" in md, "md: falta el certificado")
        # 3) Gráficas enlazadas
        for name in re.findall(r"\(charts/([A-Za-z0-9_.-]+\.svg)\)", md):
            checks += 1
            svg = app / "charts" / name
            try:
                doc = xml.dom.minidom.parseString(svg.read_text(encoding="utf-8"))
                _check(errors, doc.documentElement.tagName == "svg", f"svg: {name} no es SVG")
            except (OSError, Exception):  # noqa: BLE001 — cualquier fallo de lectura/parseo invalida
                errors.append(f"svg: {name} ausente o inválido")
    else:
        checks += 1
        errors.append("md: falta app/informe.md")

    # 4) Historial
    reports = hist / "reports.csv"
    if reports.exists():
        rows = list(csv.DictReader(reports.open(encoding="utf-8")))
        ids = [r.get("report_id") for r in rows]
        checks += 3
        _check(errors, all(i and GR_RE.match(i) for i in ids), "historial: identificador GR inválido en reports.csv")
        _check(errors, len(ids) == len(set(ids)), "historial: identificadores GR duplicados")
        _check(errors, not report_id or (ids and ids[-1] == report_id), "historial: el último registro no es el informe publicado")
    daily = hist / "daily.csv"
    if daily.exists():
        dd = [r.get("date") for r in csv.DictReader(daily.open(encoding="utf-8"))]
        checks += 1
        _check(errors, dd == sorted(dd) and len(dd) == len(set(dd)), "historial: daily.csv con fechas duplicadas o desordenadas")

    return {"status": "ok" if not errors else "failed", "checks": checks, "errors": errors,
            "report_id": report_id, "app_version": data.get("app_version"), "generated_at": data.get("generated_at")}


def write_result(root: str | Path, result: dict) -> None:
    out = Path(root) / "app" / "validation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
