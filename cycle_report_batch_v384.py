#!/usr/bin/env python3
"""V3.8.4: generate certified cycle reports into a local artifact directory.

No network, live Garmin files, repository commits, or ChatGPT delivery claims.
"""
import argparse
import json
from pathlib import Path
from cycle_report_publisher_v383 import publish
from cycle_snapshot_report_v38 import SnapshotError


def run(ledger, outdir, cycle_id=None):
    if not isinstance(ledger, dict) or not isinstance(ledger.get('cycles'), list):
        raise SnapshotError('Invalid ledger')
    rows = ledger['cycles']
    eligible = [r['cycle_id'] for r in rows if isinstance(r, dict) and r.get('state') == 'data_ready' and isinstance(r.get('cycle_id'), str)]
    if len(eligible) != len(set(eligible)):
        raise SnapshotError('Duplicate eligible cycle IDs')
    if cycle_id:
        if cycle_id not in eligible:
            raise SnapshotError('Requested cycle not eligible')
        eligible = [cycle_id]
    eligible.sort()
    results = []
    for cid in eligible:
        results.append({'cycle_id': cid, **publish(ledger, cid, outdir, write=True)})
    return {'version': '3.8.4', 'mode': 'artifact_only', 'delivery': 'unverified_no_receipt', 'count': len(results), 'reports': results}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--ledger', type=Path, default=Path('report_cycles.json'))
    p.add_argument('--outdir', type=Path, default=Path('certified_cycle_reports'))
    p.add_argument('--cycle-id')
    args = p.parse_args()
    ledger = json.loads(args.ledger.read_text(encoding='utf-8'))
    result = run(ledger, args.outdir, args.cycle_id)
    args.outdir.mkdir(parents=True, exist_ok=True)
    (args.outdir / 'manifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'count': result['count'], 'mode': result['mode'], 'delivery': result['delivery']}))


if __name__ == '__main__':
    main()
