import json
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from garmin_recovery import garmin_hrv_timeline as ht

TZ = ZoneInfo("Europe/Madrid")
NOW = datetime(2026, 10, 18, 12, 0, tzinfo=TZ)
T0 = 1_792_300_000_000


def raw(readings=(60, 62, 64), avg=62, **k):
    r = {"hrvReadings": [{"readingTimeGMT": T0 + i * 300_000, "hrvValue": v} for i, v in enumerate(readings)],
         "hrvSummary": {"lastNightAvg": avg, "weeklyAvg": 58, "lastNight5MinHigh": 80, "status": "BALANCED",
                        "baseline": {"balancedLow": 54, "balancedUpper": 62}},
         "sleepStartTimestampGMT": T0 - 3_600_000, "sleepEndTimestampGMT": T0 + 3_600_000}
    r.update(k)
    return r


class Parse(unittest.TestCase):
    def test_epoch_and_numbers(self):
        self.assertIsNone(ht.epoch_millis_utc(True))
        self.assertIsNone(ht.epoch_millis_utc(None))
        self.assertEqual(ht.epoch_millis_utc(1_700_000_000), 1_700_000_000_000)
        self.assertIsNone(ht.epoch_millis_utc(5))
        self.assertEqual(ht.epoch_millis_utc("1970-01-01T00:00:01"), 1000)   # sin zona = UTC
        self.assertIsNone(ht.epoch_millis_utc("x"))
        self.assertIsNone(ht.epoch_millis_utc([]))
        self.assertIsNone(ht.local_iso(None))
        self.assertEqual(ht.valid_number(50, 1, 500), 50)
        self.assertIsNone(ht.valid_number(0, 1, 500))
        self.assertIsNone(ht.valid_number(True, 1, 500))

    def test_readings_dedup_sort_and_filter(self):
        r = {"hrvReadings": [{"readingTimeGMT": T0 + 300_000, "hrvValue": 70.5}, {"readingTimeGMT": T0, "hrvValue": 60},
                             {"readingTimeGMT": T0, "hrvValue": 61}, {"readingTimeGMT": "x", "hrvValue": 60},
                             {"readingTimeGMT": T0 + 600_000, "hrvValue": 9999}, "x"]}
        self.assertEqual(ht.parse_hrv_readings(r), [[T0, 61], [T0 + 300_000, 70.5]])
        self.assertEqual(ht.parse_hrv_readings(None), [])

    def test_build_record(self):
        rec = ht.build_record(raw(), date(2026, 10, 18), NOW.isoformat())
        self.assertEqual((rec["sample_count"], rec["night_avg_ms"], rec["garmin_status"]), (3, 62, "BALANCED"))
        self.assertEqual(rec["baseline_ms"], {"balanced_low": 54, "balanced_upper": 62})
        self.assertTrue(rec["last_sample_local"] > rec["first_sample_local"])
        self.assertTrue(ht.has_data(rec))
        empty = ht.build_record({}, "2026-10-18", NOW.isoformat())
        self.assertFalse(ht.has_data(empty))
        self.assertIsNone(empty["first_sample_local"])
        alt = ht.build_record({"startTimestampGMT": T0, "endTimestampGMT": T0 + 1000, "hrvSummary": "x"}, date(2026, 10, 18), "g")
        self.assertIsNotNone(alt["sleep_start_local"])


class Collect(unittest.TestCase):
    def test_dates_to_fetch(self):
        d, cur = ht.dates_to_fetch(date(2026, 10, 18), {}, 0)
        self.assertEqual(d[:2], [date(2026, 10, 18), date(2026, 10, 17)])
        self.assertEqual(len(d), 2 + ht.BACKFILL_PER_RUN)
        self.assertEqual(cur, ht.BACKFILL_PER_RUN)

    def test_collect_keeps_better_previous_and_computes_week(self):
        class Api:
            def get_hrv_data(self, key):
                if key == "2026-10-17":
                    return {"hrvSummary": {"lastNightAvg": 66}}      # sin lecturas
                if key == "2026-10-16":
                    raise RuntimeError("429")
                return raw()
        prev = {"days": {"2026-10-17": {"date": "2026-10-17", "sample_count": 5, "night_avg_ms": 60, "samples": [[1, 1]]}}}
        out = ht.collect(Api(), NOW, prev)
        self.assertEqual(out["days"]["2026-10-17"]["sample_count"], 5)       # conserva las lecturas anteriores
        self.assertEqual(out["days"]["2026-10-17"]["night_avg_ms"], 66)      # pero mejora el resumen
        self.assertEqual(out["days"]["2026-10-18"]["sample_count"], 3)
        self.assertIn("2026-10-16", out["fetch_errors"])
        dates = out["last_7_completed_nights"]["dates"]
        self.assertIn("2026-10-17", dates)
        self.assertNotIn("2026-10-18", dates)     # hoy no cuenta como noche completa

    def test_unavailable_and_store_loading(self):
        class Api:
            def get_hrv_data(self, key):
                return {}
        out = ht.collect(Api(), NOW, {"days": {}})
        self.assertIn("2026-10-18", out["unavailable_dates"])
        self.assertEqual(out["last_7_completed_nights"]["nights_present"], 0)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.json"
            self.assertEqual(ht.load_store(p)["days"], {})
            p.write_text(json.dumps({"days": {"a": 1}}), encoding="utf-8")
            self.assertEqual(ht.load_store(p)["days"], {"a": 1})
            p.write_text("[1]", encoding="utf-8")
            self.assertEqual(ht.load_store(p)["days"], {})


if __name__ == "__main__":
    unittest.main()
