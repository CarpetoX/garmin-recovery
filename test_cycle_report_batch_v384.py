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

        # Use an unoccupied valid slot on the same day as the source snapshot.
        # A fixed 2026-10-13-1645 used to collide with the growing real ledger.
        existing_ids = {
            row.get('cycle_id') for row in ledger['cycles'] if isinstance(row, dict)
        }
        candidates = (
            f'{CID[:10]}-{hour:02d}{minute:02d}'
            for hour in range(24) for minute in range(60)
        )
        bad_cycle_id = next((cid for cid in candidates if cid not in existing_ids), None)
        self.assertIsNotNone(bad_cycle_id, 'No unused test cycle ID available')

        bad['cycle_id'] = bad_cycle_id
        original_slot_at = bad['slot_at']
        bad['slot_at'] = (
            f'{original_slot_at[:11]}{bad_cycle_id[-4:-2]}:'
            f'{bad_cycle_id[-2:]}{original_slot_at[16:]}'
        )
        # Tampered snapshot digest must never be accepted.
        bad['snapshot']['recovery_assessment']['current']['hrv_ms'] = 999
        ledger['cycles'].append(bad)

        with tempfile.TemporaryDirectory() as tmp:
            result = run(ledger, tmp)
            self.assertGreaterEqual(result['count'], 1)
            self.assertIn(bad_cycle_id, [x['cycle_id'] for x in result['rejected']])
            rejected_bad = next(x for x in result['rejected'] if x['cycle_id'] == bad_cycle_id)
            self.assertIn('SHA-256 mismatch', rejected_bad['detail'])
            self.assertNotIn(bad_cycle_id, [x['cycle_id'] for x in result['reports']])
            self.assertEqual(result['delivery'], 'unverified_no_receipt')

    def test_explicit_invalid_cycle_still_fails(self):
        ledger = copy.deepcopy(BatchTests.ledger)
        row = next(x for x in ledger['cycles'] if x.get('cycle_id') == CID)
        row['snapshot']['recovery_assessment']['current']['hrv_ms'] = 999
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(SnapshotError):
            run(ledger, tmp, CID)
