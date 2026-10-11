"""V2.9.6: preview compacta sin recortar certificados ni alterar producción."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from cycle_shards_v296 import ShardError, canonical_hash, prepare
from ledger_compact_preview_v296 import build, verify, write_preview


def sample(day, slot, size=2500):
    snap = {'date': day, 'metrics': {'hrv': 51}, 'padding': 'X' * size}
    return {'entry_schema_version': 2, 'certificate_kind': 'scheduled_cycle',
            'cycle_id': f'{day}-{slot}', 'slot_at': f'{day}T08:30:00+02:00',
            'ready_at': f'{day}T08:55:00+02:00', 'sync_run_id': 100,
            'crossfit_run_id': 102, 'state': 'data_ready',
            'notification_delivery': 'unverified', 'snapshot': snap,
            'snapshot_sha256': canonical_hash(snap)}


class CompactIndexTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'report_cycles.json'
        self.archive = self.root / 'sharded'
        self.preview_file = self.root / 'preview.json'
        self.cycles = [
            {'cycle_id': '2026-10-08-0830',
             'slot_at': '2026-10-08T08:30:00+02:00',
             'legacy_without_snapshot': True, 'entry_schema_version': 1},
            sample('2026-10-10', '0830'),
            sample('2026-10-11', '0830-post-sleep'),
            sample('2026-10-11', '1645')
        ]
        self.source.write_text(json.dumps({
            'schema_version': 2, 'ledger_version': '2.8.0',
            'purpose': 'Historical data readiness; not receipt',
            'cycles': self.cycles, 'count': len(self.cycles),
        }, indent=2), encoding='utf-8')
        self.start_source = self.source.read_bytes()
        prepare(self.source, self.archive)

    def test_complete_preview_roundtrip(self):
        report = write_preview(self.source, self.archive, self.preview_file)
        self.assertEqual(report['status'], 'compact_preview_verified')
        self.assertEqual(report['cycle_count'], 4)
        self.assertEqual(report['snapshots_verified'], 3)
        self.assertEqual(report['legacy_cycles_preserved'], 1)
        self.assertEqual(report['shard_count'], 3)
        self.assertTrue(report['complete_reconstruction'])
        self.assertEqual(self.source.read_bytes(), self.start_source)

    def test_preview_is_smaller_than_source(self):
        report = write_preview(self.source, self.archive, self.preview_file)
        self.assertLess(report['preview_bytes'], report['source_bytes'])
        self.assertGreater(report['preview_reduction_pct'], 20)

    def test_not_a_production_ledger(self):
        preview = build(self.source, self.archive)
        self.assertEqual(preview['schema_version'], 3)
        self.assertIn('DO_NOT_REPLACE_REPORT_CYCLES', preview['migration_state'])
        self.assertTrue(all('snapshot' not in entry['metadata'] for entry in preview['cycles']))

    def test_snapshot_pointers_are_bounded_and_unique_by_index(self):
        preview = build(self.source, self.archive)
        for i, x in enumerate(preview['cycles']):
            self.assertEqual(x['record_index'], i)
            self.assertTrue(x['shard_ref']['path'].startswith('shards/'))
        self.assertEqual(preview['cycles'][2]['cycle_id'], '2026-10-11-0830-post-sleep')

    def test_reject_metadata_tampering(self):
        preview = build(self.source, self.archive)
        preview['cycles'][1]['metadata']['sync_run_id'] = 999
        with self.assertRaisesRegex(ShardError, 'compacto'):
            verify(self.source, self.archive, preview)

    def test_reject_pointers_tampering(self):
        preview = build(self.source, self.archive)
        preview['cycles'][1]['shard_ref']['offset'] = 999
        with self.assertRaisesRegex(ShardError, 'compacto'):
            verify(self.source, self.archive, preview)

    def test_reject_index_hash_tampering(self):
        preview = build(self.source, self.archive)
        preview['shard_index_bytes_sha256'] = '0' * 64
        with self.assertRaisesRegex(ShardError, 'indice no coincide'):
            verify(self.source, self.archive, preview)

    def test_reject_source_later_changed(self):
        preview = build(self.source, self.archive)
        data = json.loads(self.source.read_text())
        data['cycles'].append(sample('2026-10-12', '0830'))
        data['count'] += 1
        self.source.write_text(json.dumps(data))
        with self.assertRaises(ShardError):
            verify(self.source, self.archive, preview)

    def test_reject_shard_bytes_modified(self):
        preview = build(self.source, self.archive)
        f = self.archive / preview['cycles'][1]['shard_ref']['path']
        f.write_bytes(f.read_bytes() + b' ')
        with self.assertRaisesRegex(ShardError, 'SHA-256'):
            verify(self.source, self.archive, preview)

    def test_refuse_overwriting_existing_output(self):
        self.preview_file.write_text('do not overwrite')
        with self.assertRaisesRegex(ShardError, 'sobrescribe'):
            write_preview(self.source, self.archive, self.preview_file)
        self.assertEqual(self.preview_file.read_text(), 'do not overwrite')

    def test_corrupt_preview_rejected(self):
        preview = build(self.source, self.archive)
        preview['cycles'] = preview['cycles'][:-1]
        with self.assertRaisesRegex(ShardError, 'Falta algun ciclo'):
            verify(self.source, self.archive, preview)

    def test_empty_ledger_is_supported(self):
        self.archive.rename(self.root / 'old_sharded')
        self.archive = self.root / 'empty_sharded'
        self.source.write_text(json.dumps({
            'schema_version': 2, 'ledger_version': '2.8.0',
            'cycles': [], 'count': 0,
        }))
        prepare(self.source, self.archive)
        result = write_preview(self.source, self.archive, self.preview_file)
        self.assertEqual(result['cycle_count'], 0)
        self.assertTrue(result['complete_reconstruction'])


if __name__ == '__main__':
    unittest.main()
