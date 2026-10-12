"""V3.8.5 regression tests against the existing certified historical ledger."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from cycle_report_batch_v385 import run
from cycle_report_compat_v385 import render
from cycle_report_publisher_v385 import publish
from cycle_snapshot_report_v38 import SnapshotError

LEDGER = Path(__file__).with_name('report_cycles.json')

class HistoricalCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = json.loads(LEDGER.read_text(encoding='utf-8'))

    def test_legacy_chart_missing_is_partial(self):
        report, status = render(self.ledger, '2026-10-10-0830')
        self.assertEqual(status, 'partial_missing_crossfit_chart')
        self.assertIn('no disponible', report)
        self.assertNotIn('█', report)

    def test_post_sleep_identifier(self):
        report, status = render(self.ledger, '2026-10-11-0830-post-sleep')
        self.assertIn('2026-10-11-0830-post-sleep', report)
        self.assertIn(status, ('complete', 'partial_missing_crossfit_chart'))

    def test_invalid_digest_remains_rejected(self):
        with self.assertRaises(SnapshotError):
            render(self.ledger, '2026-10-09-1645')

    def test_complete_cycle_unchanged(self):
        report, status = render(self.ledger, '2026-10-12-1645')
        self.assertEqual(status, 'complete')
        self.assertIn('1457.7', report)

    def test_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = publish(self.ledger, '2026-10-11-0830-post-sleep', tmp, True)
            b = publish(self.ledger, '2026-10-11-0830-post-sleep', tmp, True)
            self.assertEqual(a['state'], 'published_local')
            self.assertEqual(b['state'], 'already_present')
            self.assertEqual(len(list(Path(tmp).glob('*.md'))), 1)

    def test_batch_six_recovered_one_quarantined(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run(self.ledger, tmp)
            self.assertEqual(result['count'], 10)
            self.assertEqual(result['rejected_count'], 1)
            self.assertEqual(result['rejected'][0]['cycle_id'], '2026-10-09-1645')

    def test_no_path_traversal(self):
        with self.assertRaises(SnapshotError):
            render(self.ledger, '../../2026-10-12-1645')

    def test_tamper_is_not_accepted(self):
        altered = copy.deepcopy(self.ledger)
        row = next(x for x in altered['cycles'] if x['cycle_id'] == '2026-10-12-1645')
        row['snapshot']['recovery_assessment']['current']['hrv_ms'] = 999
        with self.assertRaises(SnapshotError):
            render(altered, '2026-10-12-1645')

if __name__ == '__main__':
    unittest.main()
