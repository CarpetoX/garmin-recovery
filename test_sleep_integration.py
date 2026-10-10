import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import patch
import report_sleep_integration as integration

TZ=ZoneInfo('Europe/Madrid')

class SleepIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.chain={'slot':{'slot':'0830'}}
        self.now=datetime(2026,10,10,9,40,tzinfo=TZ)
    def check(self,state,expected):
        with patch.object(integration,'_original_build',return_value={'target_report_at':'08:45','limitations':[]}),patch.object(integration,'sleep_state',return_value=state):
            cert=integration.build(self.chain,{},self.now)
        self.assertEqual(cert['physiological_report_status'],expected)
        self.assertEqual(cert['target_report_at'],integration.TARGETS[self.chain['slot']['slot']])
        return cert
    def test_missing_sleep_is_provisional(self):
        self.check({},'provisional')
    def test_pending_sleep_is_provisional(self):
        self.check({'state':'sleep_or_sync_pending','is_definitive':False,'date':'2026-10-10'},'provisional')
    def test_confirmed_wait_is_provisional(self):
        self.check({'state':'confirmed_wait_30m','is_definitive':False,'date':'2026-10-10'},'provisional')
    def test_night_shift_pending_is_provisional(self):
        self.check({'state':'post_night_shift_sleep_pending','is_definitive':False,'date':'2026-10-10'},'provisional')
    def test_ready_is_definitive(self):
        self.check({'state':'confirmed_ready','is_definitive':True,'date':'2026-10-10'},'definitive')
    def test_stale_ready_is_provisional(self):
        self.check({'state':'confirmed_ready','is_definitive':True,'date':'2026-10-09'},'provisional')
    def test_other_slots_do_not_claim_sleep(self):
        self.chain['slot']['slot']='1645'
        cert=self.check({'state':'confirmed_ready','is_definitive':True,'date':'2026-10-10'},'not_evaluated_for_this_slot')
        self.assertEqual(cert['target_report_at'],'17:10')

if __name__=='__main__': unittest.main()
