#!/usr/bin/env python3
"""V3.8.6: content-addressed, atomic, no-overwrite offline report publisher."""
import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from cycle_report_compat_v386 import render
from cycle_snapshot_report_v38 import build, SnapshotError


def publish(ledger, cycle_id, outdir, write=False):
    report, completeness = render(ledger, cycle_id)
    digest = build(ledger, cycle_id)['snapshot_sha256']
    data = report.encode('utf-8')
    destination = Path(outdir) / f'{cycle_id}-{digest[:16]}-v386.md'
    if destination.is_symlink():
        raise SnapshotError('Symlink destination rejected')
    if destination.exists():
        if destination.read_bytes() != data:
            raise SnapshotError('Existing report differs; refusing overwrite')
        state = 'already_present'
    elif not write:
        state = 'dry_run'
    else:
        directory = Path(outdir)
        if directory.is_symlink():
            raise SnapshotError('Symlink directory rejected')
        directory.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=directory, prefix='.pending-', suffix='.md')
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(tmp, destination)
            except FileExistsError:
                if destination.is_symlink() or destination.read_bytes() != data:
                    raise SnapshotError('Concurrent report differs; refusing overwrite')
                state = 'already_present'
            else:
                state = 'published_local'
        finally:
            Path(tmp).unlink(missing_ok=True)
    return {'state': state, 'completeness': completeness,
            'path': str(destination), 'sha256': hashlib.sha256(data).hexdigest()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ledger', type=Path, default=Path('report_cycles.json'))
    parser.add_argument('--cycle-id', required=True)
    parser.add_argument('--outdir', type=Path, default=Path('certified_cycle_reports'))
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    result = publish(json.loads(args.ledger.read_text(encoding='utf-8')),
                     args.cycle_id, args.outdir, args.write)
    print(json.dumps(result, ensure_ascii=False))

if __name__ == '__main__':
    main()
