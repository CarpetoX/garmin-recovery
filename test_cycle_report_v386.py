import copy
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from cycle_snapshot_report_v38 import digest, SnapshotError
from cycle_report_compat_v386 import render
from cycle_report_batch_v386 import run

class HistoricalQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = json.loads(Path('report_cycles.json').read_text(encoding='utf-8'))

    def test_real_ledger_expected_classification(self):
        with TemporaryDirectory() as d:
            result = run(self.ledger, d)
            self.assertEqual(result['count'], 10)
            self.assertEqual(result['rejected_count'], 1)
            self.assertEqual(result['rejected'][0]['cycle_id'], '2026-10-09-1645')
            self.assertEqual(result['rejected'][0]['reason'], 'legacy_without_snapshot')
            self.assertEqual(sum(x['completeness'] == 'complete' for x in result['reports']), 4)
            self.assertEqual(sum(x['completeness'] == 'partial_missing_crossfit_chart' for x in result['reports']), 6)

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
