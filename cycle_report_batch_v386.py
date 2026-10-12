#!/usr/bin/env python3
"""V3.8.6: batch historical reports; invalid integrity remains quarantined."""
import argparse
import json
from pathlib import Path
from cycle_report_publisher_v386 import publish
from cycle_snapshot_report_v38 import SnapshotError


def run(ledger, outdir, cycle_id=None):
    if not isinstance(ledger, dict) or not isinstance(ledger.get('cycles'), list):
        raise SnapshotError('Invalid ledger')
    eligible = [r['cycle_id'] for r in ledger['cycles'] if isinstance(r, dict)
                and r.get('state') == 'data_ready' and isinstance(r.get('cycle_id'), str)]
    if len(eligible) != len(set(eligible)):
        raise SnapshotError('Duplicate eligible cycle IDs')
    if cycle_id is not None:
        if cycle_id not in eligible:
            raise SnapshotError('Requested cycle not eligible')
        eligible = [cycle_id]
    reports, rejected = [], []
    for cid in sorted(eligible):
        try:
            reports.append({'cycle_id': cid, **publish(ledger, cid, outdir, write=True)})
        except (SnapshotError, ValueError, TypeError, OSError) as exc:
            if cycle_id is not None:
                raise
            rejected.append({'cycle_id': cid, 'reason': ('legacy_without_snapshot' if next((r for r in ledger['cycles'] if isinstance(r, dict) and r.get('cycle_id') == cid and r.get('legacy_without_snapshot') and not isinstance(r.get('snapshot'), dict)), None) is not None else type(exc).__name__), 'detail': str(exc)[:200]})
    return {'version': '3.8.6', 'mode': 'artifact_only', 'delivery': 'unverified_no_receipt',
            'count': len(reports), 'rejected_count': len(rejected),
            'reports': reports, 'rejected': rejected}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--ledger', type=Path, default=Path('report_cycles.json'))
    p.add_argument('--outdir', type=Path, default=Path('certified_cycle_reports'))
    p.add_argument('--cycle-id')
    args = p.parse_args()
    result = run(json.loads(args.ledger.read_text(encoding='utf-8')), args.outdir, args.cycle_id)
    args.outdir.mkdir(parents=True, exist_ok=True)
    (args.outdir / 'manifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'count': result['count'], 'rejected_count': result['rejected_count'],
                      'mode': result['mode'], 'delivery': result['delivery']}))

if __name__ == '__main__':
    main()
