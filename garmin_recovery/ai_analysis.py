"""Análisis de Claude (``app/analisis_ia.md``): lo escribe la rutina de Claude; la app solo lo comprueba y lo muestra.

El archivo empieza por ``<!-- cycle_id: AAAA-MM-DD-HHMM[-sufijo] -->`` (el sufijo, p. ej. ``-post-sleep``, forma parte del ID). Se publica solo si es del ciclo vigente
(``report_ready.json``); si es de otro, se marca como desactualizado. Además se avisan las cifras del texto
que no aparecen en los datos del ciclo (aviso visible, no bloqueo).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HEADER = re.compile(r"\A\s*<!--\s*cycle_id:\s*([0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{4}(?:-[A-Za-z0-9_]+)*)\s*-->\s*")
NUM = re.compile(r"(?<![\w.,])\d+(?:[.,]\d+)?")
SOURCES = ("app/informe_completo.md", "app/informe.md", "app/readiness_v3.json", "recovery_assessment.json",
           "garmin_extended.json", "garmin_stress.json", "garmin_heart_rate.json", "garmin_sleep_history.json",
           "advanced_analytics.json", "crossfit_insights.json", "shift_calendar.json")


def _norm(tok: str) -> str:
    tok = tok.replace(",", ".")
    return tok.rstrip("0").rstrip(".") if "." in tok else tok


def _known(root: Path) -> set[str]:
    known: set[str] = set()
    for rel in SOURCES:
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except OSError:
            continue
        for t in NUM.findall(text):
            known.add(_norm(t))
            if "." in t.replace(",", "."):
                known.add(str(round(float(t.replace(",", ".")))))
    return known


def check(root) -> dict:
    """``{"state": absent|ok|stale|invalid, "body", "cycle_id", "unverified": [...]}``."""
    root = Path(root)
    path = root / "app" / "analisis_ia.md"
    if not path.exists():
        return {"state": "absent"}
    raw = path.read_text(encoding="utf-8")
    m = HEADER.match(raw)
    if not m:
        return {"state": "invalid", "reason": "falta la marca cycle_id"}
    body = raw[m.end():].strip()
    try:
        current = json.loads((root / "report_ready.json").read_text(encoding="utf-8")).get("cycle_id")
    except (OSError, ValueError):
        current = None
    if not body:
        return {"state": "invalid", "reason": "vacío", "cycle_id": m.group(1)}
    known = _known(root)
    unverified = sorted({t for t in NUM.findall(body) if len(t.replace(",", "").replace(".", "")) >= 2
                         and _norm(t) not in known and not re.fullmatch(r"20\d\d", t)})
    return {"state": "ok" if current and m.group(1) == current else "stale", "body": body,
            "cycle_id": m.group(1), "current": current, "unverified": unverified}


def section(root) -> str:
    """Markdown de la sección «Análisis de Claude» ('' si no hay archivo)."""
    r = check(root)
    if r["state"] == "absent":
        return ""
    out = ["\n## Análisis de Claude\n"]
    if r["state"] == "invalid":
        return "".join(out) + f"_Análisis no publicado: {r.get('reason')}._\n"
    if r["state"] == "stale":
        out.append(f"⚠️ _Este análisis es del ciclo {r['cycle_id']}; el informe de arriba es del {r.get('current') or '—'}. "
                   "Aún no hay análisis del ciclo vigente._\n")
    if r["unverified"]:
        out.append("⚠️ _Cifras de este texto que no constan en los datos del ciclo: " + ", ".join(r["unverified"][:12])
                   + ". Contrástalas con el informe._\n")
    out.append(r["body"] + "\n")
    out.append("\n_Texto redactado por un modelo de IA a partir de los datos del ciclo; no es un diagnóstico médico._\n")
    return "\n".join(out)


LEAD = re.compile(r"^\*\*En breve:?\*\*:?\s*(.+)$", re.M)


def lead(root) -> str | None:
    """Párrafo «**En breve:** …» del análisis, solo si es del ciclo vigente (para mostrarlo en el panel)."""
    r = check(root)
    if r.get("state") != "ok":
        return None
    m = LEAD.search(r["body"])
    return m.group(1).strip() if m else None
