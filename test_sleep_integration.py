import unittest
from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo
import report_sleep_integration as integration

TZ = ZoneInfo('Europe/Madrid')

class SleepIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 10, 9, 40, tzinfo=TZ)
        self.chain = {'slot': {'slot': '0830'}}

    def valid(self):
        return dict(state='confirmed_ready', is_definitive=True, date='2026-10-10',
                    generated_at=(self.now-timedelta(minutes=2)).isoformat(),
                    sleep_end_local=(self.now-timedelta(minutes=40)).isoformat(),
                    earliest_definitive_at=(self.now-timedelta(minutes=10)).isoformat(),
                    recovery_matches_sleep_episode=True, recovery_sleep_fresh=True)

    def check(self, state, expected):
        with patch.object(integration, '_original_build', return_value={'target_report_at': '08:45', 'limitations': []}), patch.object(integration, 'sleep_state', return_value=state):
            cert = integration.build(self.chain, {}, self.now)
        self.assertEqual(cert['physiological_report_status'], expected)
        self.assertEqual(cert['target_report_at'], integration.TARGETS[self.chain['slot']['slot']])
        return cert

    def test_valid(self): self.check(self.valid(), 'definitive')
    def test_missing(self): self.check({}, 'provisional')
    def test_previous_day(self):
        x=self.valid(); x['date']='2026-10-09'; self.check(x, 'provisional')
    def test_old_generation(self):
        x=self.valid(); x['generated_at']=(self.now-timedelta(hours=3)).isoformat(); self.check(x, 'provisional')
    def test_future_generation(self):
        x=self.valid(); x['generated_at']=(self.now+timedelta(minutes=10)).isoformat(); self.check(x, 'provisional')
    def test_unconfirmed(self):
        x=self.valid(); x['state']='confirmed_wait_30m'; self.check(x, 'provisional')
    def test_margin(self):
        x=self.valid(); x['earliest_definitive_at']=(self.now+timedelta(minutes=1)).isoformat(); self.check(x, 'provisional')
    def test_mismatch(self):
        x=self.valid(); x['recovery_matches_sleep_episode']=False; self.check(x, 'provisional')
    def test_unfresh_recovery(self):
        x=self.valid(); x['recovery_sleep_fresh']=False; self.check(x, 'provisional')
    def test_night_shift_pending(self):
        x=self.valid(); x['state']='post_night_shift_sleep_pending'; self.check(x, 'provisional')
    def test_other_slots(self):
        self.chain['slot']['slot']='1645'; self.check(self.valid(), 'not_evaluated_for_this_slot')
    def test_no_legacy_target(self):
        self.assertEqual(integration.gate.SLOTS[0][3], '09:05')

if __name__ == '__main__': unittest.main()
