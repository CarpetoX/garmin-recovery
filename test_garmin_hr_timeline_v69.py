import json
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

from garmin_recovery import garmin_hr_timeline as hr

TZ = ZoneInfo("Europe/Madrid")
NOW = datetime(2026, 10, 18, 12, 0, tzinfo=TZ)


def ms(d, h, mi=0):
    return int(datetime(2026, 10, d, h, mi, tzinfo=TZ).timestamp() * 1000)


def hr_raw(day=18):
    return {"heartRateValues": [[ms(day, 1), 50], [ms(day, 2), 52.5], [ms(day, 2), 53], [ms(day, 3), 10], [ms(day, 4), True],
                                [ms(day - 1, 23), 60], "x", [ms(day, 5)]]}


class Extract(unittest.TestCase):
    def test_milliseconds(self):
        self.assertIsNone(hr.to_milliseconds(True))
        self.assertEqual(hr.to_milliseconds(1_700_000_000), 1_700_000_000_000)
        self.assertIsNone(hr.to_milliseconds(12))
        self.assertEqual(hr.to_milliseconds("1970-01-01T00:00:02Z"), 2000)
        self.assertIsNone(hr.to_milliseconds("x"))
        self.assertIsNone(hr.to_milliseconds(None))

    def test_samples_only_local_day_dedup_and_valid(self):
        s = hr.extract_hr_samples(hr_raw(), date(2026, 10, 18))
        self.assertEqual([x[1] for x in s], [50, 53])        # duplicado → último; 10 bpm y True descartados; ayer fuera
        self.assertEqual(hr.extract_hr_samples(None, date(2026, 10, 18)), [])
        self.assertEqual(hr.extract_hr_samples(hr_raw(), "2026-10-17")[0][1], 60)

    def test_sleep_window_and_record(self):
        raw = {"dailySleepDTO": {"sleepStartTimestampGMT": ms(18, 0), "sleepEndTimestampGMT": ms(18, 8)}}
        w = hr.extract_sleep_window(raw)
        self.assertTrue(w["start_local"].startswith("2026-10-18T00:00") and w["end_local"].startswith("2026-10-18T08:00"))
        self.assertIsNone(hr.extract_sleep_window({"dailySleepDTO": {"sleepStartTimestampGMT": 5, "sleepEndTimestampGMT": 1}}))
        self.assertIsNone(hr.extract_sleep_window([]))
        rec = hr.make_day_record(hr_raw(), date(2026, 10, 18), NOW.isoformat(), [w, dict(w), "x"], partial_day=True)
        self.assertEqual((rec["sample_count"], rec["partial_day"], len(rec["sleep_windows_local"])), (2, True, 1))
        empty = hr.make_day_record({}, "2026-10-18", "g")
        self.assertIsNone(empty["first_sample_local"])


class Collect(unittest.TestCase):
    def test_dates_to_fetch(self):
        d = hr.dates_to_fetch(date(2026, 10, 18), {"2026-10-15": {}})
        self.assertEqual(d[:2], [date(2026, 10, 18), date(2026, 10, 17)])
        self.assertNotIn(date(2026, 10, 15), d)
        self.assertEqual(len(d), 2 + hr.BACKFILL_PER_RUN)

    def test_collect(self):
        class Api:
            def get_heart_rates(self, key):
                if key == "2026-10-16":
                    raise RuntimeError("429")
                if key == "2026-10-17":
                    return {}
                return hr_raw(int(key[-2:]))

            def get_sleep_data(self, key):
                if key == "2026-10-19":
                    raise RuntimeError("x")
                return {"dailySleepDTO": {"sleepStartTimestampGMT": ms(int(key[-2:]), 0), "sleepEndTimestampGMT": ms(int(key[-2:]), 8)}}
        prev = {"days": {"2026-10-17": {"sample_count": 9}, "2026-01-01": {}}}
        out = hr.collect(Api(), NOW, prev)
        self.assertTrue(out["days"]["2026-10-18"]["partial_day"])
        self.assertEqual(out["days"]["2026-10-17"], {"sample_count": 9})   # datos previos conservados
        self.assertIn("2026-10-17", out["fetch_errors"])
        self.assertIn("2026-10-16", out["fetch_errors"])
        self.assertNotIn("2026-01-01", out["days"])

    def test_load_store(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.json"
            with mock.patch.object(hr, "FILE", p):
                self.assertEqual(hr.load_store()["days"], {})
                p.write_text(json.dumps({"days": {"a": 1}}), encoding="utf-8")
                self.assertEqual(hr.load_store()["days"], {"a": 1})


if __name__ == "__main__":
    unittest.main()
