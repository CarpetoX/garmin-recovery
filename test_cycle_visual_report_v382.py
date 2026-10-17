import unittest
from cycle_snapshot_report_v38 import digest, SnapshotError
from cycle_visual_report_v382 import make

CID='2026-10-12-1645'

def ledger():
    snap={'date':'2026-10-12','source_generated_at':{'daily_summary.json':'2026-10-12T17:00:00+02:00'},
          'recovery_assessment':{'status':'yellow','confidence':'medium','score':88,'current':{'hrv_ms':66},'baseline_28d':{'hrv_ms':{'median':58,'n':17}}},
          'daily':{'readiness_hybrid':{'score':74}},
          'crossfit':{'performance_report':{'window_summaries':{'recent_7d':{'sessions':9,'sessions_with_rpe':9}},'daily_chart_7d':[{'date':f'2026-10-{i:02d}','sessions':1,'srpe_from_recorded_duration':i} for i in range(6,13)],'recommendations':[{'text':'Adaptar RPE'}]}},
          'garmin':{'heart_rate_rolling':{'7d':{'daytime_avg_hr':82,'nighttime_avg_hr':62.7}}}}
    return {'cycles':[{'cycle_id':CID,'state':'data_ready','slot_at':'2026-10-12T16:45:00+02:00','source_generated_at':snap['source_generated_at'],'snapshot':snap,'snapshot_sha256':digest(snap)}]}

class Visual382Tests(unittest.TestCase):
    def test_realistic_report(self):
        s=make(ledger(),CID)
        self.assertIn('66 ms',s)
        self.assertIn('█',s)
        self.assertIn('82 lpm',s)
        self.assertIn('no se representan curvas inventadas',s)
    def test_deterministic(self):
        d=ledger()
        self.assertEqual(make(d,CID),make(d,CID))
    def test_tamper_rejected(self):
        d=ledger();d['cycles'][0]['snapshot']['recovery_assessment']['score']=100
        with self.assertRaises(SnapshotError):make(d,CID)
    def test_missing_cycle_rejected(self):
        with self.assertRaises(SnapshotError):make(ledger(),'2026-10-12-0830')
    def test_missing_chart_rejected(self):
        d=ledger();d['cycles'][0]['snapshot']['crossfit']['performance_report'].pop('daily_chart_7d');d['cycles'][0]['snapshot_sha256']=digest(d['cycles'][0]['snapshot'])
        with self.assertRaises(SnapshotError):make(d,CID)

if __name__=='__main__':unittest.main()
