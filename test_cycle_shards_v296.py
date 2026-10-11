"""Regresión de V2.9.6: fragmentación reversible sin mutar producción."""
import copy
import hashlib
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from cycle_shards_v296 import (ShardError, audit, canonical_hash, prepare,
                              restore, verify_archive)


def cycle(day, code, size=150):
    cid = f'{day}-{code}'
    snap = {'date': day, 'sample': ['HRV', 'RPE'], 'padding': 'x' * size}
    return {
        'entry_schema_version': 2, 'cycle_id': cid,
        'slot_at': f'{day}T08:30:00+02:00', 'ready_at': f'{day}T08:45:00+02:00',
        'snapshot': snap, 'snapshot_sha256': canonical_hash(snap),
        'state': 'data_ready', 'notification_delivery': 'unverified'
    }


class CycleShardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.ledger = self.base / 'report_cycles.json'
        self.out = self.base / 'shards'
        self.rows = [cycle('2026-10-09', '1645'),
                     cycle('2026-10-09', '2245'),
                     cycle('2026-10-10', '0830'),
                     cycle('2026-10-10', '0830-post-sleep'),
                     cycle('2026-10-10', '1645')]
        self.save()

    def save(self):
        self.original = {'schema_version': 2, 'ledger_version': '2.8.0',
                         'purpose': 'historical ledger',
                         'cycles': copy.deepcopy(self.rows),
                         'count': len(self.rows)}
        self.ledger.write_text(json.dumps(self.original, ensure_ascii=False), encoding='utf-8')

    def prepared(self):
        original_bytes = self.ledger.read_bytes()
        result = prepare(self.ledger, self.out)
        self.assertTrue(result['source_unchanged'])
        self.assertEqual(self.ledger.read_bytes(), original_bytes)
        return result

    def test_audit_reports_count_without_mutation(self):
        source = self.ledger.read_bytes()
        self.assertEqual(audit(self.ledger)['cycle_count'], 5)
        self.assertEqual(self.ledger.read_bytes(), source)

    def test_prepare_verify_all_records(self):
        r = self.prepared()
        self.assertEqual(r['cycle_count'], 5)
        restored, report = verify_archive(self.out, self.ledger)
        self.assertEqual(report['status'], 'verified')
        self.assertEqual(restored, self.original)

    def test_snapshot_sha_preserved(self):
        self.prepared()
        restored, _ = verify_archive(self.out, self.ledger)
        self.assertEqual([c['snapshot_sha256'] for c in restored['cycles']],
                         [c['snapshot_sha256'] for c in self.original['cycles']])

    def test_post_sleep_cycle_not_lost(self):
        self.prepared()
        restored, _ = verify_archive(self.out, self.ledger)
        self.assertIn('2026-10-10-0830-post-sleep', [c['cycle_id'] for c in restored['cycles']])

    def test_restore_does_not_overwrite_existing(self):
        self.prepared()
        target = self.base / 'restore.json'
        target.write_text('original')
        with self.assertRaisesRegex(ShardError, 'existente'):
            restore(self.out, target)
        self.assertEqual(target.read_text(), 'original')

    def test_restore_semantic_equality(self):
        self.prepared()
        target = self.base / 'restored_cycles.json'
        report = restore(self.out, target, self.ledger)
        self.assertEqual(report['status'], 'restored_and_verified')
        self.assertEqual(json.loads(target.read_text()), self.original)

    def test_refuses_replacing_existing_archive(self):
        self.prepared()
        before = (self.out / 'index.json').read_bytes()
        with self.assertRaisesRegex(ShardError, 'existe'):
            prepare(self.ledger, self.out)
        self.assertEqual((self.out / 'index.json').read_bytes(), before)

    def test_rejects_corrupt_snapshot_even_if_data_looks_valid(self):
        self.rows[0]['snapshot']['sample'] = ['wrong']
        self.save()
        with self.assertRaisesRegex(ShardError, 'SHA-256'):
            prepare(self.ledger, self.out)
        self.assertFalse(self.out.exists())

    def test_rejects_corrupt_source_json_no_archive(self):
        self.ledger.write_text('{broken')
        with self.assertRaises(ShardError):
            prepare(self.ledger, self.out)
        self.assertFalse(self.out.exists())

    def test_rejects_duplicate_id(self):
        self.rows.append(copy.deepcopy(self.rows[0]))
        self.save()
        with self.assertRaisesRegex(ShardError, 'duplicado'):
            prepare(self.ledger, self.out)

    def test_rejects_wrong_count(self):
        data = json.loads(self.ledger.read_text())
        data['count'] = 999
        self.ledger.write_text(json.dumps(data))
        with self.assertRaisesRegex(ShardError, 'count'):
            prepare(self.ledger, self.out)

    def test_legacy_entry_without_snapshot_preserved(self):
        self.rows[0] = {'cycle_id': 'legacy',
                        'slot_at': '2026-10-09T16:45:00+02:00',
                        'legacy_without_snapshot': True}
        self.save()
        self.assertEqual(audit(self.ledger)['legacy_count'], 1)
        self.prepared()
        restored, _ = verify_archive(self.out)
        self.assertEqual(restored['cycles'][0], self.rows[0])

    def test_rejects_legacy_without_marker(self):
        self.rows[0] = {'cycle_id': 'legacy',
                        'slot_at': '2026-10-09T16:45:00+02:00'}
        self.save()
        with self.assertRaisesRegex(ShardError, 'legacy'):
            audit(self.ledger)

    def test_missing_shard_rejected(self):
        self.prepared()
        index = json.loads((self.out / 'index.json').read_text())
        (self.out / index['shards'][0]['path']).unlink()
        with self.assertRaisesRegex(ShardError, 'Falta fragmento'):
            verify_archive(self.out)

    def test_modified_shard_rejected(self):
        self.prepared()
        index = json.loads((self.out / 'index.json').read_text())
        path = self.out / index['shards'][0]['path']
        path.write_bytes(path.read_bytes().replace(b'"HRV"', b'"FAKE"'))
        with self.assertRaisesRegex(ShardError, 'SHA-256'):
            verify_archive(self.out)

    def test_index_checksum_modification_rejected(self):
        self.prepared()
        p = self.out / 'index.json'
        j = json.loads(p.read_text()); j['cycles_digest_sha256'] = '0' * 64
        p.write_text(json.dumps(j))
        with self.assertRaisesRegex(ShardError, 'global'):
            verify_archive(self.out)

    def test_path_traversal_rejected(self):
        self.prepared()
        p = self.out / 'index.json'
        j = json.loads(p.read_text()); j['shards'][0]['path'] = '../../report_cycles.json'
        p.write_text(json.dumps(j))
        with self.assertRaisesRegex(ShardError, 'Ruta'):
            verify_archive(self.out)

    def test_changed_source_after_archive_rejected(self):
        self.prepared()
        self.rows.append(cycle('2026-10-11', '0830')); self.save()
        with self.assertRaisesRegex(ShardError, 'ORIGINAL'):
            verify_archive(self.out, self.ledger)
        # Offline copy remains verifiable without comparing newer source
        _, r = verify_archive(self.out)
        self.assertEqual(r['cycle_count'], 5)

    def test_forced_partition_same_day(self):
        self.rows = [cycle('2026-10-10', f'{h:04d}', size=3700) for h in range(10)]
        self.save()
        r = prepare(self.ledger, self.out, byte_limit=10_000)
        self.assertGreater(r['shard_count'], 1)
        rebuilt, _ = verify_archive(self.out, self.ledger)
        self.assertEqual(rebuilt, self.original)

    def test_huge_single_cycle_fails_no_archive(self):
        self.rows = [cycle('2026-10-10', '0830', size=10000)]; self.save()
        with self.assertRaisesRegex(ShardError, 'individual'):
            prepare(self.ledger, self.out, byte_limit=1024)
        self.assertFalse(self.out.exists())

    def test_allows_empty_ledger(self):
        self.rows = []; self.save()
        r = prepare(self.ledger, self.out)
        self.assertEqual(r['shard_count'], 0)
        restored, _ = verify_archive(self.out, self.ledger)
        self.assertEqual(restored, self.original)

    def test_preserves_non_chronological_order(self):
        self.rows = [cycle('2026-10-10', '0830'), cycle('2026-10-09', '2245'),
                     cycle('2026-10-10', '1645')]
        self.save(); self.prepared()
        reconstructed, _ = verify_archive(self.out)
        self.assertEqual(reconstructed, self.original)

    def test_refuses_invalid_shard_size_bounds(self):
        with self.assertRaisesRegex(ShardError, 'inválido'):
            prepare(self.ledger, self.out, byte_limit=100)
        self.assertFalse(self.out.exists())

    def test_refuses_shard_with_wrong_day(self):
        self.prepared()
        index = json.loads((self.out / 'index.json').read_text())
        p = self.out / index['shards'][0]['path']
        raw = json.loads(p.read_text())
        raw['day'] = '2026-10-01'
        p.write_text(json.dumps(raw))
        with self.assertRaises(ShardError):
            verify_archive(self.out)


if __name__ == '__main__':
    unittest.main()
