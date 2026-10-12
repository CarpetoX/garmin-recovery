#!/usr/bin/env python3
"""V3.8: read-only, reproducible cycle snapshot report (not a V3.6 regeneration).

Only data embedded in a verified ledger snapshot may appear in the report.
No live Garmin files, network, commits, or delivery assertions.
"""
import argparse
import hashlib
import json
from pathlib import Path

def digest(obj):
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()

class SnapshotError(ValueError):
    pass


def build(ledger, cycle_id):
    if not isinstance(ledger, dict) or not isinstance(ledger.get('cycles'), list):
        raise SnapshotError('Invalid cycle ledger')
    rows = [r for r in ledger['cycles'] if isinstance(r, dict) and r.get('cycle_id') == cycle_id]
    if len(rows) != 1:
        raise SnapshotError('Cycle missing or ambiguous')
    row = rows[0]
    snap = row.get('snapshot')
    if not isinstance(snap, dict) or digest(snap) != row.get('snapshot_sha256'):
        raise SnapshotError('Snapshot missing or SHA-256 mismatch')
    if row.get('state') != 'data_ready':
        raise SnapshotError('Cycle not data_ready')
    if row.get('source_generated_at') != snap.get('source_generated_at'):
        raise SnapshotError('Snapshot source provenance mismatch')
    if snap.get('date') != cycle_id[:10] or row.get('slot_at', '')[:10] != cycle_id[:10]:
        raise SnapshotError('Snapshot date mismatch')
    return {
        'version': '3.8.0', 'kind': 'certified_snapshot_descriptive_report',
        'cycle_id': cycle_id, 'slot_at': row['slot_at'],
        'snapshot_sha256': row['snapshot_sha256'],
        'source_generated_at': snap['source_generated_at'],
        'source': 'immutable_ledger_snapshot_only',
        'data': {k: snap.get(k) for k in (
            'recovery_assessment', 'daily', 'advanced', 'data_quality', 'crossfit',
            'garmin', 'morning_sleep', 'live_sensor_quality', 'physiological_report_status')
            if k in snap},
        'report_v36_link': 'not_claimed',
        'chatgpt_delivery': 'unverified_no_receipt',
        'limitations': [
            'Historical snapshot, not a live Garmin measurement.',
            'No reconstructed V3.6 report or invented RPE, loads or one-rep maxima.',
            'Snapshot integrity does not independently verify GitHub Actions conclusions.',
            'No ChatGPT delivery receipt is available.'
        ],
    }


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--ledger', type=Path, default=Path('report_cycles.json'))
    p.add_argument('--cycle-id', required=True)
    p.add_argument('--out', type=Path, help='Optional output; without this prints to stdout')
    a = p.parse_args(argv)
    try:
        report = build(json.loads(a.ledger.read_text(encoding='utf-8')), a.cycle_id)
    except (OSError, ValueError, TypeError) as e:
        p.exit(2, f'Not reportable: {e}\n')
    data = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    if a.out:
        a.out.write_text(data, encoding='utf-8')
    else:
        print(data, end='')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
