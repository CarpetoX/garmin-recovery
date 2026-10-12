#!/usr/bin/env python3
"""V3.7.1: read-only afternoon publication eligibility; never sends messages.

Requires independent GitHub Actions evidence supplied as a JSON mapping of stage
names to {id,status,conclusion}. No GitHub calls, workflow dispatch or file writes.
"""
import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from report_cycle_guard_v37 import validate_certificate, CycleNotReady

TZ = ZoneInfo('Europe/Madrid')
STAGES = ('sync', 'heart', 'advanced', 'crossfit')


def digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                     separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def evaluate(cert, ledger, report_status, *, now, actions=None, source_data=None):
    """Fail closed; report_status describes a standalone CrossFit report, not a certificate."""
    result = {'state': 'not_eligible', 'cycle_id': None,
              'standalone_report': 'not_checked', 'reason': None,
              'chatgpt_delivery': 'unverified_no_receipt'}
    if now.tzinfo is None:
        raise ValueError('now must be timezone-aware')
    now = now.astimezone(TZ)
    cycle_id = now.strftime('%Y-%m-%d-1645')
    result['cycle_id'] = cycle_id
    status = report_status if isinstance(report_status, dict) else {}
    result['standalone_report'] = ('validated_independent' if status.get('state') == 'current_validated'
                                    and status.get('report_current') is True else 'not_current')
    try:
        gate = validate_certificate(cert, cycle_id=cycle_id, now=now, source_data=source_data)
        if not isinstance(actions, dict):
            raise CycleNotReady('Independent GitHub Actions evidence required')
        for stage in STAGES:
            record = actions.get(stage)
            if not isinstance(record, dict):
                raise CycleNotReady(f'No independent Actions result: {stage}')
            run_id = cert['chain'][stage]['id']
            if (type(record.get('id')) is not int or record['id'] != run_id
                    or record.get('status') != 'completed'
                    or record.get('conclusion') != 'success'):
                raise CycleNotReady(f'GitHub Actions run not verified successful: {stage}')
        cycles = ledger.get('cycles') if isinstance(ledger, dict) else None
        matches = [c for c in cycles if isinstance(c, dict) and c.get('cycle_id') == cycle_id] if isinstance(cycles, list) else []
        if len(matches) != 1:
            raise CycleNotReady('Missing or ambiguous immutable cycle snapshot')
        entry = matches[0]
        snap = entry.get('snapshot')
        if (entry.get('state') != 'data_ready' or not isinstance(snap, dict)
                or digest(snap) != entry.get('snapshot_sha256')):
            raise CycleNotReady('Immutable snapshot missing or SHA-256 mismatch')
        if entry.get('sync_run_id') != gate['sync_run_id'] or entry.get('crossfit_run_id') != cert['chain']['crossfit']['id']:
            raise CycleNotReady('Snapshot run IDs do not match certificate')
        if entry.get('source_generated_at') != cert.get('source_generated_at'):
            raise CycleNotReady('Snapshot source timestamps do not match certificate')
        # Optional V3.6 report is never silently treated as belonging to this cycle.
        report_matches = (result['standalone_report'] == 'validated_independent'
                          and status.get('cycle_certificate') == 'same_certified_cycle'
                          and status.get('github_run_id') == cert['chain']['crossfit']['id']
                          and status.get('source_generated_at') == cert['source_generated_at']['crossfit_insights.json'])
        result.update(state='eligible_certified_snapshot', reason=None,
                      sync_run_id=gate['sync_run_id'],
                      report_v36_link='same_cycle' if report_matches else 'independent_not_certified',
                      snapshot_verified=True)
    except (CycleNotReady, KeyError, TypeError, ValueError) as exc:
        result['reason'] = str(exc)[:200]
    return result


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path('.'))
    p.add_argument('--actions-evidence', type=Path, required=True,
                   help='Independent verified GitHub Actions results, stage-keyed JSON')
    p.add_argument('--now', help='Timezone-aware ISO timestamp (default current clock)')
    a = p.parse_args(argv)
    now = datetime.fromisoformat(a.now) if a.now else datetime.now(TZ)
    try:
        result = evaluate(load(a.root/'report_ready.json'), load(a.root/'report_cycles.json'),
                          load(a.root/'crossfit_report_status_v361.json'), now=now,
                          actions=load(a.actions_evidence))
    except (OSError, ValueError, TypeError) as exc:
        result = {'state': 'not_eligible', 'reason': str(exc)[:200],
                  'chatgpt_delivery': 'unverified_no_receipt'}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['state'] == 'eligible_certified_snapshot' else 2


if __name__ == '__main__':
    raise SystemExit(main())
