#!/usr/bin/env python3
"""V3.9.2: independent enriched report batch; historical originals untouched."""
import argparse
import json
from pathlib import Path
from cycle_report_publisher_v392 import publish
from cycle_snapshot_report_v38 import SnapshotError


def run(ledger, outdir, cycle_id=None):
    if not isinstance(ledger, dict) or not isinstance(ledger.get('cycles'), list):
        raise SnapshotError('Invalid ledger')
    eligible = [row['cycle_id'] for row in ledger['cycles'] if isinstance(row, dict)
                and row.get('state') == 'data_ready' and isinstance(row.get('cycle_id'), str)]
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
            row = next((r for r in ledger['cycles'] if isinstance(r, dict) and r.get('cycle_id') == cid), {})
            reason = ('legacy_without_snapshot' if row.get('legacy_without_snapshot')
                      and not isinstance(row.get('snapshot'), dict) else type(exc).__name__)
            rejected.append({'cycle_id': cid, 'reason': reason, 'detail': str(exc)[:200]})
    return {'version': '3.9.2', 'mode': 'artifact_only', 'delivery': 'unverified_no_receipt',
            'count': len(reports), 'rejected_count': len(rejected),
            'reports': reports, 'rejected': rejected}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--ledger', type=Path, default=Path('report_cycles.json'))
    p.add_argument('--outdir', type=Path, default=Path('enriched_cycle_reports_v392'))
    p.add_argument('--cycle-id')
    a = p.parse_args()
    result = run(json.loads(a.ledger.read_text(encoding='utf-8')), a.outdir, a.cycle_id)
    a.outdir.mkdir(parents=True, exist_ok=True)
    (a.outdir / 'manifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'count': result['count'], 'rejected_count': result['rejected_count'],
                      'mode': result['mode'], 'delivery': result['delivery']}))


if __name__ == '__main__':
    main()
