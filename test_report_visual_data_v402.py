"""Focused V4.0.2 data coverage, provenance and omission tests."""
import copy
import unittest
from datetime import date

from cycle_snapshot_report_v38 import digest
from test_garmin_report_v40 import fixture
from report_visual_data_v402 import (verified_days, series, week_load, heatmap, intensity,
                                     verified_strength, stage_segments, exercise_group, valid_day)


def resign(row):
    row['snapshot_sha256']=digest(row['snapshot'])


def add_day(ledger, iso, score=75, confirmed=True):
    row=copy.deepcopy(ledger['cycles'][0])
    row['cycle_id']=iso+'-2245'
    row['slot_at']=iso+'T22:45:00+02:00'
    row['ready_at']=iso+'T23:00:00+02:00'
    snap=row['snapshot']
    snap['date']=iso
    snap['recovery_assessment']['current']['date']=iso
    snap['recovery_assessment']['score']=score
    snap['garmin']['heart_rate_today']['date']=iso
    snap['morning_sleep']={'state':'confirmed_ready' if confirmed else 'pending', 'evidence_valid':confirmed}
    snap['garmin']['body_battery_today']['endTimestampLocal']=iso+'T22:30:00+02:00'
    resign(row)
    ledger['cycles'].append(row)
    return row


class DataV402Tests(unittest.TestCase):
    def setUp(self):
        self.ledger,self.cid=fixture()
        self.anchor=date.fromisoformat(self.cid[:10])

    def test_28_day_partial_coverage(self):
        data,bad=verified_days(self.ledger,self.cid)
        self.assertEqual(len(data),1)
        self.assertEqual(bad,[])
        self.assertEqual(len(heatmap(data,self.anchor,[])),28)
        self.assertEqual(sum(x['state']=='missing' for x in heatmap(data,self.anchor,[])),27)

    def test_deduplicates_latest_cycle_per_day(self):
        row=copy.deepcopy(self.ledger['cycles'][0]);row['cycle_id']='2026-10-12-1645'
        row['slot_at']='2026-10-12T16:45:00+02:00'
        row['ready_at']='2026-10-12T17:00:00+02:00'
        row['snapshot']['recovery_assessment']['score']=48
        resign(row)
        self.ledger['cycles'].append(row)
        data,_=verified_days(self.ledger,self.cid)
        self.assertEqual(data[self.anchor]['recovery_assessment']['score'],88)

    def test_no_double_count_with_many_snapshots(self):
        for n in range(5):
            row=copy.deepcopy(self.ledger['cycles'][0]);row['cycle_id']='2026-10-11-0'+str(n)+'30'
            row['slot_at']='2026-10-11T0'+str(n)+':30:00+02:00'
            row['ready_at']='2026-10-11T0'+str(n)+':40:00+02:00'
            row['snapshot']['date']='2026-10-11'
            row['snapshot']['recovery_assessment']['current']['date']='2026-10-11'
            row['snapshot']['garmin']['heart_rate_today']['date']='2026-10-11'
            resign(row);self.ledger['cycles'].append(row)
        days,_=verified_days(self.ledger,self.cid)
        self.assertEqual(len(days),2)

    def test_quarantine_tampered_history(self):
        row=add_day(self.ledger,'2026-10-11')
        row['snapshot']['recovery_assessment']['score']=999
        days,bad=verified_days(self.ledger,self.cid)
        self.assertEqual(len(days),1)
        self.assertEqual(bad,['2026-10-11-2245'])

    def test_pending_sleep_hides_hrv_and_recovery(self):
        add_day(self.ledger,'2026-10-11',confirmed=False)
        days,_=verified_days(self.ledger,self.cid)
        self.assertEqual(series(days,self.anchor,'hrv')[-2]['value'],None)
        self.assertEqual(series(days,self.anchor,'recovery')[-2]['value'],None)

    def test_stale_current_hides_recovery(self):
        s=self.ledger['cycles'][0]['snapshot']
        s['recovery_assessment']['current']['date']='2026-10-11'
        resign(self.ledger['cycles'][0])
        days,_=verified_days(self.ledger,self.cid)
        self.assertIsNone(series(days,self.anchor,'hrv')[-1]['value'])

    def test_day_hr_requires_same_date(self):
        s=self.ledger['cycles'][0]['snapshot'];s['garmin']['heart_rate_today']['date']='2026-10-11'
        resign(self.ledger['cycles'][0]);days,_=verified_days(self.ledger,self.cid)
        self.assertIsNone(series(days,self.anchor,'rhr')[-1]['value'])

    def test_battery_requires_measurement_date(self):
        days,_=verified_days(self.ledger,self.cid)
        self.assertIsNone(series(days,self.anchor,'body_battery')[-1]['value'])
        self.ledger['cycles'][0]['snapshot']['garmin']['body_battery_today']['endTimestampLocal']='2026-10-12T22:45:00+02:00'
        resign(self.ledger['cycles'][0]);days,_=verified_days(self.ledger,self.cid)
        self.assertEqual(series(days,self.anchor,'body_battery')[-1]['value'],31)

    def test_week_load_correct_dates(self):
        days,_=verified_days(self.ledger,self.cid)
        self.assertEqual(len(week_load(days[self.anchor],self.anchor)),7)
        self.ledger['cycles'][0]['snapshot']['crossfit']['performance_report']['daily_chart_7d'][1]['date']='2026-10-25'
        resign(self.ledger['cycles'][0]);days,_=verified_days(self.ledger,self.cid)
        self.assertEqual(week_load(days[self.anchor],self.anchor),[])

    def test_training_zero_not_confused_with_missing(self):
        days,_=verified_days(self.ledger,self.cid)
        load=[{'date':'2026-10-12','value':0}]
        today=heatmap(days,self.anchor,load)[-1]
        self.assertEqual(today['load'],0)
        self.assertEqual(heatmap(days,self.anchor,[])[-1]['load'],None)

    def test_recovery_missing_day_does_not_get_past_score(self):
        days,_=verified_days(self.ledger,self.cid)
        self.assertIsNone(heatmap(days,self.anchor,[])[-2]['recovery_score'])

    def test_no_fabricated_strength_from_aggregate(self):
        days,_=verified_days(self.ledger,self.cid)
        strength,skipped=verified_strength(days,self.anchor)
        self.assertEqual(strength,{})
        self.assertEqual(skipped,0)

    def test_verified_manual_barbell_strength(self):
        s=self.ledger['cycles'][0]['snapshot'];s['crossfit']['activities_today']=[{
            'date':'2026-10-12','activity_id':101,'manual_strength_sets':[
                {'exercise':'back squat','equipment':'barbell','weight_kg':165,'reps':2,'verified':True},
                {'exercise':'back squat','equipment':'machine','weight_kg':300,'reps':2,'verified':True},
                {'exercise':'bench press','equipment':'barbell','weight_kg':95,'reps':5,'verified':False},
            ]}]
        resign(self.ledger['cycles'][0]);days,_=verified_days(self.ledger,self.cid)
        strength,skipped=verified_strength(days,self.anchor)
        self.assertEqual(len(strength['Sentadilla trasera']),1)
        self.assertEqual(strength['Sentadilla trasera'][0]['kg'],165)
        self.assertEqual(skipped,2)

    def test_dumbbell_separate_per_hand_and_machine_id(self):
        s=self.ledger['cycles'][0]['snapshot'];s['crossfit']['activities_today']=[{
            'date':'2026-10-12','activity_id':101,'manual_strength_sets':[
                {'exercise':'bench press','equipment':'barbell','weight_kg':100,'reps':5,'verified':True},
                {'exercise':'bench press','equipment':'dumbbell','weight_basis':'per_hand','weight_kg':35,'reps':8,'verified':True},
                {'exercise':'bench press','equipment':'dumbbell','weight_kg':50,'reps':8,'verified':True},
                {'exercise':'bench press','equipment':'machine','machine_id':'gymA_chest','weight_kg':65,'reps':8,'verified':True},
                {'exercise':'bench press','equipment':'machine','weight_kg':90,'reps':8,'verified':True},
            ]}]
        resign(self.ledger['cycles'][0]);days,_=verified_days(self.ledger,self.cid)
        strength,skipped=verified_strength(days,self.anchor)
        self.assertEqual(len(strength),3)
        self.assertIn('Press banca · mancuerna (por mano)',strength)
        self.assertIn('Press banca · máquina gymA_chest',strength)
        self.assertEqual(skipped,2)

    def test_no_garmin_guess_for_strength(self):
        s=self.ledger['cycles'][0]['snapshot'];s['garmin']['extended_today']['activity_metrics']={'activities':[{'exercise_sets':{'sets':[{'exercise':'SQUAT','weight_kg':210,'reps':2}]}}]}
        resign(self.ledger['cycles'][0]);days,_=verified_days(self.ledger,self.cid)
        self.assertEqual(verified_strength(days,self.anchor)[0],{})

    def test_intensity_requires_full_five_zone_values(self):
        s=self.ledger['cycles'][0]['snapshot'];s['daily']['training_today']={'hr_zone_times_secs':[60,120,180,90,30],'session_type_distribution':{'strength':2}}
        resign(self.ledger['cycles'][0]);days,_=verified_days(self.ledger,self.cid)
        values=intensity(days,self.anchor)
        self.assertEqual(values['zone_minutes'],[1,2,3,1.5,0.5])
        self.assertEqual(values['zone_days'],1)
        self.assertEqual(values['type_counts'],{'strength':2})
        s['daily']['training_today']['hr_zone_times_secs']=[60,None,90]
        resign(self.ledger['cycles'][0]);days,_=verified_days(self.ledger,self.cid)
        self.assertEqual(intensity(days,self.anchor)['zone_days'],0)

    def test_sleep_segments_require_actual_intervals(self):
        s=self.ledger['cycles'][0]['snapshot']
        curr=s['recovery_assessment']['current']
        self.assertEqual(stage_segments(s,curr,True),[])
        s['garmin']['extended_today']['sleep_detail']['stage_segments']=[{'start':'2026-10-12T00:09:29+02:00','end':'2026-10-12T00:29:29+02:00','stage':'deep'}, {'start':'2026-10-12T00:29:29+02:00','end':'2026-10-12T00:59:29+02:00','stage':'light'}]
        self.assertEqual(len(stage_segments(s,curr,True)),2)
        self.assertEqual(stage_segments(s,curr,False),[])

    def test_overlapping_sleep_segments_rejected(self):
        s=self.ledger['cycles'][0]['snapshot'];curr=s['recovery_assessment']['current']
        s['garmin']['extended_today']['sleep_detail']['stage_segments']=[{'start':'2026-10-12T00:09:29+02:00','end':'2026-10-12T00:40:00+02:00','stage':'deep'}, {'start':'2026-10-12T00:30:00+02:00','end':'2026-10-12T01:00:00+02:00','stage':'rem'}]
        self.assertEqual(stage_segments(s,curr,True),[])

    def test_bad_dates(self):
        self.assertIsNone(valid_day('2026-02-30'))
        self.assertIsNone(valid_day('2026-10-12<script>'))
        self.assertIsNone(exercise_group('random exercise'))


if __name__=='__main__':unittest.main()
