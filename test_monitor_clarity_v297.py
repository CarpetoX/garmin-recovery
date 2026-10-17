"""Isolated regression tests; no GitHub or sensor access required."""
import copy
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from garmin_recovery.monitor_clarity import analyze, target_at, parsed, read_json, atomic_json

NOW = datetime(2026, 10, 12, 7, 15, tzinfo=timezone.utc)


def fixtures():
    ids = [101, 102, 103, 104]
    cert = {
        'status':'ready', 'cycle_id':'2026-10-12-0830',
        'slot_at':'2026-10-12T08:30:00+02:00',
        'target_report_at':'09:05',
        'verified_at':'2026-10-12T09:00:26+02:00',
        'chain':{
            'sync':{'id':ids[0], 'started_at':'2026-10-12T08:59:12+02:00'},
            'heart':{'id':ids[1]},'advanced':{'id':ids[2]},'crossfit':{'id':ids[3]}}
    }
    stages = {name:{'run_id':rid,'status':'completed','conclusion':'success'}
              for name,rid in zip(('sync','heart','advanced','crossfit'), ids)}
    health = {'status':'attention','alerts':[{'code':'cron_missed_dispatch_recovered',
                    'slots':['2026-10-11T22:45:00+02:00']}],
              'schedule_v231':{'state':'recovered'},
              'pipeline_progress':{'sync_run_id':ids[0], 'stages':stages},
              'report_status_v34':{'observed_pipeline':{
                         'state':'completed_exact_chain','exact_lineage_verified':True},
                   'last_readiness_certificate':{'cycle_id':cert['cycle_id'],
                                                'relationship':'same_verified_cycle'}}}
    origin = {'cycle_id':cert['cycle_id'], 'origin':{
        'source':'apps_script_backup','verified':True,'cycle_id':cert['cycle_id'],
        'evidence':'sync_hmac_validated_v291'}}
    lineage = {'complete_chain_verified':True, 'run_id':ids[-1],
               'root':{'run_id':ids[0], 'event':'workflow_dispatch',
                       'origin_v291':{'cycle_id':cert['cycle_id'],
                                     'source_verified':True,
                                     'origin_source':'apps_script_backup',
                                     'auth_method':'hmac_sha256_shared_secret_v291',
                                     'github_event':'workflow_dispatch'}}}
    return health, cert, origin, lineage


class V297MonitorTests(unittest.TestCase):
    def report(self, values=None):
        return analyze(*(values if values is not None else fixtures()), now=NOW)

    def test_valid_signed_cycle_ready(self):
        j = self.report()['monitor_v297']
        self.assertEqual(j['current_cycle']['state'],'verified_ready')
        self.assertTrue(j['current_cycle']['origin_verified'])
        self.assertTrue(j['current_cycle']['data_ready_verified'])

    def test_legacy_historical_attention_remains_visible(self):
        health,*_ = fixtures()
        original = copy.deepcopy(health)
        v = self.report()['monitor_v297']
        self.assertEqual(v['historical_alerts']['base_monitor_status'],'attention')
        self.assertEqual(v['historical_alerts']['prior_or_unattributed_alert_codes'],
                         ['cron_missed_dispatch_recovered'])
        self.assertEqual(health,original)

    def test_data_ready_punctuality(self):
        r = self.report()['monitor_v297']['punctuality']
        self.assertEqual(r['state'],'tight_margin')
        self.assertAlmostEqual(r['ready_before_target_minutes'],4.57)
        self.assertEqual(r['sync_start_delay_from_slot_minutes'],29.2)

    def test_late_report_is_not_called_on_time(self):
        f=fixtures(); f[1]['verified_at']='2026-10-12T09:07:00+02:00'
        j=self.report(f)['monitor_v297']
        self.assertEqual(j['current_cycle']['state'],'ready_late')
        self.assertEqual(j['punctuality']['state'],'late')

    def test_unsigned_dispatch_is_not_verified(self):
        f=fixtures(); f[2]['origin']['verified']=False
        j=self.report(f)['monitor_v297']
        self.assertEqual(j['current_cycle']['state'],'ready_sender_unverified')

    def test_origin_cycle_mismatch_not_verified(self):
        f=fixtures(); f[3]['root']['origin_v291']['cycle_id']='2026-10-11-0830'
        self.assertFalse(self.report(f)['monitor_v297']['current_cycle']['origin_verified'])

    def test_certificate_lineage_mismatch_cannot_be_ready(self):
        f=fixtures(); f[1]['chain']['sync']['id']=999
        self.assertEqual(self.report(f)['monitor_v297']['current_cycle']['state'],'cycle_unverified')

    def test_failed_workflow_is_not_verified(self):
        f=fixtures(); f[0]['pipeline_progress']['stages']['advanced']['conclusion']='failure'
        self.assertEqual(self.report(f)['monitor_v297']['current_cycle']['state'],'cycle_unverified')

    def test_v34_unmatched_cert_is_not_verified(self):
        f=fixtures(); f[0]['report_status_v34']['last_readiness_certificate']['relationship']='previous_or_unmatched_certificate'
        self.assertEqual(self.report(f)['monitor_v297']['current_cycle']['state'],'cycle_unverified')

    def test_current_slot_alert_is_not_historical(self):
        f=fixtures(); f[0]['alerts'].append({'code':'current_fault','slots':[f[1]['slot_at']]})
        j=self.report(f)['monitor_v297']
        self.assertEqual(j['current_cycle']['state'],'needs_attention')
        self.assertEqual(j['historical_alerts']['current_slot_alert_codes'], ['current_fault'])

    def test_existing_error_is_not_covered_up(self):
        f=fixtures(); f[0]['status']='error'
        self.assertEqual(self.report(f)['monitor_v297']['current_cycle']['state'],'needs_attention')

    def test_github_schedule_origin(self):
        f=fixtures(); f[3]['root']['event']='schedule'; f[2]['origin']={'source':'github_schedule','verified':True}
        self.assertEqual(self.report(f)['monitor_v297']['current_cycle']['origin'],
                         'github_schedule_verified')

    def test_delivery_not_claimed(self):
        j=self.report()['monitor_v297']
        self.assertFalse(j['delivery']['message_confirmed'])
        self.assertFalse(j['delivery']['push_confirmed'])
        self.assertIsNone(j['historical_alerts']['consecutive_automatic_successes'])
        self.assertIsNone(j['historical_alerts']['verified_recovered_incidents'])

    def test_missing_target_is_not_assessable(self):
        f=fixtures(); f[1]['target_report_at']='unknown'
        j=self.report(f)['monitor_v297']
        self.assertEqual(j['punctuality']['state'],'not_assessable')
        self.assertEqual(j['current_cycle']['state'],'cycle_unverified')

    def test_malformed_timestamps_do_not_guess(self):
        f=fixtures(); f[1]['verified_at']='malformed'
        self.assertFalse(self.report(f)['monitor_v297']['current_cycle']['data_ready_verified'])

    def test_local_day_is_not_utc_date(self):
        slot=parsed('2026-10-12T00:15:00+02:00')
        self.assertEqual(target_at(slot,'01:00').isoformat(),'2026-10-12T01:00:00+02:00')

    def test_target_next_day(self):
        slot=parsed('2026-10-12T22:45:00+02:00')
        self.assertEqual(target_at(slot,'00:05').isoformat(),'2026-10-13T00:05:00+02:00')

    def test_atomic_write_preserves_base_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'workflow_health.json'
            v=self.report()
            atomic_json(path,v)
            loaded=read_json(path)
            self.assertEqual(loaded['status'],'attention')
            self.assertEqual(loaded['monitor_v297']['current_cycle']['state'],'verified_ready')

    def test_missing_optional_origin_does_not_block(self):
        with tempfile.TemporaryDirectory() as temp:
            missing = read_json(Path(temp)/'origin_missing.json', required=False)
        f=list(fixtures()); f[2]=missing
        result=self.report(f)['monitor_v297']
        self.assertEqual(result['current_cycle']['state'],'ready_sender_unverified')

    def test_fails_closed_on_missing_json(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                read_json(Path(temp)/'missing.json')


if __name__ == '__main__':
    unittest.main()
