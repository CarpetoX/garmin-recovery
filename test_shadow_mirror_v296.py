"""V2.9.6: pruebas de espejo persistible en ENSAYO, sin mutar produccion."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from garmin_recovery.cycle_shards import ShardError, canonical_hash
from garmin_recovery.ledger_access import read_compatible
from garmin_recovery.shadow_mirror import plan, prepare_candidate, verify_candidate


def cycle(day, suffix, legacy=False, size=1200):
    row = {'cycle_id': f'{day}-{suffix}',
           'slot_at': f'{day}T08:30:00+02:00',
           'entry_schema_version': 2, 'state': 'data_ready'}
    if legacy:
        row['legacy_without_snapshot'] = True
    else:
        row['snapshot'] = {'day': day, 'wellness': [54, 82], 'payload': 'm' * size}
        row['snapshot_sha256'] = canonical_hash(row['snapshot'])
    return row


class ShadowMirrorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.original = self.base / 'report_cycles.json'
        self.old = self.base / 'mirror-1'
        self.new = self.base / 'mirror-2'
        self.rows = [cycle('2026-10-09', '1645', legacy=True),
                     cycle('2026-10-10', '0830'),
                     cycle('2026-10-10', '0830-post-sleep'),
                     cycle('2026-10-11', '1645')]
        self.save()

    def save(self):
        self.data = {'schema_version': 2, 'ledger_version': '2.8.0',
                     'purpose': 'historical ledger',
                     'cycles': copy.deepcopy(self.rows), 'count': len(self.rows)}
        self.original.write_text(json.dumps(self.data, indent=2), encoding='utf-8')

    def initial(self):
        before = self.original.read_bytes()
        x = prepare_candidate(self.original, self.old)
        self.assertFalse(x['production_cutover'])
        self.assertEqual(before, self.original.read_bytes())
        return x

    def extend(self, day='2026-10-12', suffix='0830'):
        self.rows.append(cycle(day, suffix))
        self.save()

    def test_plan_non_mutating(self):
        before = self.original.read_bytes()
        r = plan(self.original)
        self.assertEqual(r['certificates_now'], 4)
        self.assertEqual(r['new_certificates'], 4)
        self.assertEqual(self.original.read_bytes(), before)

    def test_bootstrap_all_certificates(self):
        r = self.initial()
        self.assertEqual(r['certificates'], 4)
        self.assertEqual(r['shard_count'], 3)
        self.assertEqual(r['snapshot_checksums_validated'], 3)
        self.assertEqual(r['legacy_records_preserved'], 1)
        self.assertEqual(verify_candidate(self.original, self.old)['status'], 'candidate_verified')

    def test_shadow_reader_reconstructs_without_source(self):
        self.initial()
        recovered, _ = read_compatible(self.base / 'nonexistent.json', mode='shards_only',
                                        preview_path=self.old / 'compact-preview.json',
                                        archive_dir=self.old / 'archive')
        self.assertEqual(self.data, recovered)

    def test_old_versions_unmodified_after_new_stage(self):
        self.initial()
        original_mirror = {p.relative_to(self.old): p.read_bytes()
                           for p in self.old.rglob('*') if p.is_file()}
        self.extend()
        report = prepare_candidate(self.original, self.new, self.old)
        self.assertEqual(report['new_certificates'], 1)
        self.assertEqual(report['preserved'], 4)
        self.assertEqual({p.relative_to(self.old): p.read_bytes()
                          for p in self.old.rglob('*') if p.is_file()}, original_mirror)

    def test_reuses_stable_unchanged_day_shards(self):
        self.initial()
        self.extend()
        r = prepare_candidate(self.original, self.new, self.old)
        self.assertGreaterEqual(r['reusable_unchanged_shards'], 2)

    def test_index_preserves_post_sleep(self):
        self.initial()
        self.extend()
        prepare_candidate(self.original, self.new, self.old)
        x, _ = read_compatible(self.original, mode='shadow_compare',
                   preview_path=self.new / 'compact-preview.json',
                   archive_dir=self.new / 'archive')
        self.assertIn('2026-10-10-0830-post-sleep', [r['cycle_id'] for r in x['cycles']])

    def test_second_run_idempotent(self):
        self.initial()
        r = prepare_candidate(self.original, self.new, self.old)
        self.assertEqual(r['new_certificates'], 0)
        self.assertEqual(r['preserved'], 4)

    def test_rejects_missing_prior_certificate(self):
        self.initial()
        self.rows.pop(2)
        self.save()
        with self.assertRaisesRegex(ShardError, 'desaparecido'):
            prepare_candidate(self.original, self.new, self.old)
        self.assertFalse(self.new.exists())

    def test_rejects_changed_old_snapshot_with_recalculated_sha(self):
        self.initial()
        self.rows[1]['snapshot']['wellness'][0] = 0
        self.rows[1]['snapshot_sha256'] = canonical_hash(self.rows[1]['snapshot'])
        self.save()
        with self.assertRaisesRegex(ShardError, 'antiguo modificado'):
            prepare_candidate(self.original, self.new, self.old)
        self.assertFalse(self.new.exists())

    def test_rejects_reordered_old_certificates(self):
        self.initial()
        self.rows[1], self.rows[2] = self.rows[2], self.rows[1]
        self.save()
        with self.assertRaisesRegex(ShardError, 'orden relativo'):
            prepare_candidate(self.original, self.new, self.old)

    def test_allows_new_cycle_interleaved_with_existing(self):
        self.initial()
        self.rows.insert(2, cycle('2026-10-10', '1200'))
        self.save()
        r = prepare_candidate(self.original, self.new, self.old)
        self.assertEqual(r['new_certificates'], 1)
        self.assertEqual(r['preserved'], 4)

    def test_rejects_changed_root_metadata(self):
        self.initial()
        self.extend()
        self.data = json.loads(self.original.read_bytes())
        self.data['purpose'] = 'tampered'
        self.original.write_text(json.dumps(self.data))
        with self.assertRaisesRegex(ShardError, 'metadatos'):
            prepare_candidate(self.original, self.new, self.old)

    def test_invalid_previous_path_fails(self):
        with self.assertRaises(ShardError):
            prepare_candidate(self.original, self.new, self.base / 'no-mirror')

    def test_missing_prior_state_rejected(self):
        self.initial()
        (self.old / 'state.json').unlink()
        with self.assertRaises(ShardError):
            prepare_candidate(self.original, self.new, self.old)

    def test_tampered_previous_archive_rejected(self):
        self.initial()
        victim = next((self.old / 'archive' / 'shards').rglob('*.json'))
        victim.write_bytes(victim.read_bytes() + b'bad')
        with self.assertRaises(ShardError):
            prepare_candidate(self.original, self.new, self.old)

    def test_tampered_previous_state_rejected(self):
        self.initial()
        state = json.loads((self.old / 'state.json').read_bytes())
        state['certificate_count'] += 1
        (self.old / 'state.json').write_text(json.dumps(state))
        with self.assertRaises(ShardError):
            plan(self.original, self.old)

    def test_destination_existing_never_overwritten(self):
        self.new.mkdir()
        (self.new / 'important.txt').write_text('must survive')
        with self.assertRaises(ShardError):
            prepare_candidate(self.original, self.new)
        self.assertEqual((self.new / 'important.txt').read_text(), 'must survive')

    def test_reject_output_inside_previous(self):
        self.initial()
        with self.assertRaises(ShardError):
            prepare_candidate(self.original, self.old / 'subdir', self.old)

    def test_corrupt_new_candidate_rejected(self):
        self.initial()
        state = json.loads((self.old / 'state.json').read_bytes())
        state['source_file_sha256'] = 'f' * 64
        (self.old / 'state.json').write_text(json.dumps(state))
        with self.assertRaises(ShardError):
            verify_candidate(self.original, self.old)

    def test_changed_source_after_candidate_rejected(self):
        self.initial()
        self.extend()
        with self.assertRaises(ShardError):
            verify_candidate(self.original, self.old)

    def test_oversized_cycle_does_not_publish_partial(self):
        self.rows[1] = cycle('2026-10-10', '0830', size=7000)
        self.save()
        before = self.original.read_bytes()
        with self.assertRaises(ShardError):
            prepare_candidate(self.original, self.old, max_shard_bytes=1024)
        self.assertEqual(self.original.read_bytes(), before)
        self.assertFalse(self.old.exists())

    def test_existing_mirror_is_not_source(self):
        self.initial()
        before = self.original.read_bytes()
        r = plan(self.original, self.old)
        self.assertEqual(r['certificates_preserved'], 4)
        self.assertEqual(r['new_certificates'], 0)
        self.assertEqual(before, self.original.read_bytes())

    def test_empty_ledger_is_supported(self):
        self.rows = []
        self.save()
        r = prepare_candidate(self.original, self.old)
        self.assertEqual(r['certificates'], 0)
        self.assertEqual(r['shard_count'], 0)

    def test_candidate_does_not_authorize_cutover(self):
        self.initial()
        state = json.loads((self.old / 'state.json').read_bytes())
        self.assertIs(state['authorizes_replacing_report_cycles'], False)
        self.assertIs(state['production_cutover'], False)
        self.assertTrue(state['full_original_retained'])


if __name__ == '__main__':
    unittest.main()
