"""Regression for V2.9.6 explicit-format ledger read-only adapter."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from garmin_recovery.cycle_shards import ShardError, canonical_hash, prepare
from garmin_recovery.ledger_compact_preview import write_preview
from garmin_recovery.ledger_access import read_compatible


def row(day, code, size=1500, legacy=False):
    obj = {'cycle_id': f'{day}-{code}',
           'slot_at': f'{day}T08:30:00+02:00',
           'state': 'data_ready', 'notification_delivery': 'unverified'}
    if legacy:
        obj['legacy_without_snapshot'] = True
    else:
        obj['snapshot'] = {'day': day, 'samples': [54, None], 'extra': 'x' * size}
        obj['snapshot_sha256'] = canonical_hash(obj['snapshot'])
    return obj


class CompatibleReaderTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.original = self.root / 'report_cycles.json'
        self.directory = self.root / 'shards'
        self.preview = self.root / 'preview.json'
        self.ledger = {'schema_version': 2, 'ledger_version': '2.8.0',
                       'purpose': 'technical ledger',
                       'cycles': [row('2026-10-09', '1645', legacy=True),
                                  row('2026-10-10', '0830'),
                                  row('2026-10-10', '0830-post-sleep'),
                                  row('2026-10-10', '1645')], 'count': 4}
        self.original.write_text(json.dumps(self.ledger, indent=2), encoding='utf-8')

    def prepared(self):
        prepare(self.original, self.directory)
        write_preview(self.original, self.directory, self.preview)

    def test_legacy_is_safe_default(self):
        v, report = read_compatible(self.original)
        self.assertEqual(v, self.ledger)
        self.assertEqual(report['status'], 'validated_legacy')
        self.assertFalse(report['production_cutover'])

    def test_legacy_rejects_partial_shard_paths(self):
        with self.assertRaises(ShardError):
            read_compatible(self.original, archive_dir=self.directory)

    def test_rejects_invalid_mode(self):
        for mode in ('auto', '', 'fallback', 'write', None):
            with self.subTest(mode=mode), self.assertRaises(ShardError):
                read_compatible(self.original, mode=mode)

    def test_legacy_missing_source_fails_closed(self):
        with self.assertRaises(ShardError):
            read_compatible(self.root / 'missing.json')

    def test_legacy_detects_corrupted_snapshot(self):
        changed = copy.deepcopy(self.ledger)
        changed['cycles'][1]['snapshot']['day'] = 'tampered'
        self.original.write_text(json.dumps(changed), encoding='utf-8')
        with self.assertRaises(ShardError):
            read_compatible(self.original)

    def test_shadow_compare_roundtrip(self):
        self.prepared()
        source = self.original.read_bytes()
        v, report = read_compatible(self.original, mode='shadow_compare',
                                   preview_path=self.preview, archive_dir=self.directory)
        self.assertEqual(v, self.ledger)
        self.assertEqual(report['status'], 'shadow_cross_checked')
        self.assertEqual(report['snapshots_verified'], 3)
        self.assertEqual(report['legacy_records_preserved'], 1)
        self.assertEqual(self.original.read_bytes(), source)

    def test_shadow_requires_both_paths(self):
        with self.assertRaises(ShardError):
            read_compatible(self.original, mode='shadow_compare', preview_path=self.preview)
        with self.assertRaises(ShardError):
            read_compatible(self.original, mode='shadow_compare', archive_dir=self.directory)

    def test_shadow_missing_archive_does_not_fallback(self):
        with self.assertRaises(ShardError):
            read_compatible(self.original, mode='shadow_compare',
                            preview_path=self.preview, archive_dir=self.directory)

    def test_shadow_fails_when_original_changes(self):
        self.prepared()
        changed = copy.deepcopy(self.ledger)
        changed['cycles'].append(row('2026-10-11', '0830'))
        changed['count'] += 1
        self.original.write_text(json.dumps(changed), encoding='utf-8')
        with self.assertRaises(ShardError):
            read_compatible(self.original, mode='shadow_compare',
                            preview_path=self.preview, archive_dir=self.directory)

    def test_shadow_fails_when_shard_missing(self):
        self.prepared()
        target = next((self.directory/'shards').rglob('*.json'))
        target.unlink()
        with self.assertRaises(ShardError):
            read_compatible(self.original, mode='shadow_compare',
                            preview_path=self.preview, archive_dir=self.directory)

    def test_shadow_fails_when_preview_tampered(self):
        self.prepared()
        obj = json.loads(self.preview.read_text())
        obj['cycles'][0]['cycle_id'] = 'falsified'
        self.preview.write_text(json.dumps(obj))
        with self.assertRaises(ShardError):
            read_compatible(self.original, mode='shadow_compare',
                            preview_path=self.preview, archive_dir=self.directory)

    def test_shards_only_without_original(self):
        self.prepared()
        self.original.unlink()
        v, report = read_compatible(self.original, mode='shards_only',
                                   preview_path=self.preview, archive_dir=self.directory)
        self.assertEqual(v, self.ledger)
        self.assertFalse(report['source_original_verified'])
        self.assertEqual(report['status'], 'shards_verified')

    def test_shards_only_no_implicit_fallback(self):
        self.prepared()
        self.preview.unlink()
        with self.assertRaises(ShardError):
            read_compatible(self.original, mode='shards_only',
                            preview_path=self.preview, archive_dir=self.directory)

    def test_shards_only_requires_paths(self):
        with self.assertRaises(ShardError):
            read_compatible(self.original, mode='shards_only')

    def test_preserves_post_sleep(self):
        self.prepared()
        v, _ = read_compatible(self.original, mode='shards_only',
                               preview_path=self.preview, archive_dir=self.directory)
        self.assertIn('2026-10-10-0830-post-sleep', [x['cycle_id'] for x in v['cycles']])

    def test_preserves_order_and_metadata(self):
        self.prepared()
        v, _ = read_compatible(self.original, mode='shadow_compare',
                               preview_path=self.preview, archive_dir=self.directory)
        self.assertEqual(v['cycles'], self.ledger['cycles'])
        self.assertEqual(v['purpose'], self.ledger['purpose'])

    def test_read_only_no_outputs(self):
        self.prepared()
        before={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        for mode in ('legacy_only','shadow_compare','shards_only'):
            paths={} if mode == 'legacy_only' else {'preview_path':self.preview,'archive_dir':self.directory}
            read_compatible(self.original,mode=mode,**paths)
        after={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before,after)

    def test_shards_only_detects_corrupt_archive(self):
        self.prepared()
        target=next((self.directory/'shards').rglob('*.json'))
        target.write_text('{}')
        with self.assertRaises(ShardError):
            read_compatible(self.original,mode='shards_only',preview_path=self.preview,archive_dir=self.directory)


if __name__=='__main__':
    unittest.main()
