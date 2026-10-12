import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from cycle_report_batch_v392 import run
from cycle_report_publisher_v392 import publish
from cycle_snapshot_report_v38 import SnapshotError


class EnrichedPublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = json.loads(Path('report_cycles.json').read_text(encoding='utf-8'))
        cls.cid = '2026-10-12-1645'

    def test_atomic_idempotent_distinct_name(self):
        with TemporaryDirectory() as d:
            a = publish(self.ledger, self.cid, d, write=True)
            b = publish(self.ledger, self.cid, d, write=True)
            self.assertEqual(a['state'], 'published_local')
            self.assertEqual(b['state'], 'already_present')
            self.assertEqual(a['sha256'], b['sha256'])
            self.assertTrue(a['path'].endswith('-v392.md'))
            self.assertIn('Interpretación técnica', Path(a['path']).read_text())
            self.assertFalse(any(Path(d).glob('*-v386.md')))

    def test_conflict_never_overwrites(self):
        with TemporaryDirectory() as d:
            a = publish(self.ledger, self.cid, d, write=True)
            Path(a['path']).write_text('modified', encoding='utf-8')
            with self.assertRaises(SnapshotError):
                publish(self.ledger, self.cid, d, write=True)
            self.assertEqual(Path(a['path']).read_text(), 'modified')

    def test_dry_run_no_files(self):
        with TemporaryDirectory() as d:
            a = publish(self.ledger, self.cid, d, write=False)
            self.assertEqual(a['state'], 'dry_run')
            self.assertFalse(Path(a['path']).exists())

    def test_batch_and_legacy_quarantine(self):
        with TemporaryDirectory() as d:
            result = run(self.ledger, d)
            self.assertEqual(result['count'], 10)
            self.assertEqual(result['rejected_count'], 1)
            self.assertEqual(result['rejected'][0]['reason'], 'legacy_without_snapshot')
            self.assertEqual(sum(x['completeness'] == 'complete' for x in result['reports']), 5)

    def test_bad_integrity_rejected(self):
        with TemporaryDirectory() as d:
            with self.assertRaises(SnapshotError):
                publish({'cycles': []}, self.cid, d, write=True)


if __name__ == '__main__':
    unittest.main()
