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


if __name__=='__main__':
    unittest.main()
