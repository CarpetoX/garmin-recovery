import copy
import unittest
from cycle_snapshot_report_v38 import digest, SnapshotError
from cycle_visual_report_v381 import make

CID = '2026-10-12-1645'
SNAP = {'date': '2026-10-12', 'source_generated_at': {'crossfit_insights.json': '2026-10-12T17:00:33+02:00'},
        'recovery_assessment': {'status': 'yellow', 'current': {'hrv_ms': 66}},
        'crossfit': {'performance_report': {'window_summaries': {'recent_7d': {'sessions': 9}},
                                          'daily_chart_7d': [{'date': f'2026-10-{i:02d}', 'sessions': 1} for i in range(6, 13)]}}}
ROW = {'cycle_id': CID, 'slot_at': '2026-10-12T16:45:00+02:00', 'state': 'data_ready',
       'source_generated_at': SNAP['source_generated_at'], 'snapshot': SNAP, 'snapshot_sha256': digest(SNAP)}

class VisualReportTests(unittest.TestCase):
    def test_renders_historical_values(self):
        out = make({'cycles': [ROW]}, CID)
        self.assertIn('66 ms', out)
        self.assertIn('9 · Con RPE', out)
        self.assertIn('2026-10-06', out)

    def test_no_live_files(self):
        out = make({'cycles': [ROW]}, CID)
        self.assertIn('sin datos posteriores', out)
        self.assertIn('no acredita entrega', out)

    def test_rejects_modified_snapshot(self):
        row = copy.deepcopy(ROW)
        row['snapshot']['recovery_assessment']['current']['hrv_ms'] = 88
        with self.assertRaises(SnapshotError):
            make({'cycles': [row]}, CID)

    def test_rejects_missing_chart(self):
        row = copy.deepcopy(ROW)
        row['snapshot']['crossfit']['performance_report'].pop('daily_chart_7d')
        row['snapshot_sha256'] = digest(row['snapshot'])
        with self.assertRaises(SnapshotError):
            make({'cycles': [row]}, CID)

    def test_rejects_ambiguous_cycle(self):
        with self.assertRaises(SnapshotError):
            make({'cycles': [ROW, ROW]}, CID)

if __name__ == '__main__':
    unittest.main()
