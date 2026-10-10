import unittest
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from morning_sleep_gate import classify
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
if __name__=='__main__': unittest.main()
