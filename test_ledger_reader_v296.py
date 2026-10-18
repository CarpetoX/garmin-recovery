"""V2.9.6: pruebas de recuperación INDEPENDIENTE sin histórico original."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from garmin_recovery.cycle_shards import ShardError, canonical_hash, prepare
from garmin_recovery.ledger_compact_preview import write_preview
from garmin_recovery.ledger_reader import reconstruct


def cycle(day, slot, legacy=False):
    data = {
        'entry_schema_version': 2 if not legacy else 1,
        'cycle_id': f'{day}-{slot}', 'slot_at': f'{day}T08:30:00+02:00',
        'ready_at': f'{day}T08:50:00+02:00', 'state': 'data_ready',
    }
    if legacy:
        data['legacy_without_snapshot'] = True
    else:
        snap = {'day': day, 'measurements': {'hrv': 52, 'sleep': None}}
        data['snapshot'] = snap
        data['snapshot_sha256'] = canonical_hash(snap)
    return data


class LedgerReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.original_file = self.root / 'report_cycles.json'
        self.shards = self.root / 'shards'
        self.preview = self.root / 'preview.json'
        self.original = {
            'schema_version': 2, 'count': 4,
            'purpose': 'test_ledger_only',
            'cycles': [cycle('2026-10-09', '0830'),
                       cycle('2026-10-09', '0830-post-sleep'),
                       cycle('2026-10-10', '1645'),
                       cycle('2026-10-10', '2245', legacy=True)],
        }
        self.original_file.write_text(json.dumps(self.original, ensure_ascii=False), encoding='utf-8')
        prepare(self.original_file, self.shards)
        write_preview(self.original_file, self.shards, self.preview)

    def change_preview(self, callback):
        data = json.loads(self.preview.read_bytes())
        callback(data)
        self.preview.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

    def check_reject(self):
        with self.assertRaises(ShardError):
            reconstruct(self.preview, self.shards)

    def test_independent_without_original(self):
        self.original_file.unlink()
        actual, report = reconstruct(self.preview, self.shards)
        self.assertEqual(actual, self.original)
        self.assertFalse(report['original_cross_checked'])
        self.assertEqual(report['certificates'], 4)

    def test_cross_check_original(self):
        original_bytes = self.original_file.read_bytes()
        result, report = reconstruct(self.preview, self.shards, self.original_file)
        self.assertEqual(result, self.original)
        self.assertTrue(report['original_cross_checked'])
        self.assertEqual(self.original_file.read_bytes(), original_bytes)

    def test_post_sleep_kept(self):
        a, _ = reconstruct(self.preview, self.shards)
        self.assertIn('2026-10-09-0830-post-sleep', [x['cycle_id'] for x in a['cycles']])

    def test_legacy_kept(self):
        _, r = reconstruct(self.preview, self.shards)
        self.assertEqual(r['legacy_records_preserved'], 1)

    def test_snapshot_hash_verification(self):
        _, r = reconstruct(self.preview, self.shards)
        self.assertEqual(r['snapshots_verified'], 3)

    def test_index_metadata_tamper(self):
        self.change_preview(lambda d: d['cycles'][0]['metadata'].update({'ready_at': '2030-01-01'}))
        self.check_reject()

    def test_index_ref_tamper(self):
        self.change_preview(lambda d: d['cycles'][0]['shard_ref'].update({'offset': 1}))
        self.check_reject()

    def test_index_source_sha_tamper(self):
        self.change_preview(lambda d: d.update({'source_bytes_sha256': '0'*64}))
        self.check_reject()

    def test_wrong_record_count(self):
        self.change_preview(lambda d: d.update({'source_cycle_count': 99}))
        self.check_reject()

    def test_index_order_tamper(self):
        self.change_preview(lambda d: d['cycles'].reverse())
        self.check_reject()

    def test_requires_explicit_preview_state(self):
        self.change_preview(lambda d: d.update({'migration_state': 'PRODUCTION_ENABLED'}))
        self.check_reject()

    def test_missing_fragment(self):
        path = next((self.shards / 'shards').rglob('*.json'))
        path.unlink()
        self.check_reject()

    def test_modified_fragment(self):
        path = next((self.shards / 'shards').rglob('*.json'))
        obj = json.loads(path.read_bytes())
        obj['cycles'][0]['ready_at'] = '2040-01-01'
        path.write_text(json.dumps(obj), encoding='utf-8')
        self.check_reject()

    def test_changed_original_detected(self):
        j = copy.deepcopy(self.original)
        j['cycles'][0]['ready_at'] = '2040-01-01'
        self.original_file.write_text(json.dumps(j), encoding='utf-8')
        with self.assertRaises(ShardError):
            reconstruct(self.preview, self.shards, self.original_file)

    def test_missing_index(self):
        (self.shards / 'index.json').unlink()
        self.check_reject()

    def test_index_empty_wrong_root(self):
        self.change_preview(lambda d: d['root_metadata'].update({'purpose': 'different'}))
        self.check_reject()

    def test_no_source_file_writes(self):
        originals={p.relative_to(self.root):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        reconstruct(self.preview, self.shards)
        now={p.relative_to(self.root):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(originals, now)


if __name__ == '__main__':
    unittest.main()
