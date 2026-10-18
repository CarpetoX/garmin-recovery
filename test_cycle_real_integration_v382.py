"""Read-only integration against the certified 2026-10-12 historical cycle.

CI test intentionally pins the historical digest; no live files or dispatches.
"""
import copy
import json
import unittest
from pathlib import Path
from garmin_recovery.cycle_snapshot_report import digest, SnapshotError
from garmin_recovery.cycle_visual_report import make

CYCLE = '2026-10-12-1645'
SHA = 'f3343c8527b36cbec089f6cefd0e8e7ca56604969c84c7a2c8105589d4dddbbe'
LEDGER = Path(__file__).with_name('report_cycles.json')


class RealHistoricalCycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = json.loads(LEDGER.read_text(encoding='utf-8'))
        cls.rows = [x for x in cls.ledger['cycles'] if x.get('cycle_id') == CYCLE]

    def test_unique_and_pinned_digest(self):
        self.assertEqual(len(self.rows), 1)
        row = self.rows[0]
        self.assertEqual(row['state'], 'data_ready')
        self.assertEqual(row['snapshot_sha256'], SHA)
        self.assertEqual(digest(row['snapshot']), SHA)
        self.assertEqual(row['source_generated_at'], row['snapshot']['source_generated_at'])

    def test_real_report_contains_expected_sections_and_values(self):
        report = make(self.ledger, CYCLE)
        for phrase in ('Informe histórico V3.8.2', CYCLE, SHA,
                       'HRV nocturna', '66 ms', '53 lpm',
                       'CrossFit', '1457.7', 'Frecuencia cardíaca',
                       'Limitaciones y trazabilidad'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, report)
        self.assertNotIn('2026-10-13', report)

    def test_tampering_rejected(self):
        tampered = copy.deepcopy(self.ledger)
        row = next(x for x in tampered['cycles'] if x['cycle_id'] == CYCLE)
        row['snapshot']['recovery_assessment']['current']['hrv_ms'] = 999
        with self.assertRaises(SnapshotError):
            make(tampered, CYCLE)

    def test_reproducible(self):
        self.assertEqual(make(self.ledger, CYCLE), make(self.ledger, CYCLE))


if __name__ == '__main__':
    unittest.main()
