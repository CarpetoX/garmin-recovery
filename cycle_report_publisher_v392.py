#!/usr/bin/env python3
"""V3.9.2: separate, immutable, content-addressed enriched Markdown publisher."""
import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

from cycle_report_enriched_v391 import render
from cycle_snapshot_report_v38 import build, SnapshotError


def publish(ledger, cycle_id, outdir, write=False):
    report, completeness = render(ledger, cycle_id)
    digest = build(ledger, cycle_id)['snapshot_sha256']
    data = report.encode('utf-8')
    directory = Path(outdir)
    destination = directory / f'{cycle_id}-{digest[:16]}-v392.md'
    if directory.is_symlink() or destination.is_symlink():
        raise SnapshotError('Symlink path rejected')
    if destination.exists():
        if not destination.is_file() or destination.read_bytes() != data:
            raise SnapshotError('Existing enriched report differs; refusing overwrite')
        state = 'already_present'
    elif not write:
        state = 'dry_run'
    else:
        directory.mkdir(parents=True, exist_ok=True)
        if directory.is_symlink():
            raise SnapshotError('Symlink directory rejected')
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
                    raise SnapshotError('Concurrent enriched report differs; refusing overwrite')
                state = 'already_present'
            else:
                state = 'published_local'
        finally:
            Path(tmp).unlink(missing_ok=True)
    return {'state': state, 'completeness': completeness, 'path': str(destination),
            'sha256': hashlib.sha256(data).hexdigest(), 'snapshot_sha256': digest,
            'format_version': '3.9.2'}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--ledger', type=Path, default=Path('report_cycles.json'))
    p.add_argument('--cycle-id', required=True)
    p.add_argument('--outdir', type=Path, default=Path('enriched_cycle_reports_v392'))
    p.add_argument('--write', action='store_true')
    a = p.parse_args()
    print(json.dumps(publish(json.loads(a.ledger.read_text(encoding='utf-8')),
                             a.cycle_id, a.outdir, a.write), ensure_ascii=False))


if __name__ == '__main__':
    main()
