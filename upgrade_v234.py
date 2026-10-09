#!/usr/bin/env python3
"""One-shot migration: Garmin Recovery V2.3.3 -> V2.3.4 robustness update."""
from pathlib import Path

ROOT = Path(".")
changed = []

def read(path):
    return (ROOT / path).read_text(encoding="utf-8")

def write(path, text):
    (ROOT / path).write_text(text, encoding="utf-8")
    changed.append(path)

def replace_once(text, old, new, label):
    if old not in text:
        raise RuntimeError(f"V2.3.4 patch anchor missing: {label}")
    return text.replace(old, new, 1)

p = "report_delivery_gate.py"
s = read(p)
s = replace_once(
    s,
    '"""Garmin Recovery V2.3.3: certificate for a completed cross-workflow report cycle.',
    '"""Garmin Recovery V2.3.4: certificate for a completed cross-workflow report cycle.',
    "gate doc version",
)
s = replace_once(s, "import json\nimport os", "import hashlib\nimport json\nimport os", "gate hashlib import")
s = s.replace("'User-Agent': 'Garmin-Report-Delivery-Gate/2.3.2'", "'User-Agent': 'Garmin-Report-Delivery-Gate/2.3.4'")
s = s.replace("'gate_version': '2.3.3'", "'gate_version': '2.3.4'")

anchor = "\n\n\ndef append_ready_cycle(cert, path=Path('report_cycles.json'), max_entries=120):"
if anchor not in s:
    raise RuntimeError("V2.3.4 patch anchor missing: append_ready_cycle")

snapshot_code = '\ndef _read_json(name, default):\n    try:\n        return json.loads(Path(name).read_text(encoding=\'utf-8\'))\n    except (OSError, ValueError, TypeError):\n        return default\n\n\ndef _today_row(obj, day):\n    if not isinstance(obj, dict):\n        return {}\n    days = obj.get(\'days\')\n    if isinstance(days, dict) and isinstance(days.get(day), dict):\n        return days[day]\n    return {}\n\n\ndef _last_body_battery(row):\n    values = row.get(\'bodyBatteryValuesArray\') if isinstance(row, dict) else None\n    if not isinstance(values, list):\n        return None\n    valid = [\n        x for x in values\n        if isinstance(x, list)\n        and len(x) >= 2\n        and isinstance(x[1], (int, float))\n    ]\n    return valid[-1][1] if valid else None\n\n\ndef compact_cycle_snapshot(cert):\n    """Freeze the report inputs used by this cycle."""\n    day = str(cert.get(\'cycle_id\') or \'\')[:10]\n    daily = _read_json(\'daily_summary.json\', {})\n    recovery = _read_json(\'recovery_assessment.json\', {})\n    advanced = _read_json(\'advanced_analytics.json\', {})\n    quality = _read_json(\'data_quality.json\', {})\n    crossfit = _read_json(\'crossfit_insights.json\', {})\n    status = _read_json(\'garmin_status.json\', {})\n    heart = _read_json(\'garmin_heart_rate.json\', {})\n    stress = _today_row(_read_json(\'garmin_stress.json\', {}), day)\n    battery = _today_row(_read_json(\'garmin_body_battery.json\', {}), day)\n    extended = _today_row(_read_json(\'garmin_extended.json\', {}), day)\n    hr_day = _today_row(heart, day)\n\n    crossfit_day = []\n    for row in crossfit.get(\'activities\', []) if isinstance(crossfit, dict) else []:\n        if isinstance(row, dict) and str(row.get(\'date\') or \'\') == day:\n            crossfit_day.append(row)\n\n    rec_v23 = recovery.get(\'v23\') if isinstance(recovery.get(\'v23\'), dict) else {}\n    snapshot = {\n        \'snapshot_version\': \'2.3.4\',\n        \'date\': day,\n        \'source_generated_at\': cert.get(\'source_generated_at\'),\n        \'measurement_provenance\': cert.get(\'measurement_provenance\'),\n        \'recovery_assessment\': {\n            \'generated_at\': recovery.get(\'generated_at\'),\n            \'state\': recovery.get(\'state\'),\n            \'status\': recovery.get(\'status\'),\n            \'score\': recovery.get(\'score\'),\n            \'confidence\': recovery.get(\'confidence\'),\n            \'reason\': recovery.get(\'reason\'),\n            \'current\': recovery.get(\'current\'),\n            \'baseline_28d\': recovery.get(\'baseline_28d\'),\n            \'metrics_used\': recovery.get(\'metrics_used\'),\n            \'warnings\': recovery.get(\'warnings\'),\n            \'recommendation\': recovery.get(\'recommendation\'),\n            \'work_shift_context\': recovery.get(\'work_shift_context\'),\n            \'sleep_integrity\': rec_v23.get(\'sleep_integrity\'),\n            \'reason_codes\': rec_v23.get(\'reason_codes\'),\n            \'training_guidance\': rec_v23.get(\'training_guidance\'),\n        },\n        \'daily\': {\n            \'generated_at\': daily.get(\'generated_at\'),\n            \'recovery_today\': daily.get(\'recovery_today\'),\n            \'training_today\': daily.get(\'training_today\'),\n            \'readiness_model\': daily.get(\'readiness_model\'),\n            \'readiness_hybrid\': daily.get(\'readiness_hybrid\'),\n        },\n        \'advanced\': {\n            \'generated_at\': advanced.get(\'generated_at\'),\n            \'readiness_hybrid\': advanced.get(\'readiness_hybrid\'),\n            \'personal_recovery_index\': advanced.get(\'personal_recovery_index\'),\n            \'convergence_alert\': advanced.get(\'convergence_alert\'),\n            \'weekly_load\': advanced.get(\'weekly_load\'),\n            \'heart_rate_recovery\': advanced.get(\'heart_rate_recovery\'),\n            \'recovery_data_coverage\': advanced.get(\'recovery_data_coverage\'),\n            \'recovery_fused_baseline_28d\': advanced.get(\'recovery_fused_baseline_28d\'),\n            \'rpe_feedback\': advanced.get(\'rpe_feedback\'),\n        },\n        \'data_quality\': quality,\n        \'crossfit\': {\n            \'generated_at\': crossfit.get(\'generated_at\'),\n            \'sheet_source\': crossfit.get(\'sheet_source\'),\n            \'sheet_error\': crossfit.get(\'sheet_error\'),\n            \'sheet_rows_loaded\': crossfit.get(\'sheet_rows_loaded\'),\n            \'sheet_latest_date\': crossfit.get(\'sheet_latest_date\'),\n            \'data_quality\': crossfit.get(\'data_quality\'),\n            \'weekly_report\': crossfit.get(\'weekly_report\'),\n            \'activities_today\': crossfit_day,\n        },\n        \'garmin\': {\n            \'status\': {\n                \'generated_at\': status.get(\'generated_at\'),\n                \'status\': status.get(\'status\'),\n                \'error\': status.get(\'error\'),\n                \'activity_metrics_available\': status.get(\'activity_metrics_available\'),\n                \'activity_metrics_error\': status.get(\'activity_metrics_error\'),\n            },\n            \'heart_rate_today\': hr_day,\n            \'heart_rate_rolling\': heart.get(\'rolling\') if isinstance(heart, dict) else None,\n            \'stress_today\': {\n                \'avgStressLevel\': stress.get(\'avgStressLevel\'),\n                \'maxStressLevel\': stress.get(\'maxStressLevel\'),\n                \'endTimestampLocal\': stress.get(\'endTimestampLocal\'),\n            },\n            \'body_battery_today\': {\n                \'charged\': battery.get(\'charged\'),\n                \'drained\': battery.get(\'drained\'),\n                \'latest\': _last_body_battery(battery),\n                \'endTimestampLocal\': battery.get(\'endTimestampLocal\'),\n            },\n            \'extended_today\': {\n                \'training_readiness\': extended.get(\'training_readiness\'),\n                \'recovery_time\': extended.get(\'recovery_time\'),\n                \'hrv_status\': extended.get(\'hrv_status\'),\n                \'sleep_detail\': extended.get(\'sleep_detail\'),\n                \'four_week_load_balance\': extended.get(\'four_week_load_balance\'),\n                \'activity_metrics\': extended.get(\'activity_metrics\'),\n            },\n        },\n    }\n    encoded = json.dumps(\n        snapshot,\n        ensure_ascii=False,\n        sort_keys=True,\n        separators=(\',\', \':\'),\n    ).encode(\'utf-8\')\n    return snapshot, hashlib.sha256(encoded).hexdigest()\n'
s = s.replace(anchor, "\n\n" + snapshot_code.strip("\n") + anchor, 1)

old_entry = """    items.append({
        'cycle_id': cycle_id, 'ready_at': cert['verified_at'],
        'slot_at': cert['slot_at'], 'target_report_at': cert['target_report_at'],
        'sync_run_id': cert['chain']['sync']['id'],
        'crossfit_run_id': cert['chain']['crossfit']['id'],
        'state': 'data_ready',
        'notification_delivery': 'unverified',
        'notice': 'No ChatGPT delivery acknowledgment is available to GitHub Actions.'
    })"""
new_entry = """    snapshot, snapshot_sha256 = compact_cycle_snapshot(cert)
    items.append({
        'cycle_id': cycle_id, 'ready_at': cert['verified_at'],
        'slot_at': cert['slot_at'], 'target_report_at': cert['target_report_at'],
        'sync_run_id': cert['chain']['sync']['id'],
        'crossfit_run_id': cert['chain']['crossfit']['id'],
        'chain': cert.get('chain'),
        'source_generated_at': cert.get('source_generated_at'),
        'measurement_provenance': cert.get('measurement_provenance'),
        'recovery_state': cert.get('recovery_state'),
        'recovery_confidence': cert.get('recovery_confidence'),
        'snapshot': snapshot,
        'snapshot_sha256': snapshot_sha256,
        'state': 'data_ready',
        'notification_delivery': 'unverified',
        'notice': 'No ChatGPT delivery acknowledgment is available to GitHub Actions.'
    })"""
s = replace_once(s, old_entry, new_entry, "cycle snapshot entry")
s = replace_once(
    s,
    "'schema_version': 1,\n        'purpose': 'Historical data-readiness ledger",
    "'schema_version': 2,\n        'ledger_version': '2.3.4',\n        'purpose': 'Historical data-readiness ledger",
    "report_cycles schema",
)
write(p, s)

p = "monitor_v231.py"
s = read(p)
s = replace_once(s, '"""Garmin V2.3.3 monitor:', '"""Garmin V2.3.4 monitor:', "monitor doc version")
s = replace_once(s, "def due_slots(now, lookback_hours=28, grace_minutes=120):",
                 "def due_slots(now, lookback_hours=28, grace_minutes=150):", "monitor due grace")
s = replace_once(s, "def audit_slots(now, runs, lookback_hours=28, grace_minutes=120):",
                 "def audit_slots(now, runs, lookback_hours=28, grace_minutes=150):", "monitor audit grace")
s = replace_once(s, "'schedule_version': 'three_syncs_v2',",
                 "'schedule_version': 'three_syncs_v234',", "monitor schedule version")
s = s.replace("print('OK: 6 tests of V2.3.3 schedule distinction')",
              "print('OK: 6 tests of V2.3.4 schedule distinction')", 1)
write(p, s)

p = "recovery_reliability.py"
s = read(p)
old = """    adv['recovery_data_coverage'] = coverage
    daily['recovery_data_coverage'] = coverage
    weekly['recovery_data_coverage'] = coverage"""
new = """    adv['recovery_data_coverage'] = coverage
    fused_baseline = assessment.get('baseline_28d', {})
    baseline_policy = {
        'version': '2.3.4',
        'canonical_for_recovery_reports': 'recovery_assessment.baseline_28d',
        'source': 'fused Garmin timelines + Intervals fallback',
        'excludes_current_day': True,
        'scoring_changed': False,
        'note': ('Advanced convergence_alert keeps its existing independently '
                 'validated record set; reports should use the fused baseline '
                 'for recovery reference values and sample counts.')
    }
    adv['recovery_fused_baseline_28d'] = fused_baseline
    adv['recovery_baseline_policy'] = baseline_policy
    quality['recovery_fused_baseline_28d'] = fused_baseline
    quality['recovery_baseline_policy'] = baseline_policy
    daily['recovery_fused_baseline_28d'] = fused_baseline
    daily['recovery_baseline_policy'] = baseline_policy
    weekly['recovery_fused_baseline_28d'] = fused_baseline
    weekly['recovery_baseline_policy'] = baseline_policy
    daily['recovery_data_coverage'] = coverage
    weekly['recovery_data_coverage'] = coverage"""
s = replace_once(s, old, new, "canonical fused baseline")
write(p, s)

p = ".github/workflows/sync.yml"
s = read(p)
old = """      - name: Guardar datos de Intervals
        run: |
          git config user.name "Garmin Recovery Bot"
          git config user.email "actions@github.com"

          git add recovery.csv wellness.json activities.csv activities.json daily_summary.json weekly_summary.json
          git diff --cached --quiet || git commit -m "Actualizar recuperación y análisis profesional"
          git push"""
new = """      - name: Guardar datos de Intervals con reintentos
        shell: bash
        run: |
          set -euo pipefail
          git config user.name "Garmin Recovery Bot"
          git config user.email "actions@github.com"

          git add recovery.csv wellness.json activities.csv activities.json daily_summary.json weekly_summary.json
          if git diff --cached --quiet; then
            echo "Sin cambios de Intervals que publicar."
            exit 0
          fi
          git commit -m "Actualizar recuperación y análisis profesional"

          for attempt in 1 2 3 4 5; do
            if ! git pull --rebase origin main; then
              git rebase --abort || true
              exit 1
            fi
            if git push origin HEAD:main; then
              exit 0
            fi
            sleep $((attempt * 3))
          done
          exit 1"""
s = replace_once(s, old, new, "sync resilient push")
write(p, s)

p = ".github/workflows/advanced-analytics-rpe.yml"
s = read(p)
old = """      - name: Guardar analítica avanzada
        run: |
          git config user.name "Garmin Recovery Bot"
          git config user.email "actions@github.com"

          git add advanced_analytics.json data_quality.json activity_hr_recovery.json
          git add daily_summary.json weekly_summary.json recovery_assessment.json
          [ -f training_feedback.json ] && git add training_feedback.json || true
          [ -f day_context.json ] && git add day_context.json || true

          git diff --cached --quiet || git commit -m "Actualizar analítica, RPE y fiabilidad de recuperación"
          git push"""
new = """      - name: Guardar analítica avanzada con reintentos
        shell: bash
        run: |
          set -euo pipefail
          git config user.name "Garmin Recovery Bot"
          git config user.email "actions@github.com"

          git add advanced_analytics.json data_quality.json activity_hr_recovery.json
          git add daily_summary.json weekly_summary.json recovery_assessment.json
          [ -f training_feedback.json ] && git add training_feedback.json || true
          [ -f day_context.json ] && git add day_context.json || true

          if git diff --cached --quiet; then
            echo "Sin cambios de analítica que publicar."
            exit 0
          fi
          git commit -m "Actualizar analítica, RPE y fiabilidad de recuperación"

          for attempt in 1 2 3 4 5; do
            if ! git pull --rebase origin main; then
              git rebase --abort || true
              exit 1
            fi
            if git push origin HEAD:main; then
              exit 0
            fi
            sleep $((attempt * 3))
          done
          exit 1"""
s = replace_once(s, old, new, "advanced resilient push")
write(p, s)

print("V2.3.4 patch applied to:", ", ".join(changed))
