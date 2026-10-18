import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from garmin_recovery.morning_sleep_gate import classify
TZ=ZoneInfo('Europe/Madrid')
NOW=datetime(2026,10,10,9,40,tzinfo=TZ)
def row(end):
 return {'days':{'2026-10-10':{'window_confirmed':True,'sleep_start_local':'2026-10-10T00:00:00+02:00','sleep_end_local':end}}}
def rec(end):
 return {'current':{'sleep_end_local':end},'input_freshness':{'sleep':True}}
class TestSleepGate(unittest.TestCase):
 def test_missing_sleep(self):
  x=classify(NOW,{'days':{}},{},{})
  self.assertEqual(x['state'],'sleep_or_sync_pending')
 def test_night_shift(self):
  x=classify(NOW,{'days':{}},{},{'days':{'2026-10-09':'TN'}})
  self.assertEqual(x['state'],'post_night_shift_sleep_pending')
 def test_30min(self):
  end='2026-10-10T09:20:00+02:00'
  self.assertEqual(classify(NOW,row(end),rec(end),{})['state'],'confirmed_wait_30m')
 def test_ready(self):
  end='2026-10-10T09:07:00+02:00'
  self.assertEqual(classify(NOW,row(end),rec(end),{})['state'],'confirmed_ready')
 def test_stale_recovery(self):
  end='2026-10-10T09:07:00+02:00'
  self.assertEqual(classify(NOW,row(end),rec('2026-10-09T09:07:00+02:00'),{})['state'],'confirmed_recovery_sync_pending')
 def test_future_sleep_end(self):
  end='2026-10-10T10:30:00+02:00'
  self.assertEqual(classify(NOW,row(end),rec(end),{})['state'],'sleep_or_sync_pending')
 def _tn(self,end,hours,tn=True):
  r=row(end) 
  if hours is not None: r['days']['2026-10-10']['sleep_hours']=hours
  return classify(NOW,r,rec(end),{'days':{'2026-10-09':'TN'}} if tn else {})
 def test_short_sleep_after_tn_is_provisional(self):
  x=self._tn('2026-10-10T08:30:00+02:00',3.5)
  self.assertEqual(x['state'],'post_night_shift_short_sleep_pending')
  self.assertFalse(x['is_definitive']); self.assertFalse(x['wake_confirmed']); self.assertTrue(x['possible_sleep_in_progress'])
  self.assertTrue(x['short_post_shift_episode'])
 def test_long_sleep_after_tn_is_definitive(self):
  self.assertEqual(self._tn('2026-10-10T08:30:00+02:00',6.0)['state'],'confirmed_ready')
 def test_short_sleep_without_tn_is_definitive(self):
  self.assertEqual(self._tn('2026-10-10T08:30:00+02:00',3.5,tn=False)['state'],'confirmed_ready')
 def test_unknown_hours_do_not_block(self):
  self.assertEqual(self._tn('2026-10-10T08:30:00+02:00',None)['state'],'confirmed_ready')
 def test_short_sleep_ending_after_ten_is_definitive(self):
  x=classify(datetime(2026,10,10,11,0,tzinfo=TZ),{'days':{'2026-10-10':{'window_confirmed':True,'sleep_start_local':'2026-10-10T07:00:00+02:00','sleep_end_local':'2026-10-10T10:20:00+02:00','sleep_hours':3.2}}},rec('2026-10-10T10:20:00+02:00'),{'days':{'2026-10-09':'TN'}})
  self.assertEqual(x['state'],'confirmed_ready')
if __name__=='__main__': unittest.main()
