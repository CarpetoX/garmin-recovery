import unittest
from datetime import date, datetime
from zoneinfo import ZoneInfo

from garmin_recovery import garmin_sleep_history as sh

TZ = ZoneInfo("Europe/Madrid")
NOW = datetime(2026, 10, 18, 12, 0, tzinfo=TZ)


def ms(y, mo, d, h, mi=0):
    return int(datetime(y, mo, d, h, mi, tzinfo=TZ).timestamp() * 1000)


def dto(start, end, secs=27000, **k):
    d = {"sleepStartTimestampGMT": start, "sleepEndTimestampGMT": end, "sleepTimeSeconds": secs,
         "sleepWindowConfirmed": True, "deepSleepSeconds": 3600, "remSleepSeconds": 5400,
         "sleepScores": {"overall": {"value": 87}}}
    d.update(k)
    return {"dailySleepDTO": d}


NIGHT = dto(ms(2026, 10, 18, 0, 30), ms(2026, 10, 18, 8, 0))


class Helpers(unittest.TestCase):
    def test_number_and_epoch(self):
        self.assertIsNone(sh.n(True))
        self.assertIsNone(sh.n(float("nan")))
        self.assertIsNone(sh.n(5, 10, 20))
        self.assertEqual(sh.n(15, 10, 20), 15.0)
        self.assertEqual(sh.epoch_ms(1_700_000_000_000), 1_700_000_000_000)
        self.assertEqual(sh.epoch_ms(1_700_000_000), 1_700_000_000_000)
        self.assertIsNone(sh.epoch_ms(12345))
        self.assertIsNone(sh.epoch_ms(True))
        self.assertEqual(sh.epoch_ms("1970-01-01T00:00:01Z"), 1000)
        self.assertIsNone(sh.epoch_ms("nada"))
        self.assertIsNone(sh.epoch_ms([]))
        self.assertIsNone(sh.local_time("nada"))
        self.assertTrue(sh.local_time(ms(2026, 10, 18, 8, 0)).startswith("2026-10-18T08:00:00"))


class Extract(unittest.TestCase):
    def test_night_sleep(self):
        r = sh.extract_sleep(NIGHT, date(2026, 10, 18), NOW.isoformat())
        self.assertEqual((r["sleep_hours"], r["sleep_score"], r["sleep_context"]), (7.5, 87, "night_sleep"))
        self.assertEqual((r["deep_minutes"], r["rem_minutes"]), (60.0, 90.0))
        self.assertTrue(r["window_confirmed"])

    def test_day_sleep_after_night_shift(self):
        raw = dto(ms(2026, 10, 18, 8, 0), ms(2026, 10, 18, 11, 30), secs=11000)
        self.assertEqual(sh.extract_sleep(raw, date(2026, 10, 18), NOW.isoformat())["sleep_context"], "day_sleep")

    def test_rejections(self):
        gen = NOW.isoformat()
        self.assertIsNone(sh.extract_sleep(None, date(2026, 10, 18), gen))
        self.assertIsNone(sh.extract_sleep({"dailySleepDTO": "x"}, date(2026, 10, 18), gen))
        self.assertIsNone(sh.extract_sleep(dto(None, None), date(2026, 10, 18), gen))
        self.assertIsNone(sh.extract_sleep(dto(ms(2026, 10, 18, 0), ms(2026, 10, 18, 8), secs=100), date(2026, 10, 18), gen))
        # sueño en curso: termina después de "ahora - 5 min"
        self.assertIsNone(sh.extract_sleep(dto(ms(2026, 10, 18, 9), ms(2026, 10, 18, 12, 2)), date(2026, 10, 18), gen))
        # ventana sin confirmar
        self.assertIsNone(sh.extract_sleep(dto(ms(2026, 10, 18, 0), ms(2026, 10, 18, 8), sleepWindowConfirmed=False), date(2026, 10, 18), gen))
        # sueño efectivo mayor que el tiempo transcurrido
        self.assertIsNone(sh.extract_sleep(dto(ms(2026, 10, 18, 0), ms(2026, 10, 18, 2), secs=30000), date(2026, 10, 18), gen))

    def test_naive_generated_at(self):
        r = sh.extract_sleep(NIGHT, date(2026, 10, 18), "2026-10-18T12:00:00")
        self.assertIsNotNone(r)


class FakeApi:
    def __init__(self, sleep=None, hrv=None, fail=False):
        self.sleep, self.hrv, self.fail, self.calls = sleep or {}, hrv or {}, fail, []

    def get_sleep_data(self, key):
        self.calls.append(("sleep", key))
        if self.fail:
            raise RuntimeError("429")
        return self.sleep.get(key)

    def get_hrv_data(self, key):
        if self.fail:
            raise RuntimeError("429")
        return self.hrv.get(key)


class Collect(unittest.TestCase):
    def test_choose_dates_rotation(self):
        days, cursor = sh.choose_dates(date(2026, 10, 18), {}, 0)
        self.assertEqual(days[:2], [date(2026, 10, 18), date(2026, 10, 17)])
        self.assertEqual(len(days), 2 + sh.BACKFILL_PER_RUN)
        self.assertEqual(cursor, sh.BACKFILL_PER_RUN)
        days2, _ = sh.choose_dates(date(2026, 10, 18), {}, cursor)
        self.assertNotEqual(days[2:], days2[2:])

    def test_collect_merges_and_prunes(self):
        api = FakeApi(sleep={"2026-10-18": NIGHT}, hrv={"2026-10-18": {"hrvSummary": {"lastNightAvg": 69}}})
        old = {"days": {"2026-01-01": {"sleep_hours": 7}, "2026-10-17": {"sleep_hours": 6.0, "hrv_ms": 50.0}}, "backfill_cursor": 0}
        out = sh.collect(api, NOW, old)
        row = out["days"]["2026-10-18"]
        self.assertEqual((row["sleep_hours"], row["hrv_ms"]), (7.5, 69.0))
        self.assertNotIn("2026-01-01", out["days"])          # fuera de retención
        self.assertEqual(out["days"]["2026-10-17"]["sleep_hours"], 6.0)  # se conserva si no hay dato nuevo
        self.assertEqual(out["fetch_errors"], {})

    def test_collect_records_errors_without_raising(self):
        out = sh.collect(FakeApi(fail=True), NOW, None)
        self.assertTrue(out["fetch_errors"])
        self.assertTrue(all("RuntimeError" in v for v in out["fetch_errors"].values()))
        self.assertEqual(out["days"], {})


if __name__ == "__main__":
    unittest.main()
