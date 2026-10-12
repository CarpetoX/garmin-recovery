import copy
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from report_cycle_guard_v37 import validate_certificate, CycleNotReady, SOURCES

TZ=ZoneInfo('Europe/Madrid')
NOW=datetime(2026,10,12,17,10,tzinfo=TZ)
CYCLE='2026-10-12-1645'

def fixture():
    return {'status':'ready','cycle_id':CYCLE,'verified_at':'2026-10-12T17:05:00+02:00',
            'chain':{name:{'id':i+1,'started_at':f'2026-10-12T17:0{i}:00+02:00',
                            'finished_at':f'2026-10-12T17:0{i}:30+02:00',
                            'conclusion':'publishing_in_same_job' if name=='crossfit' else 'success'}
                     for i,name in enumerate(('sync','heart','advanced','crossfit'))},
            'source_generated_at':{name:'2026-10-12T17:04:00+02:00' for name in SOURCES}}

class GuardTests(unittest.TestCase):
    def test_valid_after_1700(self):
        self.assertEqual(validate_certificate(fixture(),cycle_id=CYCLE,now=NOW)['state'],'eligible_for_report')
    def test_wrong_cycle(self):
        c=fixture();c['cycle_id']='2026-10-11-1645'
        with self.assertRaises(CycleNotReady):validate_certificate(c,cycle_id=CYCLE,now=NOW)
    def test_future_verification(self):
        c=fixture();c['verified_at']='2026-10-12T17:11:00+02:00'
        with self.assertRaises(CycleNotReady):validate_certificate(c,cycle_id=CYCLE,now=NOW)
    def test_missing_stage(self):
        c=fixture();del c['chain']['heart']
        with self.assertRaises(CycleNotReady):validate_certificate(c,cycle_id=CYCLE,now=NOW)
    def test_failed_stage(self):
        c=fixture();c['chain']['advanced']['conclusion']='failure'
        with self.assertRaises(CycleNotReady):validate_certificate(c,cycle_id=CYCLE,now=NOW)
    def test_stale_source(self):
        c=fixture();c['source_generated_at']['data_quality.json']='2026-10-11T17:04:00+02:00'
        with self.assertRaises(CycleNotReady):validate_certificate(c,cycle_id=CYCLE,now=NOW)
    def test_source_mismatch(self):
        c=fixture();data={name:{'generated_at':value} for name,value in c['source_generated_at'].items()}
        data['crossfit_insights.json']['generated_at']='2026-10-12T17:03:00+02:00'
        with self.assertRaises(CycleNotReady):validate_certificate(c,cycle_id=CYCLE,now=NOW,source_data=data)
    def test_in_progress(self):
        c=fixture();c['status']='in_progress'
        with self.assertRaises(CycleNotReady):validate_certificate(c,cycle_id=CYCLE,now=NOW)
    def test_no_delivery_claim(self):
        self.assertIn('no message delivery',validate_certificate(fixture(),cycle_id=CYCLE,now=NOW)['note'])

if __name__=='__main__':unittest.main()
