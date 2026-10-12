import copy
import tempfile
import unittest
from pathlib import Path
from cycle_snapshot_report_v38 import digest, SnapshotError
from cycle_report_publisher_v383 import publish

CID = '2026-10-12-1645'

def ledger():
    snap = {
        'date': '2026-10-12', 'source_generated_at': {'daily_summary.json': '2026-10-12T17:00:00+02:00'},
        'recovery_assessment': {'status': 'yellow', 'current': {'hrv_ms': 66}, 'baseline_28d': {}},
        'crossfit': {'performance_report': {'daily_chart_7d': [{'date': f'2026-10-{d:02}', 'srpe_from_recorded_duration': 0} for d in range(6, 13)]}},
    }
    return {'cycles': [{'cycle_id': CID, 'state': 'data_ready', 'slot_at': '2026-10-12T16:45:00+02:00',
                        'source_generated_at': snap['source_generated_at'], 'snapshot': snap, 'snapshot_sha256': digest(snap)}]}

class PublisherTests(unittest.TestCase):
    def test_dry_run_no_write(self):
        with tempfile.TemporaryDirectory() as root:
            r = publish(ledger(), CID, Path(root)/'reports')
            self.assertEqual(r['state'], 'dry_run')
            self.assertFalse(Path(r['path']).exists())

    def test_atomic_write_idempotent(self):
        with tempfile.TemporaryDirectory() as root:
            first = publish(ledger(), CID, Path(root), True)
            second = publish(ledger(), CID, Path(root), True)
            self.assertEqual(first['state'], 'published_local')
            self.assertEqual(second['state'], 'already_present')
            self.assertEqual(first['sha256'], second['sha256'])

    def test_existing_different_content_not_overwritten(self):
        with tempfile.TemporaryDirectory() as root:
            first = publish(ledger(), CID, Path(root), True)
            Path(first['path']).write_text('do not overwrite', encoding='utf-8')
            with self.assertRaises(SnapshotError):
                publish(ledger(), CID, Path(root), True)
            self.assertEqual(Path(first['path']).read_text(), 'do not overwrite')

    def test_invalid_digest_fails_closed(self):
        x = ledger()
        x['cycles'][0]['snapshot']['recovery_assessment']['current']['hrv_ms'] = 999
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(SnapshotError):
                publish(x, CID, root, True)

    def test_unsafe_id_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(SnapshotError):
                publish(ledger(), '../unsafe', root, True)

if __name__ == '__main__':
    unittest.main()
