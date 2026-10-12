#!/usr/bin/env python3
"""V3.8.3: offline, fail-closed publisher of certified historical reports.

Dry-run by default. No network, GitHub writes, dispatches or delivery claims.
Publishing is atomic, content-addressed and never overwrites different content.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
from cycle_visual_report_v382 import make
from cycle_snapshot_report_v38 import SnapshotError


def prepare(ledger, cycle_id):
    report = make(ledger, cycle_id)
    rows = [r for r in ledger.get('cycles', []) if isinstance(r, dict) and r.get('cycle_id') == cycle_id]
    if len(rows) != 1:
        raise SnapshotError('Cycle not unique')
    digest = rows[0]['snapshot_sha256']
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise SnapshotError('Invalid digest')
    if not cycle_id or any(c not in '0123456789-' for c in cycle_id):
        raise SnapshotError('Unsafe cycle id')
    name = f'{cycle_id}-{digest[:16]}.md'
    return name, report.encode('utf-8')


def publish(ledger, cycle_id, outdir, write=False):
    name, content = prepare(ledger, cycle_id)
    destination = Path(outdir) / name
    if destination.is_symlink():
        raise SnapshotError('Refusing symlink destination')
    if destination.exists():
        if destination.read_bytes() != content:
            raise SnapshotError('Existing report differs: refusing overwrite')
        return {'state': 'already_present', 'path': str(destination), 'sha256': hashlib.sha256(content).hexdigest()}
    if not write:
        return {'state': 'dry_run', 'path': str(destination), 'sha256': hashlib.sha256(content).hexdigest()}
    directory = Path(outdir)
    directory.mkdir(parents=True, exist_ok=True)
    if destination.is_symlink():
        raise SnapshotError('Refusing symlink destination')
    fd, tmp = tempfile.mkstemp(prefix='.pending-', suffix='.md', dir=directory)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        # Exclusive creation: never replace an existing report, even under races.
        os.link(tmp, destination)
    except FileExistsError:
        if destination.is_symlink() or destination.read_bytes() != content:
            raise SnapshotError('Concurrent report differs: refusing overwrite')
    finally:
        Path(tmp).unlink(missing_ok=True)
    return {'state': 'published_local', 'path': str(destination), 'sha256': hashlib.sha256(content).hexdigest()}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--ledger', type=Path, default=Path('report_cycles.json'))
    p.add_argument('--cycle-id', required=True)
    p.add_argument('--outdir', type=Path, default=Path('certified_cycle_reports'))
    p.add_argument('--write', action='store_true', help='Explicit opt-in for local filesystem publication')
    args = p.parse_args()
    try:
        result = publish(json.loads(args.ledger.read_text(encoding='utf-8')), args.cycle_id, args.outdir, args.write)
    except (OSError, ValueError, TypeError) as exc:
        p.exit(2, f'Not published: {exc}\n')
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
