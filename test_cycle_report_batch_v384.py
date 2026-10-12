import copy
import json
import tempfile
import unittest
from pathlib import Path
from cycle_report_batch_v384 import run
from cycle_snapshot_report_v38 import SnapshotError

LEDGER = Path(__file__).with_name('report_cycles.json')
CID = '2026-10-12-1645'


class BatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = json.loads(LEDGER.read_text(encoding='utf-8'))

    def test_real_cycle_and_idempotence(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = run(self.ledger, tmp, CID)
            second = run(self.ledger, tmp, CID)
            self.assertEqual(first['count'], 1)
            self.assertEqual(first['reports'][0]['state'], 'published_local')
            self.assertEqual(second['reports'][0]['state'], 'already_present')
            self.assertEqual(len(list(Path(tmp).glob('*.md'))), 1)
            self.assertEqual(first['delivery'], 'unverified_no_receipt')

    def test_rejects_tampering(self):
        altered = copy.deepcopy(self.ledger)
        row = next(x for x in altered['cycles'] if x.get('cycle_id') == CID)
        row['snapshot']['recovery_assessment']['current']['hrv_ms'] = 999
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(SnapshotError):
            run(altered, tmp, CID)

    def test_rejects_missing_cycle(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(SnapshotError):
            run(self.ledger, tmp, '2099-01-01-1645')

    def test_rejects_duplicate_eligible_cycle(self):
        altered = copy.deepcopy(self.ledger)
        row = next(x for x in altered['cycles'] if x.get('cycle_id') == CID)
        altered['cycles'].append(copy.deepcopy(row))
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(SnapshotError):
            run(altered, tmp, CID)


if __name__ == '__main__':
    unittest.main()

class InvalidCycleIsolationTests(unittest.TestCase):
    def test_invalid_cycle_does_not_block_certified_cycle(self):
        ledger = copy.deepcopy(BatchTests.ledger)
        bad = copy.deepcopy(next(x for x in ledger['cycles'] if x.get('cycle_id') == CID))
        bad['cycle_id'] = '2026-10-13-1645'
        bad['slot_at'] = '2026-10-13T16:45:00+02:00'
        # Tampered snapshot digest must never be accepted.
        bad['snapshot']['recovery_assessment']['current']['hrv_ms'] = 999
        ledger['cycles'].append(bad)
        with tempfile.TemporaryDirectory() as tmp:
            result = run(ledger, tmp)
            self.assertGreaterEqual(result['count'], 1)
            self.assertIn('2026-10-13-1645', [x['cycle_id'] for x in result['rejected']])
            self.assertNotIn('2026-10-13-1645', [x['cycle_id'] for x in result['reports']])
            self.assertEqual(result['delivery'], 'unverified_no_receipt')

    def test_explicit_invalid_cycle_still_fails(self):
        ledger = copy.deepcopy(BatchTests.ledger)
        row = next(x for x in ledger['cycles'] if x.get('cycle_id') == CID)
        row['snapshot']['recovery_assessment']['current']['hrv_ms'] = 999
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(SnapshotError):
            run(ledger, tmp, CID)
