import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from cycle_report_batch_v392 import run
from cycle_report_publisher_v392 import publish
from cycle_snapshot_report_v38 import SnapshotError

LEGACY_CYCLE = '2026-10-09-1645'


def expected_completeness(row):
    snapshot = row['snapshot']
    performance = snapshot.get('crossfit', {}).get('performance_report', {})
    chart = performance.get('daily_chart_7d')
    valid = (isinstance(chart, list) and len(chart) == 7 and all(
        isinstance(point, dict)
        and isinstance(point.get('date'), str)
        and '\n' not in point['date']
        and '\r' not in point['date']
        for point in chart
    ))
    return 'complete' if valid else 'partial_missing_crossfit_chart'


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
            eligible = {
                row['cycle_id']: row
                for row in self.ledger['cycles']
                if isinstance(row, dict)
                and row.get('state') == 'data_ready'
                and isinstance(row.get('cycle_id'), str)
            }
            self.assertIn(LEGACY_CYCLE, eligible)
            self.assertGreaterEqual(len(eligible), 11)  # Preserve known certified history.
            self.assertEqual(result['count'], len(eligible) - 1)
            self.assertEqual(result['count'], len(result['reports']))
            self.assertEqual(result['rejected_count'], 1)
            self.assertEqual(result['rejected'][0]['cycle_id'], LEGACY_CYCLE)
            self.assertEqual(result['rejected'][0]['reason'], 'legacy_without_snapshot')
            self.assertEqual(
                {item['cycle_id'] for item in result['reports']},
                set(eligible) - {LEGACY_CYCLE},
            )

            states = {item['cycle_id']: item['completeness'] for item in result['reports']}
            self.assertEqual(len(states), result['count'])
            for cycle_id, row in eligible.items():
                if cycle_id != LEGACY_CYCLE:
                    with self.subTest(cycle_id=cycle_id):
                        self.assertEqual(states[cycle_id], expected_completeness(row))

    def test_bad_integrity_rejected(self):
        with TemporaryDirectory() as d:
            with self.assertRaises(SnapshotError):
                publish({'cycles': []}, self.cid, d, write=True)


if __name__ == '__main__':
    unittest.main()
