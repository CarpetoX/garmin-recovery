"""Pruebas V3.4: estados independientes, origen probado y suplementos post-sueño."""
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

from report_monitor_v34 import analyze, main

NOW = datetime(2026, 10, 11, 19, 50, tzinfo=timezone.utc)


def sample():
    times = [('2026-10-11T19:39:59Z', '2026-10-11T19:40:13Z'),
             ('2026-10-11T19:40:15Z', '2026-10-11T19:40:42Z'),
             ('2026-10-11T19:40:44Z', '2026-10-11T19:40:55Z'),
             ('2026-10-11T19:40:57Z', '2026-10-11T19:41:18Z')]
    run_ids = [38168979917, 38168999815, 38169035188, 38169050930]
    stages = {name: dict(run_id=ident, status='completed', conclusion='success',
                         created_at=start, updated_at=end)
              for name, ident, (start, end) in zip(('sync','heart','advanced','crossfit'), run_ids, times)}
    health = {'status':'attention', 'checked_at':'2026-10-11T21:42:00+02:00',
              'schedule_v231':{'state':'recovered','due':3,'matched':0,
                               'recovered_by_unattributed':['2026-10-11T16:45:00+02:00']},
              'pipeline_progress':{'state':'completed_outside_report_slots',
                                   'sync_run_id':run_ids[0],'stages':stages},
              'alerts':[], 'note':'Prior evidence.'}
    lineage = {'complete_chain_verified':True, 'run_id':run_ids[-1],
               'root':{'run_id':run_ids[0], 'event':'workflow_dispatch',
                       'origin_v291':{'source_verified':False,
                                     'origin_source':'workflow_dispatch_unattributed'}},
               'stages':{name:{'run_id':rid} for name,rid in zip(stages,run_ids)}}
    cert = {'status':'ready','cycle_id':'2026-10-11-1645',
            'verified_at':'2026-10-11T17:00:17+02:00',
            'chain':{'sync':{'id':38149393086},'crossfit':{'id':38149449854}}}
    base_ledger = {'cycles':[
        {'cycle_id':'2026-10-11-0830','ready_at':'2026-10-11T08:50:00+02:00',
         'sync_run_id':101,'state':'data_ready','notification_delivery':'unverified'},
        {'cycle_id':'2026-10-11-0830-post-sleep',
         'parent_cycle_id':'2026-10-11-0830','certificate_kind':'post_sleep_supplement',
         'ready_at':'2026-10-11T10:45:00+02:00', 'sync_run_id':102,
         'state':'data_ready','notification_delivery':'unverified'},
        {'cycle_id':'2026-10-11-1645','ready_at':'2026-10-11T17:00:17+02:00',
         'sync_run_id':38149393086,'crossfit_run_id':38149449854,'state':'data_ready','notification_delivery':'unverified'}]}
    crossfit = {'generated_at':'2026-10-11T21:41:05.832691+02:00'}
    trends = {'generated_at':'2026-10-11T19:41:06.008941+00:00',
              'as_of_date':'2026-10-11', 'source_generated_at':crossfit['generated_at'],
              'performance_report_v32':{
                  'version':'3.2','schema_version':1,'as_of_date':'2026-10-11',
                  'provenance':{'crossfit_generated_at':crossfit['generated_at']},
                  'charts':{'daily_28d':[{'date':'2026-10-11'}] * 28}}}
    return health, base_ledger, cert, lineage, trends, crossfit


def evaluate(parts):
    return analyze(*parts, now=NOW)['report_status_v34']


class MonitorV34Tests(unittest.TestCase):
    def test_verified_manual_pipeline_report_and_previous_certificate(self):
        a=evaluate(sample())
        self.assertEqual(a['observed_pipeline']['state'],'completed_exact_chain')
        self.assertEqual(a['performance_report']['state'],'published_for_observed_pipeline')
        self.assertEqual(a['last_readiness_certificate']['relationship'],
                         'previous_or_unmatched_certificate')
        self.assertEqual(a['launch_origin']['state'],'caller_unverified')

    def test_no_delivery_even_with_report_and_certificate(self):
        a=evaluate(sample())
        self.assertEqual(a['chatgpt_delivery']['state'],'unverified_no_receipt')
        self.assertFalse(a['chatgpt_delivery']['confirmed_message'])
        self.assertFalse(a['chatgpt_delivery']['confirmed_push'])

    def test_post_sleep_is_supplement_not_scheduled_or_delivered(self):
        a=evaluate(sample())
        self.assertEqual(a['post_sleep']['state'],'supplement_data_ready_once')
        self.assertTrue(a['post_sleep']['not_a_second_scheduled_report'])
        self.assertFalse(a['post_sleep']['delivery_to_chatgpt_confirmed'])

    def test_duplicate_supplement_is_flagged(self):
        parts=sample()
        parts[1]['cycles'].append(copy.deepcopy(parts[1]['cycles'][1]))
        out=analyze(*parts, now=NOW)
        self.assertEqual(out['status'],'attention')
        self.assertEqual(out['report_status_v34']['post_sleep']['state'],
                         'duplicate_certificates_detected')
        self.assertTrue(any(a['code']=='post_sleep_certificate_integrity_v34'
                            for a in out['alerts']))

    def test_orphan_supplement_is_flagged(self):
        parts=sample(); parts[1]['cycles'][1]['parent_cycle_id']='2026-10-11-2245'
        self.assertEqual(evaluate(parts)['post_sleep']['state'],
                         'invalid_certificate_relationship')

    def test_post_sleep_invalid_time_is_flagged(self):
        parts=sample(); parts[1]['cycles'][1]['ready_at']='2031-01-01T10:45:00Z'
        self.assertEqual(evaluate(parts)['post_sleep']['state'],
                         'invalid_certificate_relationship')

    def test_missing_ledger_does_not_guess_post_sleep(self):
        parts=list(sample()); parts[1]=None
        self.assertEqual(evaluate(parts)['post_sleep']['state'],'ledger_unavailable')

    def test_exact_readiness_matches_only_current_sync_and_ledger(self):
        parts=sample(); parts[2]['chain']['sync']['id']=38168979917
        parts[1]['cycles'][2]['sync_run_id']=38168979917
        parts[2]['chain']['crossfit']['id']=38169050930
        parts[1]['cycles'][2]['crossfit_run_id']=38169050930
        out=evaluate(parts)
        self.assertTrue(out['last_readiness_certificate']['corresponds_to_observed_pipeline'])
        self.assertEqual(out['last_readiness_certificate']['relationship'],'same_verified_cycle')

    def test_readiness_not_inherited_if_ledger_id_different(self):
        parts=sample(); parts[2]['chain']['sync']['id']=38168979917
        self.assertFalse(evaluate(parts)['last_readiness_certificate']['corresponds_to_observed_pipeline'])

    def test_future_cert_cannot_claim_ready(self):
        parts=sample(); parts[2]['verified_at']='2030-10-11T17:00:17+02:00'
        self.assertEqual(evaluate(parts)['last_readiness_certificate']['status'],'not_verified')

    def test_no_cert_does_not_stop_observation(self):
        parts=list(sample()); parts[2]=None
        self.assertEqual(evaluate(parts)['observed_pipeline']['state'],'completed_exact_chain')
        self.assertEqual(evaluate(parts)['last_readiness_certificate']['status'],'not_verified')

    def test_lineage_wrong_sync_id_cannot_certify(self):
        parts=sample(); parts[3]['root']['run_id']=1
        a=evaluate(parts)
        self.assertEqual(a['observed_pipeline']['state'],'completed_lineage_unverified')
        self.assertFalse(a['performance_report']['verified_current_pipeline'])

    def test_lineage_wrong_stage_cannot_certify(self):
        parts=sample(); parts[3]['stages']['advanced']['run_id']=999
        self.assertFalse(evaluate(parts)['observed_pipeline']['exact_lineage_verified'])

    def test_incomplete_stage_not_advanced_to_completed(self):
        parts=sample(); parts[0]['pipeline_progress']['stages']['crossfit']['status']='in_progress'
        self.assertNotEqual(evaluate(parts)['observed_pipeline']['state'],'completed_exact_chain')

    def test_pipeline_failure_not_marked_success(self):
        parts=sample(); parts[0]['pipeline_progress']['state']='failed'
        self.assertEqual(evaluate(parts)['observed_pipeline']['state'],'failed')

    def test_pending_state_not_completed(self):
        parts=sample(); parts[0]['pipeline_progress']['state']='in_progress'
        self.assertEqual(evaluate(parts)['observed_pipeline']['state'],'in_progress')

    def test_missing_sync_run_not_started(self):
        parts=sample(); parts[0]['pipeline_progress']['sync_run_id']=None
        self.assertEqual(evaluate(parts)['observed_pipeline']['state'],'sync_not_observed')

    def test_stale_report_cannot_claim_current_pipeline(self):
        parts=sample(); parts[4]['source_generated_at']='2026-10-10T11:00:00+02:00'
        self.assertFalse(evaluate(parts)['performance_report']['verified_current_pipeline'])

    def test_crossfit_report_time_does_not_belong_to_current_run(self):
        parts=sample(); parts[5]['generated_at']='2026-10-10T21:41:05+02:00'
        parts[4]['source_generated_at']=parts[5]['generated_at']
        parts[4]['performance_report_v32']['provenance']['crossfit_generated_at']=parts[5]['generated_at']
        self.assertFalse(evaluate(parts)['performance_report']['verified_current_pipeline'])

    def test_missing_v32_not_reported_published(self):
        parts=sample(); parts[4].pop('performance_report_v32')
        self.assertEqual(evaluate(parts)['performance_report']['state'],'not_published_or_legacy')

    def test_invalid_chart_not_published(self):
        parts=sample(); parts[4]['performance_report_v32']['charts']['daily_28d']=['x']
        self.assertFalse(evaluate(parts)['performance_report']['verified_current_pipeline'])

    def test_signed_apps_script_only_with_real_verified_proof(self):
        parts=sample(); parts[3]['root']['origin_v291']={
            'source_verified':True, 'origin_source':'apps_script_backup',
            'auth_method':'hmac_sha256_shared_secret_v291',
            'github_event':'repository_dispatch','cycle_id':'2026-10-11-1645'}
        parts[3]['root']['event']='repository_dispatch'
        self.assertEqual(evaluate(parts)['launch_origin']['state'],'apps_script_signed_verified')
        parts[3]['root']['origin_v291']['source_verified']=False
        self.assertEqual(evaluate(parts)['launch_origin']['state'],'caller_unverified')

    def test_signed_proof_cannot_use_different_event(self):
        parts=sample()
        parts[3]['root']['origin_v291']={
            'source_verified':True,'origin_source':'apps_script_backup',
            'auth_method':'hmac_sha256_shared_secret_v291',
            'github_event':'repository_dispatch'}
        self.assertNotEqual(evaluate(parts)['launch_origin']['state'],
                            'apps_script_signed_verified')

    def test_schedule_from_last_sync_run_url(self):
        parts=sample()
        parts[3]['root']['event']=None
        parts[0]['workflows']={'sync.yml':{
            'latest_run_event':'schedule',
            'latest_run_url':'https://github.com/CarpetoX/garmin-recovery/actions/runs/38168979917'}}
        self.assertEqual(evaluate(parts)['launch_origin']['state'],'github_schedule_observed')
        parts[0]['workflows']['sync.yml']['latest_run_url'] += '88'
        self.assertNotEqual(evaluate(parts)['launch_origin']['state'],'github_schedule_observed')

    def test_github_schedule_known_event(self):
        parts=sample(); parts[3]['root']['event']='schedule'
        self.assertEqual(evaluate(parts)['launch_origin']['state'],'github_schedule_observed')

    def test_no_mutation_of_inputs(self):
        parts=sample(); before=copy.deepcopy(parts)
        analyze(*parts,now=NOW)
        self.assertEqual(parts,before)

    def test_idempotent_repeated_audit(self):
        parts=sample()
        once=analyze(*parts, now=NOW)
        twice=analyze(once, *parts[1:], now=NOW)
        self.assertEqual(once,twice)

    def test_invalid_health_rejected(self):
        with self.assertRaises(ValueError):
            analyze(None,now=NOW)

    def test_naive_monitor_time_rejected(self):
        with self.assertRaises(ValueError):
            analyze({},now=datetime(2026,10,11,21,30))

    def test_cli_missing_health_does_not_create_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'health.json'
            with self.assertRaises(SystemExit):
                main(['--health',str(path)])
            self.assertFalse(path.exists())

    def test_cli_updates_health_atomically_without_source_modification(self):
        parts=sample()
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)
            names=['health.json','ledger.json','cert.json','lineage.json','trends.json','crossfit.json']
            for name, content in zip(names,parts):
                (d/name).write_text(json.dumps(content),encoding='utf-8')
            inputs=[(d/name).read_bytes() for name in names[1:]]
            args=[]
            for label, name in zip(['health','ledger','certificate','lineage','trends','crossfit'],names):
                args.extend(['--'+label, str(d/name)])
            self.assertEqual(main(args),0)
            health=json.loads((d/'health.json').read_text(encoding='utf-8'))
            self.assertEqual(health['report_status_v34']['chatgpt_delivery']['state'],
                             'unverified_no_receipt')
            self.assertEqual([(d/name).read_bytes() for name in names[1:]],inputs)


if __name__=='__main__':
    unittest.main()
