import unittest
from datetime import date
from training_trends_v31 import trend


class TrendsV31Tests(unittest.TestCase):
    def base(self):
        return {'generated_at':'2026-10-11T15:01:00+02:00', 'sheet_source':'cycle_snapshot',
                'activities':[{'activity_id':'a','date':'2026-10-11','rpe_used':6,
                               'recorded_minutes':30,'srpe_using_recorded_minutes':180},
                              {'activity_id':'b','date':'2026-10-10','rpe_used':8,
                               'recorded_minutes':10,'srpe_using_recorded_minutes':80}],
                'muscle_load':{'strength_exercises':[
                    {'date':'2026-10-11','activity_id':'a','exercise':'Sentadilla trasera',
                     'equipment':'barbell','load_unit':'kg_total_barra',
                     'peak_declared_load_kg':150,'verified_volume_kg':4260,'known_sets':9,'volume_complete':True},
                    {'date':'2026-10-10','activity_id':'b','exercise':'Sentadilla trasera',
                     'equipment':'machine_stack','load_unit':'kg_indicado_maquina',
                     'peak_declared_load_kg':120,'verified_volume_kg':4320,'known_sets':4,'volume_complete':True}]}}

    def test_separate_exercise_equipment(self):
        r=trend(self.base(),date(2026,10,11))
        self.assertEqual(len(r['strength_by_exact_equipment']),2)
        self.assertTrue(all(g['progression_status']=='insufficient_repeats' for g in r['strength_by_exact_equipment']))

    def test_no_fabricated_1rm(self):
        r=trend(self.base(),date(2026,10,11))
        self.assertTrue(all(g['estimated_1rm_inferred'] is False for g in r['strength_by_exact_equipment']))

    def test_recorded_s_rpe_explicit(self):
        r=trend(self.base(),date(2026,10,11))
        self.assertEqual(r['windows']['3d']['srpe_recorded_duration_sum'],260)
        self.assertEqual(r['windows']['7d']['mean_session_rpe'],7)

    def test_no_workout_day_is_not_verified_rest(self):
        r=trend(self.base(),date(2026,10,11))
        empty=[d for d in r['daily_chart_28d'] if d['date']=='2026-10-09'][0]
        self.assertTrue(empty['no_recorded_sessions_not_proof_of_rest'])

    def test_missing_rpe_not_replaced(self):
        data=self.base()
        data['activities'][0]['rpe_used']=None
        r=trend(data,date(2026,10,11))
        self.assertEqual(r['windows']['7d']['recorded_sessions_with_rpe'],1)

    def test_outlier_machines_not_merged(self):
        data=self.base()
        data['muscle_load']['strength_exercises'][1]['peak_declared_load_kg']=1000
        r=trend(data,date(2026,10,11))
        bar=[g for g in r['strength_by_exact_equipment'] if g['equipment']=='barbell'][0]
        self.assertEqual(bar['points'][0]['observed_peak_kg'],150)

    def test_future_activity_excluded(self):
        data=self.base()
        data['activities'][0]['date']='2026-10-12'
        r=trend(data,date(2026,10,11))
        self.assertEqual(r['windows']['3d']['recorded_sessions'],1)

    def test_invalid_source_rejected(self):
        with self.assertRaises(ValueError):
            trend({},date(2026,10,11))

    def test_duplicate_same_equipment_repeat_is_descriptive(self):
        data=self.base()
        data['muscle_load']['strength_exercises'][1].update(equipment='barbell',load_unit='kg_total_barra')
        r=trend(data,date(2026,10,11))
        self.assertEqual(len(r['strength_by_exact_equipment']),1)
        self.assertEqual(r['strength_by_exact_equipment'][0]['progression_status'],'descriptive_only')


# V3.2 tests are hosted here so the EXISTING Garmin CI test invocation
# (python -m unittest ... test_training_trends_v31 ...) runs them automatically.
from performance_report_v32 import build_report


class PerformanceReportV32Tests(unittest.TestCase):
    TODAY=date(2026,10,11)

    def make(self, activities=None, strength=None, wellness=None, daily=None):
        crossfit={'sheet_source':'cycle_snapshot','generated_at':'2026-10-11T21:05:00+02:00',
            'activities':activities if activities is not None else [],
            'muscle_load':{'strength_exercises':strength if strength is not None else []}}
        return build_report(crossfit, wellness if wellness is not None else [],
                            daily if daily is not None else {}, self.TODAY)

    @staticmethod
    def act(aid, day, rpe=6, minutes=30, trimp=35):
        return {'activity_id':aid,'date':day,'name':'Fuerza',
                'rpe_used':rpe,'recorded_minutes':minutes,
                'srpe_using_recorded_minutes':rpe*minutes if rpe is not None else None,
                'internal_load_not_additive':{'trimp':trimp},
                'heart_rate':{'average':118}}

    def test_new_report_28_daily_chart_rows(self):
        r=self.make([self.act('a','2026-10-11')])
        self.assertEqual(len(r['charts']['daily_28d']),28)
        self.assertEqual(r['charts']['daily_28d'][-1]['date'],'2026-10-11')
        self.assertTrue(r['charts']['daily_28d'][0]['missing_training_entry_is_not_rest'])
        self.assertIsNone(r['charts']['daily_28d'][0]['trimp'])

    def test_no_fake_7_day_comparison(self):
        r=self.make([self.act('a','2026-10-11')])
        self.assertEqual(r['window_comparison']['current_vs_previous_7d']['comparison_status'],
                         'insufficient_sessions_in_either_week')
        self.assertIsNone(r['window_comparison']['current_vs_previous_7d']['srpe_proxy_delta_pct'])

    def test_two_weeks_with_three_complete_sessions_allow_descriptive_delta(self):
        dates=['2026-10-11','2026-10-10','2026-10-09',
               '2026-10-04','2026-10-03','2026-10-02']
        r=self.make([self.act(str(i),d,6,30,35) for i,d in enumerate(dates)])
        cmp=r['window_comparison']['current_vs_previous_7d']
        self.assertEqual(cmp['comparison_status'],'descriptive_only')
        self.assertEqual(cmp['srpe_proxy_delta_pct'],0.0)
        self.assertEqual(cmp['trimp_delta_pct'],0.0)
        self.assertTrue(cmp['load_metrics_are_not_additive'])

    def test_incomplete_rpe_disables_srpe_comparison(self):
        dates=['2026-10-11','2026-10-10','2026-10-09',
               '2026-10-04','2026-10-03','2026-10-02']
        acts=[self.act(str(i),d) for i,d in enumerate(dates)]
        acts[0]['rpe_used']=None
        acts[0]['srpe_using_recorded_minutes']=None
        r=self.make(acts)
        self.assertIsNone(r['window_comparison']['current_vs_previous_7d']['srpe_proxy_delta_pct'])
        self.assertEqual(r['window_comparison']['windows']['7d']['sessions_with_rpe'],2)

    def test_machine_bar_and_load_units_separate(self):
        s=[{'date':'2026-10-11','activity_id':'a','exercise':'sentadilla trasera',
            'equipment':'barbell','load_unit':'kg_total_barra','peak_declared_load_kg':150},
           {'date':'2026-10-11','activity_id':'b','exercise':'sentadilla trasera',
            'equipment':'machine_stack','load_unit':'kg_indicado_maquina','peak_declared_load_kg':150},
           {'date':'2026-10-10','activity_id':'c','exercise':'sentadilla trasera',
            'equipment':'barbell','load_unit':'kg_por_pierna','peak_declared_load_kg':150}]
        r=self.make(strength=s)
        self.assertEqual(len(r['strength']['exact_exercise_groups']),3)
        self.assertFalse(r['strength']['mixed_equipment_tonnage_comparable'])

    def test_strength_change_is_only_descriptive(self):
        s=[{'date':'2026-10-10','exercise':'sentadilla trasera','activity_id':'a',
            'equipment':'barbell','load_unit':'kg_total_barra','peak_declared_load_kg':100,
            'verified_volume_kg':1200,'volume_complete':True},
           {'date':'2026-10-11','exercise':'sentadilla trasera','activity_id':'b',
            'equipment':'barbell','load_unit':'kg_total_barra','peak_declared_load_kg':150,
            'verified_volume_kg':2000,'volume_complete':True}]
        r=self.make(strength=s)
        x=r['strength']['exact_exercise_groups'][0]
        self.assertEqual(x['observed_peak_change_kg'],50)
        self.assertEqual(x['peak_change_interpretation'],'descriptive_only_not_strength_gain_or_1rm')
        self.assertFalse(r['strength']['est_1rm_from_session_rpe'])

    def test_volume_same_equipment_only_and_incomplete_disables_comparison(self):
        a={'exercise':'sentadilla trasera','equipment':'barbell',
           'load_unit':'kg_total_barra','peak_declared_load_kg':100,
           'verified_volume_kg':1000,'volume_complete':True}
        days=['2026-10-11','2026-10-10','2026-10-04','2026-10-03']
        s=[{**a,'date':d,'activity_id':str(i)} for i,d in enumerate(days)]
        g=self.make(strength=s)['strength']['exact_exercise_groups'][0]
        self.assertEqual(g['volume_windows']['7d']['verified_volume_kg'],2000)
        self.assertEqual(g['volume_change_7d_vs_previous_pct'],0)
        s[0]['volume_complete']=False
        g=self.make(strength=s)['strength']['exact_exercise_groups'][0]
        self.assertIsNone(g['volume_windows']['7d']['verified_volume_kg'])
        self.assertIsNone(g['volume_change_7d_vs_previous_pct'])

    def test_unconfirmed_laterality_never_counts_complete_volume(self):
        s=[{'date':'2026-10-11','exercise':'curl femoral unilateral','activity_id':'a',
            'equipment':'machine_stack','load_unit':'kg_indicado_maquina',
            'peak_declared_load_kg':40,'verified_volume_kg':2560,
            'volume_complete':True,'laterality_unconfirmed':True}]
        x=self.make(strength=s)['strength']['exact_exercise_groups'][0]['points'][0]
        self.assertIsNone(x['verified_volume_kg'])
        self.assertEqual(x['partial_volume_lower_bound_kg'],2560)

    def test_confirmed_unilateral_uses_recorded_volume_without_doubling(self):
        s=[{'date':'2026-10-11','exercise':'curl femoral unilateral','activity_id':'a',
            'equipment':'machine_stack','load_unit':'kg_indicado_maquina',
            'peak_declared_load_kg':40,'verified_volume_kg':2560,
            'volume_complete':True,'laterality_unconfirmed':False}]
        x=self.make(strength=s)['strength']['exact_exercise_groups'][0]['points'][0]
        self.assertEqual(x['verified_volume_kg'],2560)

    def test_recovery_comparison_requires_4_days_each_week(self):
        w=[{'id':'2026-10-11','hrv':61,'restingHR':48,'sleepSecs':27000,'sleepScore':81},
           {'id':'2026-10-10','hrv':62,'restingHR':49,'sleepSecs':25200}]
        r=self.make(wellness=w)
        a=r['recovery']['7d_vs_previous_7d']
        self.assertIsNone(a['hrv']['delta_mean'])
        self.assertFalse(a['hrv']['comparison_supported'])

    def test_supported_recovery_delta_with_4_days_both_sides(self):
        w=[]
        for day in ['2026-10-11','2026-10-10','2026-10-09','2026-10-08']:
            w.append({'id':day,'hrv':70,'restingHR':48,'sleepSecs':28800})
        for day in ['2026-10-04','2026-10-03','2026-10-02','2026-10-01']:
            w.append({'id':day,'hrv':60,'restingHR':50,'sleepSecs':25200})
        r=self.make(wellness=w)
        self.assertEqual(r['recovery']['7d_vs_previous_7d']['hrv']['delta_mean'],10)
        self.assertEqual(r['recovery']['7d_vs_previous_7d']['sleep_hours']['delta_mean'],1)

    def test_old_daily_summary_does_not_become_today_readiness(self):
        r=self.make(daily={'date':'2026-10-10','readiness_model':{'score':99,'status':'green'}})
        self.assertIsNone(r['readiness_today']['score'])
        self.assertEqual(r['readiness_today']['status'],'unavailable')

    def test_future_and_duplicate_ids_not_double_counted(self):
        acts=[self.act('a','2026-10-11'),self.act('a','2026-10-11'),
              self.act('f','2026-10-12')]
        r=self.make(acts)
        self.assertEqual(r['window_comparison']['windows']['7d']['sessions'],1)
        self.assertEqual(r['provenance']['deduplicated_activity_ids'],1)

    def test_rpe_hr_pairs_no_correlation_claim(self):
        r=self.make([self.act('a','2026-10-11')])
        self.assertEqual(len(r['charts']['rpe_vs_garmin_hr']),1)
        self.assertIn('not_correlation',r['charts']['rpe_hr_scatter_interpretation'])

    def test_invalid_data_rejected(self):
        with self.assertRaises(ValueError):
            build_report({},[],{},self.TODAY)

    def test_wellness_absent_not_zero(self):
        r=self.make()
        self.assertIsNone(r['recovery']['7d']['hrv']['mean'])
        self.assertEqual(r['recovery']['7d']['hrv']['days'],0)
        self.assertIsNone(r['charts']['daily_28d'][-1]['sleep_hours'])


# V3.3 tests: loaded by the already-configured Garmin CI test_training_trends_v31 suite.
import copy
import json
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from validate_performance_v33 import audit, main


class PerformanceContractV33Tests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 11, 21, 12, tzinfo=ZoneInfo('Europe/Madrid'))
        self.day = self.now.date()
        self.crossfit = {
            'generated_at': datetime(2026, 10, 11, 21, 10,
                                     tzinfo=ZoneInfo('Europe/Madrid')).isoformat(),
            'sheet_source': 'cycle_snapshot',
            'activities': [
                {'activity_id': 'a1', 'date': self.day.isoformat(), 'name': 'Fuerza',
                 'rpe_used': 6, 'recorded_minutes': 40,
                 'srpe_using_recorded_minutes': 240,
                 'heart_rate': {'average': 118},
                 'internal_load_not_additive': {'trimp': 25.2}},
            ],
            'muscle_load': {'strength_exercises': []},
        }
        self.candidate = trend(self.crossfit, self.day)
        self.candidate['performance_report_v32'] = build_report(
            self.crossfit, [], {}, self.day)
        self.candidate['generated_at'] = datetime(2026, 10, 11, 19, 11,
                                                  tzinfo=timezone.utc).isoformat()

    def codes(self, modify=None, crossfit=None, now=None):
        candidate = copy.deepcopy(self.candidate)
        if modify:
            modify(candidate)
        return audit(candidate, crossfit or self.crossfit, now or self.now)

    def test_valid_provisional_report_is_accepted(self):
        self.assertEqual(self.codes(), [])

    def test_missing_v32_is_failure(self):
        self.assertIn('performance_v32_missing', self.codes(lambda c: c.pop('performance_report_v32')))

    def test_empty_candidate_rejected(self):
        self.assertIn('wrong_top_level_contract', audit({}, self.crossfit, self.now))

    def test_crossfit_generated_at_mismatch(self):
        self.assertIn('source_timestamp_mismatch',
                      self.codes(lambda c: c.update(source_generated_at='2026-10-11T20:00:00+02:00')))

    def test_v32_provenance_mismatch(self):
        self.assertIn('performance_v32_source_mismatch',
                      self.codes(lambda c: c['performance_report_v32']['provenance'].update(
                          crossfit_generated_at='2026-10-11T20:00:00+02:00')))

    def test_old_source_rejected_even_when_json_present(self):
        self.assertIn('crossfit_source_not_fresh', self.codes(now=self.now + timedelta(hours=2)))

    def test_future_clock_rejected(self):
        self.assertIn('crossfit_source_not_fresh', self.codes(now=self.now - timedelta(minutes=10)))

    def test_wrong_local_day_rejected(self):
        self.assertIn('report_local_day_invalid', self.codes(lambda c: c.update(as_of_date='2026-10-10')))

    def test_corrupted_v31_chart_rejected(self):
        self.assertIn('v31_chart_28d_missing', self.codes(lambda c: c['daily_chart_28d'].pop()))

    def test_corrupted_v32_chart_dates_rejected(self):
        self.assertIn('performance_v32_chart_dates_inconsistent',
                      self.codes(lambda c: c['performance_report_v32']['charts']['daily_28d'][0].update(
                          date='2026-09-20')))

    def test_missing_rpe_is_valid_if_explicitly_null(self):
        self.crossfit['activities'][0]['rpe_used'] = None
        self.crossfit['activities'][0]['srpe_using_recorded_minutes'] = None
        self.candidate = trend(self.crossfit, self.day)
        self.candidate['performance_report_v32'] = build_report(self.crossfit, [], {}, self.day)
        self.candidate['generated_at'] = '2026-10-11T19:11:00+00:00'
        self.assertEqual(self.codes(), [])

    def test_no_sessions_is_valid_not_fake_zero_historical_activity(self):
        self.crossfit['activities'] = []
        self.candidate = trend(self.crossfit, self.day)
        self.candidate['performance_report_v32'] = build_report(self.crossfit, [], {}, self.day)
        self.candidate['generated_at'] = '2026-10-11T19:11:00+00:00'
        self.assertEqual(self.codes(), [])

    def test_machine_and_bodyweight_safety_required(self):
        self.assertIn('performance_v32_strength_guardrails_missing', self.codes(
            lambda c: c['performance_report_v32']['strength'].update(
                mixed_equipment_tonnage_comparable=True)))

    def test_weekly_load_guardrail_required(self):
        self.assertIn('performance_v32_load_guardrail_missing', self.codes(
            lambda c: c['performance_report_v32']['window_comparison']['current_vs_previous_7d'].update(
                load_metrics_are_not_additive=False)))

    def test_cli_fails_if_candidate_missing_without_modifying_previous_good(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            existing = root / 'published.json'
            existing.write_bytes(b'{"last_good":true}')
            source = root / 'crossfit.json'
            source.write_text(json.dumps(self.crossfit), encoding='utf-8')
            self.assertEqual(main(['--candidate', str(root / 'missing.json'), '--crossfit', str(source)]), 1)
            self.assertEqual(existing.read_bytes(), b'{"last_good":true}')

    def test_cli_fails_on_nonfinite_json(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            candidate = root / 'candidate.json'
            candidate.write_text('{"generated_at":NaN}', encoding='utf-8')
            source = root / 'crossfit.json'
            source.write_text(json.dumps(self.crossfit), encoding='utf-8')
            self.assertEqual(main(['--candidate', str(candidate), '--crossfit', str(source)]), 1)

    def test_cli_accepts_valid_generated_candidate(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            candidate = root / 'candidate.json'
            source = root / 'crossfit.json'
            # Replace both source and candidate timestamps with the current clock.
            current = datetime.now(ZoneInfo('Europe/Madrid'))
            self.crossfit['generated_at'] = (current - timedelta(minutes=2)).isoformat()
            self.crossfit['activities'][0]['date'] = current.date().isoformat()
            valid = trend(self.crossfit, current.date())
            valid['performance_report_v32'] = build_report(self.crossfit, [], {}, current.date())
            valid['generated_at'] = current.astimezone(timezone.utc).isoformat()
            candidate.write_text(json.dumps(valid), encoding='utf-8')
            source.write_text(json.dumps(self.crossfit), encoding='utf-8')
            self.assertEqual(main(['--candidate', str(candidate), '--crossfit', str(source)]), 0)

    def test_cli_rejects_exponent_overflow_json(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            candidate = root / 'candidate.json'
            candidate.write_text('{"generated_at":1e999}', encoding='utf-8')
            source = root / 'crossfit.json'
            source.write_text(json.dumps(self.crossfit), encoding='utf-8')
            self.assertEqual(main(['--candidate', str(candidate), '--crossfit', str(source)]), 1)

    def test_missing_nested_recovery_rejected(self):
        self.assertIn('performance_v32_recovery_missing', self.codes(
            lambda c: c['performance_report_v32'].pop('recovery')))

    def test_missing_1rm_safety_rejected(self):
        self.assertIn('performance_v32_1rm_guardrail_missing', self.codes(
            lambda c: c['performance_report_v32']['interpretation_quality'].update(
                no_set_rir_inferred_from_session_rpe=False)))


if __name__=='__main__':
    unittest.main()
