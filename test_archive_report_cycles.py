"""Regression tests for non-destructive Garmin Recovery archive copies."""
import copy
import hashlib
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from garmin_recovery.archive_report_cycles import ArchiveError, audit, digest, prepare


def cycle(cid, month):
    snapshot = {'date': month + '-08', 'metrics': {'hrv': 45, 'sleep': None}}
    return {'cycle_id': cid, 'slot_at': month + '-08T08:30:00+02:00',
            'snapshot': snapshot, 'snapshot_sha256': digest(snapshot)}


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.path = self.root / 'report_cycles.json'
        self.rows = [cycle('2026-09-08-0830', '2026-09'),
                     cycle('2026-10-08-0830', '2026-10')]
        self.save()

    def save(self):
        self.path.write_text(json.dumps({'schema_version': 2, 'cycles': self.rows,
                                         'count': len(self.rows)}), encoding='utf-8')

    def test_audit_no_mutation(self):
        before = self.path.read_bytes()
        self.assertEqual(audit(self.path)['verified'], 2)
        self.assertEqual(self.path.read_bytes(), before)

    def test_detect_tampered_snapshot(self):
        self.rows[0]['snapshot']['metrics']['hrv'] = 90
        self.save()
        with self.assertRaisesRegex(ArchiveError, 'SHA-256'):
            audit(self.path)

    def test_detect_duplicate_cycle(self):
        self.rows.append(copy.deepcopy(self.rows[0]))
        self.save()
        with self.assertRaisesRegex(ArchiveError, 'duplicado'):
            audit(self.path)

    def test_detect_miscount(self):
        data = json.loads(self.path.read_text(encoding='utf-8'))
        data['count'] = 999
        self.path.write_text(json.dumps(data), encoding='utf-8')
        with self.assertRaisesRegex(ArchiveError, 'Contador'):
            audit(self.path)

    def test_preserve_explicit_legacy(self):
        self.rows[0] = {'cycle_id': 'legacy', 'slot_at': '2026-09-08T08:30:00+02:00',
                        'legacy_without_snapshot': True}
        self.save()
        self.assertEqual(audit(self.path)['legacy'], 1)

    def test_missing_snapshot_rejected(self):
        del self.rows[0]['snapshot']
        del self.rows[0]['snapshot_sha256']
        self.save()
        with self.assertRaisesRegex(ArchiveError, 'sin registro legacy'):
            audit(self.path)

    def test_copy_older_month_and_restore(self):
        before = self.path.read_bytes()
        output = self.root / 'archive'
        result = prepare(self.path, output, date(2026, 10, 11))
        self.assertEqual(result['status'], 'prepared_and_verified')
        self.assertEqual(result['cycles_copied'], 1)
        self.assertTrue((output / '2026-09.json').exists())
        self.assertFalse((output / '2026-10.json').exists())
        self.assertEqual(self.path.read_bytes(), before)
        manifest = json.loads((output / 'manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['source_bytes_sha256'], hashlib.sha256(before).hexdigest())

    def test_no_closed_month_no_files_created(self):
        self.rows = [self.rows[1]]
        self.save()
        result = prepare(self.path, self.root / 'archive', date(2026, 10, 11))
        self.assertEqual(result['status'], 'no_closed_months')
        self.assertFalse((self.root / 'archive').exists())

    def test_never_overwrite_an_archive(self):
        (self.root / 'archive').mkdir()
        with self.assertRaisesRegex(ArchiveError, 'existente'):
            prepare(self.path, self.root / 'archive', date(2026, 10, 11))


if __name__ == '__main__':
    unittest.main()
