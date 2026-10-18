import tempfile
import unittest
from datetime import date
from pathlib import Path

from garmin_recovery import garmin_metrics as gm

H = 3600 * 1000


class Basics(unittest.TestCase):
    def test_load_save_json(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.json"
            self.assertEqual(gm.load_json(p, {"a": 1}), {"a": 1})
            gm.save_json(p, {"ñ": 2})
            self.assertEqual(gm.load_json(p, None), {"ñ": 2})
            p.write_text("{roto", encoding="utf-8")
            self.assertEqual(gm.load_json(p, "def"), "def")

    def test_number_and_samples(self):
        self.assertIsNone(gm.number(True))
        self.assertEqual(gm.number(3), 3)
        self.assertEqual(gm.first_numeric_sample([1, 2, 55]), 55)
        self.assertEqual(gm.first_numeric_sample([1, 40]), 40)
        self.assertIsNone(gm.first_numeric_sample([1, None]))
        self.assertIsNone(gm.first_numeric_sample("x"))

    def test_epoch_ms(self):
        self.assertEqual(gm.epoch_ms(5.9), 5)
        self.assertEqual(gm.epoch_ms("1970-01-01T00:00:01Z"), 1000)
        self.assertIsNone(gm.epoch_ms("nada"))
        self.assertIsNone(gm.epoch_ms(None))
        self.assertIsNone(gm.local_iso_from_ms(None))
        self.assertTrue(gm.local_iso_from_ms(0).startswith("1970-01-01T01:00"))

    def test_hr_samples_filters(self):
        raw = {"heartRateValues": [[1000, 60], [2000, 10], [3000, 300], [4000, None], "x", [5000]]}
        self.assertEqual(gm.hr_samples(raw), [(1000, 60.0)])
        self.assertEqual(gm.hr_samples(None), [])

    def test_sleep_window(self):
        ok = {"dailySleepDTO": {"sleepStartTimestampGMT": 1000, "sleepEndTimestampGMT": 5000}}
        self.assertEqual(gm.sleep_window_gmt(ok), (1000, 5000))
        bad = {"dailySleepDTO": {"sleepStartTimestampGMT": 5000, "sleepEndTimestampGMT": 1000}}
        self.assertEqual(gm.sleep_window_gmt(bad), (None, None))
        self.assertEqual(gm.sleep_window_gmt([]), (None, None))
        self.assertTrue(gm.inside_window(2, 1, 3))
        self.assertFalse(gm.inside_window(2, None, 3))


class HeartRate(unittest.TestCase):
    def test_split_day_night_and_next_sleep(self):
        hr_prev = {"heartRateValues": [[0, 50], [1 * H, 52]]}
        hr_today = {"restingHeartRate": 55, "minHeartRate": 45, "maxHeartRate": 150,
                    "heartRateValues": [[3 * H, 51], [10 * H, 80], [12 * H, 100], [22 * H, 49]]}
        sleep = {"dailySleepDTO": {"sleepStartTimestampGMT": 0, "sleepEndTimestampGMT": 6 * H}}
        nxt = {"dailySleepDTO": {"sleepStartTimestampGMT": 21 * H, "sleepEndTimestampGMT": 30 * H}}
        r = gm.heart_rate_summary(hr_today, hr_prev, sleep, nxt, partial_day=True)
        self.assertEqual(r["nighttime_sample_count"], 3)
        self.assertEqual(r["daytime_sample_count"], 2)
        self.assertEqual(r["daytime_avg_hr"], 90.0)
        self.assertEqual(r["day_minus_night_bpm"], round(90 - (50 + 52 + 51) / 3, 1))
        self.assertTrue(r["partial_day"] and r["sleep_window_available"])
        self.assertEqual(r["resting_hr"], 55)

    def test_no_sleep_window_and_non_dict(self):
        r = gm.heart_rate_summary(None, None, None)
        self.assertIsNone(r["nighttime_avg_hr"])
        self.assertFalse(r["sleep_window_available"])
        self.assertIsNone(r["resting_hr"])

    def test_rolling_excludes_partial_daytime(self):
        days = {
            "2026-10-16": {"daytime_avg_hr": 70, "daytime_sample_count": 100, "nighttime_avg_hr": 50, "nighttime_sample_count": 50},
            "2026-10-17": {"daytime_avg_hr": 80, "daytime_sample_count": 100, "nighttime_avg_hr": 52, "nighttime_sample_count": 50,
                           "partial_day": True},
            "2026-10-18": "no-dict",
        }
        r = gm.heart_rate_rolling(days, date(2026, 10, 18))
        self.assertEqual(r["3d"]["daytime_avg_hr"], 70.0)
        self.assertEqual(r["3d"]["daytime_partial_days_excluded"], 1)
        self.assertEqual(r["3d"]["nighttime_avg_hr"], 51.0)
        self.assertEqual(r["3d"]["day_minus_night_bpm"], 19.0)
        self.assertEqual((r["28d"]["from"], r["28d"]["to"]), ("2026-09-21", "2026-10-18"))
        empty = gm.heart_rate_rolling({}, date(2026, 10, 18))
        self.assertIsNone(empty["7d"]["daytime_avg_hr"])
        self.assertIsNone(empty["7d"]["day_minus_night_bpm"])


class Summaries(unittest.TestCase):
    def test_stress(self):
        raw = {"avgStressLevel": 30, "maxStressLevel": 80, "stressValuesArray": [[0, 10], [1, -1], [2, 50], [3, 90], [4, None]]}
        r = gm.stress_summary(raw)
        self.assertEqual((r["sample_count"], r["sample_mean"], r["sample_p90"], r["average_stress"]), (3, 50.0, 50, 30))
        self.assertIsNone(gm.stress_summary("x"))
        self.assertIsNone(gm.stress_summary({})["sample_mean"])

    def test_body_battery(self):
        raw = {"charged": 40, "drained": 30, "bodyBatteryValuesArray": [[1000, "x", 80], [2000, 60], [3000, None]]}
        r = gm.body_battery_summary(raw)
        self.assertEqual((r["latest"], r["highest"], r["lowest"], r["latest_sample_timestamp"]), (60, 80, 60, 2000))
        self.assertIsNone(gm.body_battery_summary(None))
        self.assertIsNone(gm.body_battery_summary({})["latest"])

    def test_readiness_and_hrv(self):
        r = gm.summarize_readiness({"score": 59, "level": "MODERATE", "recoveryTime": 90})
        self.assertEqual((r["score"], r["recovery_time_hours"]), (59, 1.5))
        self.assertIsNone(gm.summarize_readiness({})["recovery_time_hours"])
        self.assertIsNone(gm.summarize_readiness(None))
        h = gm.summarize_hrv({"hrvSummary": {"lastNightAvg": 69, "baseline": {"balancedLow": 54}}, "hrvReadings": [1, 2]})
        self.assertEqual((h["last_night_avg"], h["baseline"]["balanced_low"], h["reading_count"]), (69, 54, 2))
        self.assertIsNone(gm.summarize_hrv([]))
        self.assertIsNone(gm.summarize_hrv({})["reading_count"])

    def test_sleep(self):
        raw = {"dailySleepDTO": {"sleepTimeSeconds": 28200, "napTimeSeconds": 3240, "deepSleepSeconds": 3600,
                                 "sleepScores": {"overall": {"value": 87, "qualifierKey": "GOOD"}}}}
        r = gm.summarize_sleep(raw)
        self.assertEqual((r["sleep_hours"], r["nap_minutes"], r["deep_minutes"]), (7.83, 54.0, 60.0))
        self.assertEqual(r["score_components"]["overall"], {"value": 87, "qualifier": "GOOD"})
        self.assertIsNone(r["score_components"]["stress"])
        self.assertIsNone(gm.summarize_sleep(None))
        self.assertIsNone(gm.summarize_sleep({})["sleep_hours"])

    def test_scalars_training_and_events(self):
        obj = {"a": {"trainingLoad": 5, "other": 1}, "b": [{"acwrRatio": 1.2}], "c": None}
        self.assertEqual(gm.select_scalars(obj, ("load", "ratio")), {"a.trainingLoad": 5, "b[0].acwrRatio": 1.2})
        self.assertIsNone(gm.select_scalars({"x": 1}, ("zzz",)))
        self.assertEqual(len(gm.select_scalars({f"load{i}": i for i in range(10)}, ("load",), max_fields=3)), 3)
        self.assertIsNone(gm.summarize_training_payload("x"))
        self.assertEqual(gm.summarize_training_payload({"trainingStatus": "OK"}), {"trainingStatus": "OK"})
        ev = gm.summarize_bb_events([{"eventType": "SLEEP", "startTime": 1}, {"eventType": "SLEEP"}, "x", {"zzz": 1}])
        self.assertEqual(ev["event_type_counts"], {"SLEEP": 2})
        self.assertEqual(ev["event_count"], 4)
        self.assertIsNone(gm.summarize_bb_events({}))

    def test_call_optional(self):
        errs = {}
        self.assertEqual(gm.call_optional("ok", lambda: 5, errs), 5)
        self.assertIsNone(gm.call_optional("bad", lambda: 1 / 0, errs))
        self.assertIn("ZeroDivisionError", errs["bad"])


if __name__ == "__main__":
    unittest.main()
