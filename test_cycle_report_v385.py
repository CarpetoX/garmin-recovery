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
LEGACY_CYCLE = '2026-10-09-1645'


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
            render(self.ledger, LEGACY_CYCLE)

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

    def test_batch_recovers_all_certified_and_quarantines_legacy(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run(self.ledger, tmp)
            eligible = {
                row['cycle_id']
                for row in self.ledger['cycles']
                if isinstance(row, dict)
                and row.get('state') == 'data_ready'
                and isinstance(row.get('cycle_id'), str)
            }
            self.assertIn(LEGACY_CYCLE, eligible)
            self.assertGreaterEqual(len(eligible), 11)  # Prevent unnoticed historical loss.
            self.assertEqual(result['count'], len(eligible) - 1)
            self.assertEqual(result['count'], len(result['reports']))
            self.assertEqual(result['rejected_count'], 1)
            self.assertEqual(result['rejected'][0]['cycle_id'], LEGACY_CYCLE)
            self.assertEqual(
                {item['cycle_id'] for item in result['reports']},
                eligible - {LEGACY_CYCLE},
            )

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
