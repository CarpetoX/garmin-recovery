import copy
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from garmin_recovery.cycle_snapshot_report import digest, SnapshotError
from garmin_recovery.cycle_report_compat import render
from garmin_recovery.cycle_report_batch import run


LEGACY_CYCLE = '2026-10-09-1645'


def eligible_cycles(ledger):
    return {
        row['cycle_id']: row
        for row in ledger['cycles']
        if isinstance(row, dict)
        and row.get('state') == 'data_ready'
        and isinstance(row.get('cycle_id'), str)
    }


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


class HistoricalQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = json.loads(Path('report_cycles.json').read_text(encoding='utf-8'))

    def test_real_ledger_expected_classification(self):
        with TemporaryDirectory() as d:
            result = run(self.ledger, d)
            eligible = eligible_cycles(self.ledger)
            self.assertIn(LEGACY_CYCLE, eligible)
            self.assertGreaterEqual(len(eligible), 11)  # Retain historical baseline.

            # New certified cycles must not break the test merely by arriving.
            self.assertEqual(result['count'], len(eligible) - 1)
            self.assertEqual(result['count'], len(result['reports']))
            self.assertEqual(result['rejected_count'], 1)
            self.assertEqual(result['rejected_count'], len(result['rejected']))
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

    def test_partial_retains_metrics(self):
        ledger = copy.deepcopy(self.ledger)
        row = next(x for x in ledger['cycles'] if x['cycle_id'] == '2026-10-12-1645')
        row['snapshot']['crossfit']['performance_report'].pop('daily_chart_7d', None)
        row['snapshot_sha256'] = digest(row['snapshot'])
        report, state = render(ledger, row['cycle_id'])
        self.assertEqual(state, 'partial_missing_crossfit_chart')
        for section in ('## Recuperación y sueño', '## CrossFit', '## Frecuencia cardíaca', 'Gráfica diaria CrossFit: no disponible'):
            self.assertIn(section, report)

    def test_tamper_rejected(self):
        ledger = copy.deepcopy(self.ledger)
        row = next(x for x in ledger['cycles'] if x['cycle_id'] == '2026-10-12-1645')
        row['snapshot']['date'] = '1999-01-01'
        with self.assertRaises(SnapshotError):
            render(ledger, row['cycle_id'])

    def test_deterministic_report(self):
        cid = '2026-10-12-1645'
        self.assertEqual(render(self.ledger, cid), render(self.ledger, cid))

    def test_unsafe_id(self):
        with self.assertRaises(SnapshotError):
            render(self.ledger, '../escape')


if __name__ == '__main__':
    unittest.main()
