#!/usr/bin/env python3
"""V3.0: versioned, read-only contracts for exported Garmin Recovery JSON.

This module validates the produced shape and same-cycle RPE fingerprints, but
never rewrites, coerces or invents the underlying measurements. Its audit is
an additional diagnostic and does not replace existing quality checks.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _good_str(value):
    return isinstance(value, str) and bool(value.strip())


def audit(inputs):
    """Accept dict filename->JSON object or None; return structured diagnostics."""
    issues = []
    present = {}
    required = ('advanced_analytics.json', 'training_feedback.json', 'crossfit_insights.json')
    for name in required:
        data = inputs.get(name)
        present[name] = isinstance(data, dict)
        if not present[name]:
            issues.append({'code': 'source_unavailable_or_invalid', 'source': name})
            continue
        if not _good_str(data.get('generated_at')) and name != 'training_feedback.json':
            issues.append({'code': 'missing_generated_at', 'source': name})
    advanced = inputs.get('advanced_analytics.json') or {}
    feedback = inputs.get('training_feedback.json') or {}
    crossfit = inputs.get('crossfit_insights.json') or {}
    if all(present.values()) and isinstance(advanced, dict) and isinstance(feedback, dict) and isinstance(crossfit, dict):
        afp = advanced.get('rpe_feedback') or {}
        if not isinstance(afp, dict):
            afp = {}
        if crossfit.get('sheet_source') == 'cycle_snapshot':
            for key in ('source_rows_sha256', 'advanced_run_id'):
                v1 = afp.get(key)
                v2 = feedback.get(key)
                if not v1 or not v2 or str(v1) != str(v2):
                    issues.append({'code': 'cycle_fingerprint_mismatch', 'field': key})
            if crossfit.get('sheet_rows_loaded') != feedback.get('remote_rows_loaded'):
                issues.append({'code': 'rpe_row_count_mismatch'})
        elif crossfit.get('sheet_source') not in ('live_csv', None):
            issues.append({'code': 'unrecognized_rpe_source', 'value': str(crossfit.get('sheet_source'))[:80]})
        activities = crossfit.get('activities')
        if not isinstance(activities, list):
            issues.append({'code': 'invalid_activities_structure'})
        else:
            ids = []
            for activity in activities:
                if not isinstance(activity, dict) or not _good_str(str(activity.get('activity_id') or '')):
                    issues.append({'code': 'activity_id_missing_or_invalid'})
                    break
                ids.append(str(activity['activity_id']))
            if len(ids) != len(set(ids)):
                issues.append({'code': 'duplicate_activity_id'})
        # A direct source must be explicitly identified, never inferred by date.
        if not _good_str(crossfit.get('sheet_source')):
            issues.append({'code': 'missing_rpe_provenance'})
    status = 'ok' if not issues else ('unavailable' if all(i['code'] == 'source_unavailable_or_invalid' for i in issues) else 'attention')
    return {'schema_version': 1, 'version': '3.0', 'status': status,
            'source_presence': present, 'issues': issues,
            'rules': ['No coerced or estimated measurements',
                      'RPE cross-stage equality uses run ID and SHA-256, not dates',
                      'Diagnostic audit, not a ChatGPT delivery receipt']}


def read_inputs(directory):
    out = {}
    for name in ('advanced_analytics.json', 'training_feedback.json', 'crossfit_insights.json'):
        try:
            out[name] = json.loads((directory/name).read_text(encoding='utf-8'))
        except (OSError, ValueError):
            out[name] = None
    return out


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--directory', type=Path, default=Path('.'))
    p.add_argument('--out', type=Path, default=Path('schema_health_v30.json'))
    p.add_argument('--strict', action='store_true', help='CI use: exit nonzero on missing/inconsistent inputs')
    args = p.parse_args(argv)
    report = audit(read_inputs(args.directory))
    report['generated_at'] = datetime.now(timezone.utc).isoformat()
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'issues': len(report['issues'])}))
    if args.strict and report['status'] != 'ok':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
