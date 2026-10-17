import copy
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from garmin_recovery.reliability_history import analyze

NOW = datetime(2026, 10, 11, 18, 20, tzinfo=timezone.utc)  # 20:20 local

def entry(cycle_id, time_str, sync=1, crossfit=2):
    return dict(cycle_id=cycle_id, slot_at='2026-10-11T16:45:00+02:00',
                ready_at=time_str, state='data_ready',
                sync_run_id=sync, crossfit_run_id=crossfit,
                notification_delivery='unverified')

class ReliabilityTest(unittest.TestCase):
    def test_recent_window_uses_only_completed_days(self):
        a = analyze({'cycles': []}, NOW)['windows']['7d']
        self.assertEqual(a['matured_scheduled_slots'], 3)
        self.assertEqual(a['not_certified_in_ledger'], 3)
        self.assertEqual(a['calendar_window_end'], '2026-10-10')
        self.assertEqual(a['status'], 'provisional_incomplete_window')
    def test_today_progress_separate_from_7_day_completed_window(self):
        entry_today=entry('2026-10-11-1645','2026-10-11T17:00:17+02:00')
        r=analyze({'cycles':[entry_today]},NOW)
        self.assertEqual(r['windows']['7d']['certified_ready'],0)
        self.assertEqual(r['today_progress']['matured_scheduled_slots'],2)
        self.assertEqual(r['today_progress']['certified_ready'],1)
        self.assertTrue(r['today_progress']['not_a_full_day_or_slo'])
    def test_post_sleep_never_in_denominator(self):
        c = entry('2026-10-11-0830-post-sleep','2026-10-11T10:45:56+02:00')
        r = analyze({'cycles': [c]}, NOW)
        self.assertEqual(r['post_sleep_entries_excluded_from_denominators'], 1)
        self.assertEqual(r['windows']['7d']['certified_ready'], 0)
    def test_report_on_time_uses_real_targets(self):
        entries = [entry('2026-10-11-1645','2026-10-11T17:00:17+02:00'),
                   entry('2026-10-10-1645','2026-10-10T17:00:12+02:00'),
                   entry('2026-10-10-2245','2026-10-10T23:11:46+02:00')]
        result = analyze({'cycles': entries}, NOW)['windows']['7d']
        self.assertEqual(result['certified_ready'],2)
        self.assertEqual(result['ready_by_report_target'],1)
        self.assertEqual(result['ready_by_target_pct_of_ready'],50)
    def test_no_cron_or_delivery_slo_fabricated(self):
        r=analyze({'cycles': [entry('2026-10-11-1645','2026-10-11T17:00:17+02:00')]},NOW)
        for w in r['windows'].values():
            self.assertIsNone(w['cron_started_pct'])
            self.assertIsNone(w['chatgpt_delivery_pct'])
            self.assertFalse(w['slo_certified'])
    def test_ready_requires_positive_run_ids_and_time(self):
        invalid = [entry('2026-10-11-1645','2026-10-11T17:00:00+02:00',sync=0),
                   entry('2026-10-11-0830','2026-10-11T07:00:00+02:00')]
        self.assertEqual(analyze({'cycles': invalid}, NOW)['windows']['7d']['certified_ready'],0)
    def test_duplicate_cycles_warn_without_double_count(self):
        one=entry('2026-10-11-1645','2026-10-11T17:01:00+02:00')
        a=analyze({'cycles':[one,copy.deepcopy(one)]},datetime(2026,10,12,1,30,tzinfo=timezone.utc))['windows']['7d']
        self.assertEqual(a['certified_ready'],1)
        self.assertEqual(a['duplicate_cycle_ids'],['2026-10-11-1645'])
    def test_inputs_not_mutated(self):
        l={'cycles':[entry('2026-10-11-1645','2026-10-11T17:01:00+02:00')]}
        before=copy.deepcopy(l)
        analyze(l,NOW)
        self.assertEqual(l,before)
    def test_denominator_zero_is_not_100_percent(self):
        t=datetime(2026,10,10,7,0,tzinfo=timezone.utc)
        a=analyze({'cycles':[]},t)['windows']['7d']
        self.assertEqual(a['matured_scheduled_slots'],0)
        self.assertIsNone(a['certified_ready_coverage_pct'])
    def test_full_seven_days_after_seventh_day_finishes(self):
        # October 10...16 inclusive mature at 01:15 local on October 17.
        t = datetime(2026,10,16,23,20,tzinfo=timezone.utc) # October 17 01:20 Madrid
        r = analyze({'cycles':[]},t)['windows']['7d']
        self.assertEqual(r['calendar_window_start'],'2026-10-10')
        self.assertEqual(r['calendar_window_end'],'2026-10-16')
        self.assertEqual(r['matured_scheduled_slots'],21)
        self.assertTrue(r['calendar_window_complete'])
        self.assertFalse(r['slo_certified'])
        self.assertEqual(r['status'],'complete_calendar_window_evidence_only')
    def test_grace_boundary_does_not_include_unmatured_yesterday(self):
        before=datetime(2026,10,16,23,10,tzinfo=timezone.utc) # October 17 01:10 local
        r=analyze({'cycles':[]},before)['windows']['7d']
        self.assertEqual(r['calendar_window_end'],'2026-10-15')
        self.assertFalse(r['calendar_window_complete'])
    def test_28day_window_requires_28_completed_days(self):
        t=datetime(2026,11,6,0,20,tzinfo=timezone.utc) # November 6 01:20 CET
        r=analyze({'cycles':[]},t)['windows']['28d']
        self.assertFalse(r['calendar_window_complete'])
        t=datetime(2026,11,7,0,20,tzinfo=timezone.utc) # November 7 01:20 CET
        r=analyze({'cycles':[]},t)['windows']['28d']
        self.assertTrue(r['calendar_window_complete'])
        self.assertFalse(r['slo_certified'])
        self.assertEqual(r['matured_scheduled_slots'],84)
    def test_reject_naive_and_invalid_ledger(self):
        with self.assertRaises(ValueError): analyze({'cycles':[]},datetime(2026,10,11,18))
        with self.assertRaises(ValueError): analyze({},NOW)
        with self.assertRaises(ValueError): analyze({'cycles':[]},NOW,grace_minutes=-1)
    def test_cli_writes_file(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'ledger.json').write_text('{"cycles":[]}',encoding='utf-8')
            cp=subprocess.run([sys.executable,'-m','garmin_recovery.reliability_history','--ledger',str(p/'ledger.json'), '--out',str(p/'report.json'), '--now','2026-10-11T18:20:00Z'], capture_output=True,text=True)
            self.assertEqual(cp.returncode,0,cp.stderr)
            self.assertEqual(json.loads((p/'report.json').read_text())['version'],'2.9.4')

if __name__=='__main__': unittest.main()
