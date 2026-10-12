#!/usr/bin/env python3
"""Garmin Recovery V4.0: informative, deterministic and safe certified-cycle reports.

Only reads the snapshot embedded in report_cycles.json. No network, no live
measurement, no modification of historical data, no ChatGPT delivery claims.
Run in parallel with V3.9; do not use as a production replacement yet.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile

from cycle_snapshot_report_v38 import SnapshotError, build

SAFE_ID = re.compile(r"\A\d{4}-\d{2}-\d{2}-\d{4}(?:-post-sleep)?\Z", re.ASCII)


def obj(value):
    return value if isinstance(value, dict) else {}


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def fmt(value, suffix="", decimals=1):
    if not number(value):
        return "No disponible"
    return f"{value:.{decimals}f}{suffix}" if isinstance(value, float) else f"{value}{suffix}"


def safe(value, max_length=150):
    if value is None:
        return "No disponible"
    return str(value).replace("|", "/").replace("\r", " ").replace("\n", " ").replace("`", "'")[:max_length]


def latest_id(ledger):
    if not isinstance(ledger, dict) or not isinstance(ledger.get("cycles"), list):
        raise SnapshotError("Invalid ledger")
    eligible = [r for r in ledger["cycles"] if isinstance(r, dict)
                and r.get("state") == "data_ready" and isinstance(r.get("cycle_id"), str)]
    if not eligible:
        raise SnapshotError("No data_ready cycles")
    # Never fall back to an older cycle when the newest certificate is invalid.
    row = max(eligible, key=lambda r: (str(r.get("ready_at") or ""), r["cycle_id"]))
    return row["cycle_id"]


def render(ledger, cycle_id):
    """Return markdown and a deterministic metadata dict, with integrity checked first."""
    if not isinstance(cycle_id, str) or not SAFE_ID.fullmatch(cycle_id):
        raise SnapshotError("Unsafe cycle id")
    cert = build(ledger, cycle_id)
    data = cert["data"]
    recovery = obj(data.get("recovery_assessment"))
    current = obj(recovery.get("current"))
    baseline = obj(recovery.get("baseline_28d"))
    daily = obj(data.get("daily"))
    quality = obj(data.get("data_quality"))
    garmin = obj(data.get("garmin"))
    extended = obj(garmin.get("extended_today"))
    heart_today = obj(garmin.get("heart_rate_today"))
    rolling = obj(garmin.get("heart_rate_rolling"))
    crossfit = obj(data.get("crossfit"))
    performance = obj(crossfit.get("performance_report"))
    week = obj(obj(performance.get("window_summaries")).get("recent_7d"))
    advanced = obj(data.get("advanced"))
    hybrid = obj(daily.get("readiness_hybrid"))
    sleep = obj(extended.get("sleep_detail"))
    battery = obj(garmin.get("body_battery_today"))
    stress = obj(garmin.get("stress_today"))
    live = obj(obj(data.get("live_sensor_quality")).get("live_measurements"))
    sleep_gate = obj(data.get("morning_sleep"))

    warnings = []
    if quality.get("baseline_maturity") == "provisional":
        warnings.append("baseline_provisional")
    if heart_today.get("partial_day") is True:
        warnings.append("daytime_hr_partial")
    sleep_confirmed = (
        sleep_gate.get("state") == "confirmed_ready"
        and sleep_gate.get("evidence_valid") is True
        and current.get("date") == cycle_id[:10]
    )
    # A previous day's wellness row must never become a confirmed current-day reading.
    recovery_current_day = current.get("date") == cycle_id[:10]
    if not recovery_current_day:
        warnings.append("recovery_current_date_unverified")
    hr_today_valid = heart_today.get("date") == cycle_id[:10]
    if not hr_today_valid:
        warnings.append("heart_rate_today_date_unverified")
    if not sleep_confirmed:
        warnings.append("sleep_unconfirmed_or_pending")
    chart = performance.get("daily_chart_7d")
    chart_valid = isinstance(chart, list) and len(chart) == 7 and all(
        isinstance(p, dict) and isinstance(p.get("date"), str) and
        re.fullmatch(r"\d{4}-\d{2}-\d{2}", p["date"]) for p in chart)
    if not chart_valid:
        warnings.append("crossfit_chart_unavailable")
    warnings.append("chatgpt_delivery_unverified")

    lines = [
        "# Garmin Recovery V4.0 — Informe certificado", "",
        f"**Ciclo:** `{cycle_id}` · **Corte:** {safe(cert['slot_at'])}",
        f"**SHA-256 del snapshot:** `{cert['snapshot_sha256']}`", "",
        "**Modo:** vista V4.0 en paralelo; no sustituye los informes V3.8/V3.9 ni confirma su entrega a ChatGPT.", "",
        "## 1. Lectura rápida", "",
        "| Indicador | Valor | Contexto |", "|---|---:|---|",
        f"| Recuperación fisiológica (modelo local) | {fmt(recovery.get('score'), '/100', 0) if recovery.get('state') == 'assessed' and recovery_current_day else 'Pendiente'} | {safe(recovery.get('status'))}; confianza {safe(recovery.get('confidence'))} |",
        f"| Readiness híbrida | {fmt(hybrid.get('score'), '/100', 0) if recovery.get('state') == 'assessed' and recovery_current_day else 'Provisional (no evaluable)'} | No equivalente al modelo de recuperación |",
        f"| Calidad del registro | {fmt(quality.get('score'), '/100', 0)} | {safe(quality.get('baseline_maturity'))} |",
        f"| Contexto de turno | {safe(recovery.get('work_shift_context'))} | Registrar sueño matinal/fragmentado cuando proceda |",
        "", "Las puntuaciones corresponden a **modelos distintos**: no promediarlas ni interpretarlas como autorización médica o deportiva.", "",
        "## 2. Sueño y recuperación", "",
    ]
    if sleep_confirmed:
        lines += [
            f"- Sueño principal confirmado: **{fmt(current.get('sleep_hours'), ' h', 2)}**, puntuación **{fmt(current.get('sleep_score'), '/100', 0)}**.",
            f"- Ventana registrada: {safe(current.get('sleep_start_local'))} → {safe(current.get('sleep_end_local'))}.",
            f"- Fases estimadas Garmin: profundo {fmt(sleep.get('deep_minutes'), ' min', 0)}; REM {fmt(sleep.get('rem_minutes'), ' min', 0)}; ligero {fmt(sleep.get('light_minutes'), ' min', 0)}.",
            "- No se incorporan como sueño confirmado eventos Body Battery que se solapen o estén pendientes.",
        ]
    else:
        lines += [
            "**Sueño pendiente/no confirmado en este ciclo.** No se heredan horas ni HRV de otra fecha para emitir un juicio de recuperación.",
            "- Las métricas disponibles a continuación son descriptivas y no demuestran un despertar definitivo.",
        ]

    lines += ["", "### Comparación con la referencia personal de 28 días", "",
              "| Métrica | Actual | Mediana | Días válidos | Diferencia |",
              "|---|---:|---:|---:|---:|"]
    for label, key, unit, allow_pending in (
        ("HRV nocturna", "hrv_ms", " ms", False),
        ("Sueño", "sleep_hours", " h", False),
        ("Puntuación sueño", "sleep_score", "", False),
        ("FC en reposo", "resting_hr", " lpm", True),
        ("FC media nocturna", "night_hr", " lpm", False),
    ):
        ref = obj(baseline.get(key))
        n = ref.get("n")
        is_usable = type(n) is int and n >= 7 and number(ref.get("median"))
        is_current = (sleep_confirmed or allow_pending) and recovery_current_day and number(current.get(key))
        delta = fmt(current[key] - ref["median"], f"{unit}") if is_current and is_usable else "No evaluable"
        value = fmt(current.get(key), unit, 2 if key == "sleep_hours" else 1) if is_current else "Pendiente"
        lines.append(f"| {label} | {value} | {fmt(ref.get('median'), unit)} | {n if type(n) is int else 'ND'} | {delta} |")
    lines += ["", "Diferencias descriptivas; con pocas observaciones, la referencia es provisional. La clasificación de HRV del dispositivo puede seguir en fase de aprendizaje.", "",
              "## 3. FC, estrés y Body Battery", "",
              "| Métrica | Valor |", "|---|---:|",
              f"| FC en reposo | {fmt(heart_today.get('resting_hr') if hr_today_valid else None, ' lpm')} |",
              f"| FC diurna | {fmt(heart_today.get('daytime_avg_hr') if hr_today_valid else None, ' lpm')}{' (día parcial)' if hr_today_valid and heart_today.get('partial_day') else ''} |",
              f"| FC nocturna | {fmt(heart_today.get('nighttime_avg_hr') if hr_today_valid else None, ' lpm')} |",
              f"| Estrés Garmin promedio | {fmt(stress.get('avgStressLevel'), '/100', 0)} |",
              f"| Body Battery última lectura | {fmt(battery.get('latest'), '/100', 0)} |", "",
              "### Tendencia FC — ventanas de Garmin", "",
              "| Ventana | FC diurna | FC nocturna | Cobertura diurna/nocturna |", "|---|---:|---:|---:|"]
    for label, key in (("3 días", "3d"), ("7 días", "7d"), ("28 días", "28d")):
        row = obj(rolling.get(key))
        nd = row.get("daytime_days_present")
        nn = row.get("nighttime_days_present")
        lines.append(f"| {label} | {fmt(row.get('daytime_avg_hr'), ' lpm')} | {fmt(row.get('nighttime_avg_hr'), ' lpm')} | {fmt(nd, '', 0)} / {fmt(nn, '', 0)} |")
    lines += ["", "**Frescura de muestras:**", ""]
    for label, key in (("FC", "heart_rate_live"), ("Body Battery", "body_battery_live")):
        sample = obj(live.get(key))
        if sample.get("state") == "recent" and isinstance(sample.get("measured_at"), str):
            lines.append(f"- {label}: muestra reciente a las {safe(sample['measured_at'])}.")
        else:
            lines.append(f"- {label}: hora de medición reciente no confirmada; no equivale a una lectura en directo.")

    lines += ["", "## 4. Carga deportiva — 7 días", "",
              "| Indicador | Registro |", "|---|---:|",
              f"| Sesiones registradas | {fmt(week.get('sessions'), '', 0)} |",
              f"| Sesiones con RPE | {fmt(week.get('sessions_with_rpe'), '', 0)} |",
              f"| RPE medio | {fmt(week.get('mean_recorded_rpe'))} |",
              f"| Duración Garmin acumulada | {fmt(week.get('recorded_duration_minutes'), ' min')} |",
              f"| sRPE (duración registrada × RPE) | {fmt(week.get('srpe_from_recorded_duration'), ' UA')} |",
              f"| TRIMP (escala distinta) | {fmt(week.get('trimp_separate'))} |",
              f"| Volumen externo mínimo conocido | {fmt(week.get('minimum_recorded_external_volume_kg'), ' kg')} |",
              f"| Bloques de fuerza sin peso cuantificado | {fmt(week.get('strength_blocks_missing_quantified_weight'), '', 0)} |", "",
              "La duración Garmin no representa necesariamente la duración efectiva del WOD. El volumen externo es un mínimo; no comparar directamente máquinas, mancuernas y barras. No sumar sRPE, TRIMP y cargas de otras escalas.", ""]
    if chart_valid:
        lines += ["### Carga registrada por día", "", "| Fecha | Sesiones | RPE medio | sRPE |", "|---|---:|---:|---:|"]
        for p in chart:
            lines.append(f"| {p['date']} | {fmt(p.get('sessions'), '', 0)} | {fmt(p.get('mean_recorded_rpe'))} | {fmt(p.get('srpe_from_recorded_duration'))} |")
        lines.append("")
    else:
        lines += ["Gráfico semanal no disponible en el snapshot. No se reconstruye ni interpola.", ""]

    active = crossfit.get("activities_today")
    if isinstance(active, list) and active:
        lines += [f"**Actividades de hoy registradas:** {len(active)} (consultar sus ejercicios originales antes de valorar marcas personales).", ""]
    else:
        lines += ["**Actividades de hoy registradas:** ninguna en este snapshot; no implica necesariamente descanso.", ""]

    lines += ["## 5. Orientación de entrenamiento", ""]
    guidance = obj(recovery.get("training_guidance"))
    if recovery.get("state") == "assessed" and recovery.get("status") == "yellow":
        lines.append("**Precaución / moderación:** individualizar cargas por calentamiento, fatiga, dolor y RPE. No usar una puntuación como autorización para máximos.")
    elif recovery.get("state") != "assessed":
        lines.append("**Valoración pendiente:** falta evaluación confirmada; no inferir disponibilidad para cargas altas.")
    else:
        lines.append("La recomendación se interpreta con sensaciones, síntomas, entrenamiento reciente y técnica; no es una evaluación médica ni de preparación neuromuscular.")
    for rec in performance.get("recommendations", []) if isinstance(performance.get("recommendations"), list) else []:
        message = obj(rec).get("text")
        if isinstance(message, str) and message.strip():
            lines.append("- " + safe(message, 400))
    note = guidance.get("note")
    if isinstance(note, str) and note.strip():
        lines.append("- Nota de fiabilidad: " + safe(note, 400))

    lines += ["", "## 6. Calidad, límites y certificación", "",
              f"- Estado calidad: **{safe(quality.get('status'))}**; confianza: **{safe(quality.get('confidence'))}**.",
              f"- Históricos provisionales: **{'sí' if 'baseline_provisional' in warnings else 'no consta'}**.",
              f"- Incidencias de interpretación: **{', '.join(warnings)}**.",
              "- Fuente: únicamente snapshot del ciclo verificado por SHA-256 y procedencia; no se consultan datos en vivo.",
              "- Un SHA válido verifica la coincidencia con el snapshot registrado, no la exactitud clínica de las fuentes externas.",
              "- **Entrega en ChatGPT: no verificada.** Informe de tipo artefacto, no notificación.",
              "- Evoluciones no comparables (distintas variantes de WOD y pocos días históricos) no permiten demostrar mejoras físicas.", ""]
    meta = {
        "version": "4.0.0-preview",
        "cycle_id": cycle_id,
        "slot_at": cert["slot_at"],
        "snapshot_sha256": cert["snapshot_sha256"],
        "source": "verified_cycle_snapshot_only",
        "mode": "artifact_only_parallel_to_v39",
        "delivery": "unverified_no_chatgpt_receipt",
        "recovery_state": safe(recovery.get("state")),
        "recovery_confidence": safe(recovery.get("confidence")),
        "sleep_confirmed": sleep_confirmed,
        "chart_complete": chart_valid,
        "warning_codes": warnings,
    }
    return "\n".join(lines), meta


def _immutable_write(path, content):
    """Create-only atomic file: retries are idempotent; conflicts never overwrite."""
    path = Path(path)
    if path.parent.is_symlink() or path.is_symlink():
        raise SnapshotError("Symlink rejected")
    if path.exists():
        if not path.is_file() or path.read_bytes() != content:
            raise SnapshotError("Existing content differs; refusing overwrite")
        return "already_present"
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix=".pending-v40-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        try:
            os.link(temp, path)
            return "published_local"
        except FileExistsError:
            if path.is_symlink() or not path.is_file() or path.read_bytes() != content:
                raise SnapshotError("Concurrent conflict; refusing overwrite")
            return "already_present"
    finally:
        Path(temp).unlink(missing_ok=True)


def publish(ledger, cycle_id, outdir, write=False):
    markdown, metadata = render(ledger, cycle_id)
    markdown_bytes = (markdown.rstrip() + "\n").encode("utf-8")
    metadata = dict(metadata)
    metadata["report_sha256"] = hashlib.sha256(markdown_bytes).hexdigest()
    outdir = Path(outdir)
    name = f"{cycle_id}-{metadata['snapshot_sha256'][:16]}-v40"
    md = outdir / (name + ".md")
    manifest = outdir / (name + ".manifest.json")
    metadata["report_file"] = md.name
    metadata["manifest_file"] = manifest.name
    manifest_bytes = (json.dumps(metadata, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    if not write:
        return {**metadata, "state": "dry_run", "markdown": markdown}
    # Preflight both destinations before creating any file.
    for path, expected in ((md, markdown_bytes), (manifest, manifest_bytes)):
        if path.is_symlink() or path.parent.is_symlink() or (path.exists() and (not path.is_file() or path.read_bytes() != expected)):
            raise SnapshotError("Destination conflict; refusing overwrite")
    a = _immutable_write(md, markdown_bytes)
    b = _immutable_write(manifest, manifest_bytes)
    return {**metadata, "state": "already_present" if a == b == "already_present" else "published_local"}


def main(argv=None):
    p = argparse.ArgumentParser(description="Preview V4.0 report from verified cycle snapshots only")
    p.add_argument("--ledger", type=Path, default=Path("report_cycles.json"))
    p.add_argument("--cycle-id", help="Verified cycle ID; default is latest data_ready")
    p.add_argument("--outdir", type=Path, default=Path("v40_preview_reports"))
    p.add_argument("--write", action="store_true", help="Write immutable Markdown and manifest files")
    args = p.parse_args(argv)
    try:
        ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
        cid = args.cycle_id or latest_id(ledger)
        result = publish(ledger, cid, args.outdir, args.write)
    except (OSError, ValueError, TypeError) as exc:
        p.exit(2, f"V4.0 not reportable: {exc}\n")
    if args.write:
        print(json.dumps({k: v for k, v in result.items() if k != "markdown"}, ensure_ascii=False, sort_keys=True))
    else:
        print(result["markdown"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
