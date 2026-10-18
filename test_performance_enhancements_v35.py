"""V3.5 regression: real source fields, no invented training evidence."""
import copy
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import unittest

from garmin_recovery.performance_report import build_report
from garmin_recovery.performance_enhancements import build, validate, main
from garmin_recovery.training_trends import main as trends_main
from garmin_recovery.validate_performance import audit as validate_v33

TODAY = date(2026, 10, 11)


def fixture():
    acts = [
        {'activity_id':'A','date':'2026-10-11','name':'Fuerza','rpe_used':6,
         'recorded_minutes':40,'srpe_using_recorded_minutes':240,
         'heart_rate':{'average':118}},
        {'activity_id':'B','date':'2026-10-10','name':'HIIT','rpe_used':8.5,
         'recorded_minutes':12,'srpe_using_recorded_minutes':102,
         'heart_rate':{'average':148},'manual_rpe_conflict':True},
        {'activity_id':'C','date':'2026-10-09','name':'HIIT','rpe_used':None,
         'recorded_minutes':30,'heart_rate':{'average':135}},
        {'activity_id':'D','date':'2026-10-04','name':'Fuerza','rpe_used':9,
         'recorded_minutes':35,'srpe_using_recorded_minutes':315,
         'heart_rate':{'average':110}},
    ]
    strength = [
        {'date':'2026-10-11','activity_id':'A','exercise':'sentadilla trasera',
         'movement_pattern':'squat','equipment':'barbell','load_unit':'kg_total_barra',
         'peak_declared_load_kg':150,'verified_volume_kg':3000,
         'volume_complete':True,'known_sets':5,'laterality_unconfirmed':False},
        {'date':'2026-10-11','activity_id':'A','exercise':'prensa horizontal',
         'movement_pattern':'squat','equipment':'machine_stack','load_unit':'kg_indicado_maquina',
         'peak_declared_load_kg':120,'verified_volume_kg':4000,
         'volume_complete':True,'known_sets':4,'laterality_unconfirmed':False},
        {'date':'2026-10-11','activity_id':'A','exercise':'curl de pie unilateral',
         'movement_pattern':'knee_flexion','equipment':'machine_stack',
         'load_unit':'kg_indicado_maquina','peak_declared_load_kg':40,
         'verified_volume_kg':2560,'volume_complete':True,'known_sets':8,'laterality_unconfirmed':False},
    ]
    extensions={'metcon_exposure':{'entries':[
        {'date':'2026-10-10','activity_id':'B','movement':'Toes-to-bar',
         'verified_reps':33,'verified_distance_m':None,'evidence':'performed.totals'},
        {'date':'2026-10-10','activity_id':'B','movement':'Carrera',
         'verified_distance_m':1200,'evidence':'performed.totals'},
        {'date':'2026-10-10','activity_id':'B','movement':'thruster',
         'verified_reps':63,'evidence':'prescribed.totals'},
    ]},'performance_trends':{'eligible_benchmarks':0,'comparisons':[]}}
    return {'generated_at':'2026-10-11T21:05:00+02:00',
            'sheet_source':'cycle_snapshot','activities':acts,
            'muscle_load':{'strength_exercises':strength},
            'training_extensions':extensions}


def candidate(source=None):
    s = source or fixture()
    base = build_report(s, [], {'date':'2026-10-11'}, TODAY)
    addon = build(s, base, TODAY)
    base['performance_enhancements_v35'] = addon
    return {'version':'3.1','schema_version':1,'as_of_date':'2026-10-11',
            'source':'crossfit_insights.json','sheet_source':s['sheet_source'],
            'source_generated_at':s['generated_at'],
            'generated_at':'2026-10-11T19:06:00Z',
            'windows': {k:{'recorded_sessions':0} for k in ('3d','7d','28d')},
            'daily_chart_28d':[{'date':(TODAY-date.resolution*n).isoformat()} for n in range(27,-1,-1)],
            'performance_report_v32':base}


class V35Tests(unittest.TestCase):
    def test_existing_v32_unchanged_when_built(self):
        s=fixture(); old=build_report(s,[],{},TODAY); before=copy.deepcopy(old)
        addon=build(s,old,TODAY)
        self.assertEqual(old,before)
        self.assertEqual(addon['version'],'3.5')

    def test_real_modalities_and_rpe(self):
        x=candidate()['performance_report_v32']['performance_enhancements_v35']
        w=x['session_breakdown']['7d']
        self.assertEqual(w['sessions'],3)
        self.assertEqual(w['rpe_samples'],2)
        self.assertEqual(w['rpe_missing'],1)
        self.assertEqual(w['sessions_rpe_8_plus'],1)
        self.assertEqual(sum(w['rpe_distribution'].values()),2)
        names={v['category'] for v in w['categories']}
        self.assertEqual(names,{'Fuerza','HIIT'})

    def test_previous_week_does_not_claim_improvement(self):
        x=candidate()['performance_report_v32']['performance_enhancements_v35']
        self.assertEqual(x['session_breakdown']['previous_7d']['sessions'],1)
        self.assertEqual(x['interpretation_quality']['level'],'provisional')
        self.assertIn('insufficient_history',[r['category'] for r in x['recommendations']])

    def test_missing_day_is_not_rest(self):
        d=candidate()['performance_report_v32']['performance_enhancements_v35']['charts']['daily_14d']
        self.assertEqual(len(d),14)
        self.assertTrue(next(x for x in d if x['date']=='2026-10-08')['missing_record_is_not_rest'])
        self.assertIsNone(next(x for x in d if x['date']=='2026-10-08')['mean_session_rpe'])

    def test_unilateral_known_sets_not_doubled(self):
        patterns=candidate()['performance_report_v32']['performance_enhancements_v35']['strength_patterns']
        m={p['movement_pattern']:p for p in patterns['7d']}
        self.assertEqual(m['knee_flexion']['known_sets_recorded'],8)
        self.assertEqual(m['squat']['known_sets_recorded'],9)
        self.assertTrue(patterns['kg_from_different_equipment_or_units_never_added'])
        self.assertTrue(all('verified_volume_kg' not in p for p in patterns['7d']))

    def test_unknown_laterality_excludes_complete_volume_block(self):
        s=fixture();s['muscle_load']['strength_exercises'][-1]['laterality_unconfirmed']=True
        x=candidate(s)['performance_report_v32']['performance_enhancements_v35']
        q={p['movement_pattern']:p for p in x['strength_patterns']['7d']}
        self.assertEqual(q['knee_flexion']['volume_complete_blocks'],0)
        self.assertEqual(q['knee_flexion']['laterality_unconfirmed_blocks'],1)

    def test_metcon_only_performed(self):
        v=candidate()['performance_report_v32']['performance_enhancements_v35']['metcon_exposure']
        m={x['movement']:x for x in v['7d']}
        self.assertEqual(m['toes-to-bar']['verified_reps_total'],33)
        self.assertEqual(m['carrera']['verified_distance_m_total'],1200)
        self.assertNotIn('thruster',m)

    def test_duplicate_activity_ignored(self):
        s=fixture();s['activities'].append(copy.deepcopy(s['activities'][0]))
        x=candidate(s)['performance_report_v32']['performance_enhancements_v35']
        self.assertEqual(x['session_breakdown']['7d']['sessions'],3)
        self.assertEqual(x['provenance']['duplicate_activity_ids_ignored'],1)

    def test_duplicate_metcon_is_not_double_counted(self):
        s=fixture();e=s['training_extensions']['metcon_exposure']['entries']
        e.append(copy.deepcopy(e[0]))
        v=candidate(s)['performance_report_v32']['performance_enhancements_v35']['metcon_exposure']
        self.assertEqual(v['duplicate_activity_movement_rows_skipped'],1)
        self.assertEqual(next(x for x in v['7d'] if x['movement']=='toes-to-bar')['verified_reps_total'],33)

    def test_duplicate_strength_does_not_count_set_twice(self):
        s=fixture();ss=s['muscle_load']['strength_exercises'];ss.append(copy.deepcopy(ss[0]))
        v=candidate(s)['performance_report_v32']['performance_enhancements_v35']['strength_patterns']
        self.assertEqual(v['duplicate_exercise_rows_skipped'],1)
        self.assertEqual(next(x for x in v['7d'] if x['movement_pattern']=='squat')['known_sets_recorded'],9)

    def test_unknown_rpe_never_zero(self):
        s=fixture();s['activities'][0]['rpe_used']=None
        w=candidate(s)['performance_report_v32']['performance_enhancements_v35']['session_breakdown']['7d']
        self.assertEqual(w['rpe_samples'],1)
        self.assertEqual(w['rpe_distribution']['0_to_3'],0)

    def test_invalid_rpe_and_nonfinite_ignored(self):
        s=fixture();s['activities'][0]['rpe_used']=float('nan')
        x=build(s,build_report(s,[],{},TODAY),TODAY)
        self.assertEqual(x['session_breakdown']['7d']['rpe_samples'],1)
        self.assertEqual(x['session_breakdown']['7d']['sessions_rpe_8_plus'],1)

    def test_unmatched_and_future_metcon_excluded(self):
        s=fixture();e=s['training_extensions']['metcon_exposure']['entries']
        e.append({'date':'2026-10-11','activity_id':'wrong','movement':'carrera','verified_distance_m':999,'evidence':'performed.totals'})
        e.append({'date':'2026-10-12','activity_id':'B','movement':'carrera','verified_distance_m':999,'evidence':'performed.totals'})
        m=build(s,build_report(s,[],{},TODAY),TODAY)['metcon_exposure']
        self.assertEqual(next(x for x in m['7d'] if x['movement']=='carrera')['verified_distance_m_total'],1200)

    def test_mismatched_activity_date_never_counts_strength_or_wod(self):
        s=fixture()
        s['muscle_load']['strength_exercises'][0]['date']='2026-10-10'
        s['training_extensions']['metcon_exposure']['entries'][0]['date']='2026-10-11'
        x=candidate(s)['performance_report_v32']['performance_enhancements_v35']
        p=next(p for p in x['strength_patterns']['7d'] if p['movement_pattern']=='squat')
        self.assertEqual(p['known_sets_recorded'],4)
        self.assertNotIn('toes-to-bar', [y['movement'] for y in x['metcon_exposure']['7d']])

    def test_invalid_metcon_followed_by_valid_same_movement_keeps_valid(self):
        s=fixture()
        s['training_extensions']['metcon_exposure']['entries'].insert(0,{
            'date':'2026-10-10','activity_id':'B','movement':'Toes-to-bar',
            'verified_reps':None,'evidence':'performed.totals'})
        x=candidate(s)['performance_report_v32']['performance_enhancements_v35']
        self.assertEqual(next(y for y in x['metcon_exposure']['7d'] if y['movement']=='toes-to-bar')['verified_reps_total'],33)

    def test_no_benchmark_inferred_from_workout_name(self):
        x=candidate()['performance_report_v32']['performance_enhancements_v35']['benchmarks']
        self.assertEqual(x['status'],'no_verified_repeated_benchmarks')
        self.assertTrue(x['workout_names_are_not_benchmark_ids'])

    def test_manual_rpe_conflict_flag(self):
        x=candidate()['performance_report_v32']['performance_enhancements_v35']
        self.assertEqual(x['rpe_conflicts_recorded'],1)
        self.assertIn('rpe_conflicts',[r['category'] for r in x['recommendations']])

    def test_source_not_mutated(self):
        s=fixture();save=copy.deepcopy(s)
        build(s,build_report(s,[],{},TODAY),TODAY)
        self.assertEqual(s,save)

    def test_valid_candidate(self):
        self.assertEqual(validate(candidate(),fixture()),[])

    def test_bad_chart_rejected(self):
        z=candidate();z['performance_report_v32']['performance_enhancements_v35']['charts']['daily_14d'].pop()
        self.assertIn('v35_chart_missing',validate(z,fixture()))

    def test_bad_source_rejected(self):
        z=candidate();z['performance_report_v32']['performance_enhancements_v35']['provenance']['crossfit_generated_at']='wrong'
        self.assertIn('v35_source_mismatch',validate(z,fixture()))

    def test_bad_session_count_rejected(self):
        z=candidate();z['performance_report_v32']['performance_enhancements_v35']['session_breakdown']['7d']['sessions']=99
        self.assertIn('v35_window_mismatch:7d',validate(z,fixture()))

    def test_modified_modality_hr_rejected_even_if_shape_valid(self):
        z=candidate()
        z['performance_report_v32']['performance_enhancements_v35']['session_breakdown']['7d']['categories'][0]['mean_of_session_average_hr_bpm_unweighted']=999
        self.assertIn('v35_source_derived_values_mismatch',validate(z,fixture()))

    def test_mutated_performed_repetitions_rejected(self):
        z=candidate()
        z['performance_report_v32']['performance_enhancements_v35']['metcon_exposure']['7d'][0]['verified_distance_m_total']=99999
        self.assertIn('v35_source_derived_values_mismatch',validate(z,fixture()))

    def test_bad_guardrails_rejected(self):
        z=candidate();z['performance_report_v32']['performance_enhancements_v35']['interpretation_quality']['no_1rm_from_session_rpe']=False
        self.assertIn('v35_interpretation_guard_invalid',validate(z,fixture()))

    def test_v35_preserves_v33_validation_rules(self):
        # v33 cross-checks version 3.2 and basic provenance, accepts additive key.
        z=candidate();today=datetime(2026,10,11,19,7,tzinfo=timezone.utc)
        self.assertEqual(validate_v33(z,fixture(),today),[])

    def test_end_to_end_real_json_and_cli(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)
            s=fixture()
            (path/'crossfit_insights.json').write_text(json.dumps(s),encoding='utf-8')
            (path/'wellness.json').write_text('[]',encoding='utf-8')
            (path/'daily_summary.json').write_text('{"date":"2026-10-11"}',encoding='utf-8')
            old=os.getcwd()
            try:
                os.chdir(root)
                trends_main(['--input','crossfit_insights.json','--out','candidate.json','--today','2026-10-11'])
                self.assertEqual(main(['--candidate','candidate.json','--crossfit','crossfit_insights.json']),0)
            finally:
                os.chdir(old)

    def test_validator_rejects_nonfinite_json(self):
        with tempfile.TemporaryDirectory() as root:
            a=Path(root)/'candidate.json';b=Path(root)/'crossfit.json'
            a.write_text('{"not":NaN}',encoding='utf-8');b.write_text(json.dumps(fixture()),encoding='utf-8')
            self.assertEqual(main(['--candidate',str(a),'--crossfit',str(b)]),1)

    def test_invalid_crossfit_or_base_rejected(self):
        with self.assertRaises(ValueError):
            build({}, {}, TODAY)
        with self.assertRaises(ValueError):
            build(fixture(), {'version':'3.2','as_of_date':'2026-10-10','window_comparison':{}}, TODAY)

if __name__=='__main__':
    unittest.main()
