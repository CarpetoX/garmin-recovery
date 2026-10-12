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
