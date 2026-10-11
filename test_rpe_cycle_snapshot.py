"""Tests for RPE same-cycle lineage, tampering, duplicates and staleness."""
import copy
import unittest
from datetime import datetime, timedelta, timezone
from rpe_cycle_snapshot import (COLUMNS, SnapshotError, canonical_digest,
                                validate_rows, verified_snapshot)


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 11, 13, 7, tzinfo=timezone.utc)
        self.rows = [dict(zip(COLUMNS, ['2026-10-11', 'i196047961', 'Fuerza', '6',
                                        '', 'Sentadilla', '2026-10-11', '{}']))]
        self.snapshot = {'advanced_run_id': '12345', 'source_rows_AH': self.rows,
                         'source_rows_sha256': canonical_digest(self.rows),
                         'source_fetched_at': (self.now - timedelta(minutes=1)).isoformat(),
                         'remote_rows_loaded': 1, 'remote_latest_date': '2026-10-11'}
        self.advanced = {'generated_at': (self.now - timedelta(seconds=10)).isoformat(),
                         'rpe_feedback': {'remote_rows_loaded': 1,
                                          'remote_latest_date': '2026-10-11',
                                          'remote_fetch_error': None,
                                          'advanced_run_id': '12345',
                                          'source_rows_sha256': canonical_digest(self.rows)}}

    def ok(self, snapshot=None, advanced=None, run_id='12345', now=None):
        return verified_snapshot(snapshot or self.snapshot, advanced or self.advanced,
                                 run_id, now or self.now)

    def test_same_parent_snapshot_passes(self):
        self.assertEqual(self.ok(), self.rows)

    def test_other_parent_fails_closed(self):
        with self.assertRaisesRegex(SnapshotError, 'otra ejecución'):
            self.ok(run_id='12346')

    def test_tampered_rows_rejected(self):
        x = copy.deepcopy(self.snapshot)
        x['source_rows_AH'][0]['RPE'] = '9'
        with self.assertRaisesRegex(SnapshotError, 'SHA-256'):
            self.ok(snapshot=x)

    def test_stale_snapshot_rejected(self):
        with self.assertRaisesRegex(SnapshotError, 'antigua'):
            self.ok(now=self.now + timedelta(minutes=41))

    def test_duplicates_not_silently_reduced(self):
        with self.assertRaisesRegex(SnapshotError, 'duplicada'):
            validate_rows(self.rows + self.rows)

    def test_multiple_blocks_same_activity_allowed(self):
        second = copy.deepcopy(self.rows[0])
        second['Actividad'] = 'Curl femoral'
        self.assertEqual(len(validate_rows(self.rows + [second])), 2)

    def test_conflicting_rpe_same_activity_rejected(self):
        second = copy.deepcopy(self.rows[0])
        second['Actividad'] = 'Curl femoral'
        second['RPE'] = '9'
        with self.assertRaisesRegex(SnapshotError, 'contradictorio'):
            validate_rows(self.rows + [second])

    def test_missing_id_rejected(self):
        x = copy.deepcopy(self.rows)
        x[0]['ID actividad'] = ''
        with self.assertRaisesRegex(SnapshotError, 'ID actividad'):
            validate_rows(x)

    def test_mismatched_advanced_count_rejected(self):
        x = copy.deepcopy(self.advanced)
        x['rpe_feedback']['remote_rows_loaded'] = 2
        with self.assertRaisesRegex(SnapshotError, 'número de filas'):
            self.ok(advanced=x)

    def test_advanced_from_other_run_rejected(self):
        x = copy.deepcopy(self.advanced)
        x['rpe_feedback']['advanced_run_id'] = 'another'
        with self.assertRaisesRegex(SnapshotError, 'otra ejecución'):
            self.ok(advanced=x)

    def test_advanced_hash_mismatch_rejected(self):
        x = copy.deepcopy(self.advanced)
        x['rpe_feedback']['source_rows_sha256'] = 'f' * 64
        with self.assertRaisesRegex(SnapshotError, 'otra instantánea'):
            self.ok(advanced=x)

    def test_missing_parent_id_rejected(self):
        with self.assertRaisesRegex(SnapshotError, 'Falta ID'):
            self.ok(run_id='')

    def test_parent_advanced_event_provenance(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        import json
        from rpe_cycle_snapshot import parent_run_id_from_event
        with TemporaryDirectory() as d:
            p = Path(d) / 'event.json'
            p.write_text(json.dumps({'workflow_run': {
                'id': 12345, 'name': 'Garmin Advanced Analytics',
                'conclusion': 'success'}}), encoding='utf-8')
            self.assertEqual(parent_run_id_from_event(str(p)), '12345')

    def test_parent_event_from_other_workflow_rejected(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        import json
        from rpe_cycle_snapshot import parent_run_id_from_event
        with TemporaryDirectory() as d:
            p = Path(d) / 'event.json'
            p.write_text(json.dumps({'workflow_run': {
                'id': 12345, 'name': 'Garmin Recovery Sync',
                'conclusion': 'success'}}), encoding='utf-8')
            with self.assertRaisesRegex(SnapshotError, 'padre'):
                parent_run_id_from_event(str(p))

    def test_parent_event_failed_run_rejected(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        import json
        from rpe_cycle_snapshot import parent_run_id_from_event
        with TemporaryDirectory() as d:
            p = Path(d) / 'event.json'
            p.write_text(json.dumps({'workflow_run': {
                'id': 12345, 'name': 'Garmin Advanced Analytics',
                'conclusion': 'failure'}}), encoding='utf-8')
            with self.assertRaisesRegex(SnapshotError, 'no finalizó'):
                parent_run_id_from_event(str(p))



if __name__ == '__main__':
    unittest.main()
