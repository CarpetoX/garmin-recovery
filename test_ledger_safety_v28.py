import copy
import json
import tempfile
import unittest
from pathlib import Path
from garmin_recovery.archive_report_cycles import digest, audit
from garmin_recovery.ledger_safety import LedgerSafetyError, atomic_write_ledger

def cycle(i):
    snap = {'value': i}
    return {'cycle_id': f'2026-10-{(i%28)+1:02d}-{i:04d}',
            'slot_at': '2026-10-11T08:30:00+02:00',
            'snapshot': snap, 'snapshot_sha256': digest(snap)}

class LedgerSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'report_cycles.json'
    def write(self, rows):
        return atomic_write_ledger(self.path, rows)
    def test_new_file_is_auditable(self):
        self.assertEqual(self.write([cycle(1)])['cycles_now'], 1)
        self.assertEqual(audit(self.path)['verified'], 1)
    def test_no_truncation_past_120(self):
        self.write([cycle(i) for i in range(125)])
        self.assertEqual(audit(self.path)['cycles'], 125)
        self.write([cycle(i) for i in range(127)])
        self.assertEqual(audit(self.path)['cycles'], 127)
    def test_refuses_missing_old_record(self):
        self.write([cycle(1), cycle(2)])
        before = self.path.read_bytes()
        with self.assertRaisesRegex(LedgerSafetyError, 'descartar'):
            self.write([cycle(2)])
        self.assertEqual(before, self.path.read_bytes())
    def test_refuses_changed_old_record(self):
        self.write([cycle(1)])
        wrong = copy.deepcopy(cycle(1))
        wrong['snapshot']['value'] = 20
        wrong['snapshot_sha256'] = digest(wrong['snapshot'])
        with self.assertRaisesRegex(LedgerSafetyError, 'modificado'):
            self.write([wrong])
        self.assertEqual(audit(self.path)['verified'], 1)
    def test_refuses_corrupt_existing_json(self):
        self.path.write_text('{bad', encoding='utf-8')
        original = self.path.read_bytes()
        with self.assertRaisesRegex(LedgerSafetyError, 'ilegible'):
            self.write([cycle(1)])
        self.assertEqual(original, self.path.read_bytes())
    def test_refuses_tampered_hash(self):
        self.write([cycle(1)])
        data = json.loads(self.path.read_text(encoding='utf-8'))
        data['cycles'][0]['snapshot']['value'] = 999
        self.path.write_text(json.dumps(data), encoding='utf-8')
        before = self.path.read_bytes()
        with self.assertRaisesRegex(LedgerSafetyError, 'SHA-256'):
            self.write(data['cycles'])
        self.assertEqual(before, self.path.read_bytes())
    def test_duplicate_new_rows_rejected(self):
        with self.assertRaisesRegex(LedgerSafetyError, 'duplicado'):
            self.write([cycle(1), cycle(1)])
        self.assertFalse(self.path.exists())
    def test_existing_invalid_json_structure_rejected(self):
        self.path.write_text('[]')
        with self.assertRaisesRegex(LedgerSafetyError, 'estructura'):
            self.write([cycle(1)])
    def test_legacy_upgrade_preserves_ids(self):
        original = {'schema_version': 1, 'cycles': [
            {'cycle_id': 'old-1', 'slot_at': '2026-10-01T08:30:00+02:00'}]}
        self.path.write_text(json.dumps(original), encoding='utf-8')
        old = dict(original['cycles'][0], legacy_without_snapshot=True)
        self.write([old, cycle(1)])
        self.assertEqual(audit(self.path)['legacy'], 1)
    def test_legacy_upgrade_refuses_lost_id(self):
        self.path.write_text(json.dumps({'cycles': [{'cycle_id': 'old-1'}]}))
        with self.assertRaisesRegex(LedgerSafetyError, 'descartar'):
            self.write([cycle(1)])
    def test_do_not_allow_invalid_snapshot(self):
        bad = cycle(1)
        bad['snapshot_sha256'] = '0'*64
        with self.assertRaisesRegex(LedgerSafetyError, 'nuevo no válido'):
            self.write([bad])
    def test_atomic_output_has_no_temp_residue(self):
        self.write([cycle(1)])
        self.assertEqual(sorted(x.name for x in self.path.parent.iterdir()), ['report_cycles.json'])

if __name__ == '__main__':
    unittest.main()
