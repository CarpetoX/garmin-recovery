import base64
import json
import os
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from garmin_recovery import recovery_v231 as r

TZ = ZoneInfo("Europe/Madrid")
NOW = datetime(2026, 10, 18, 11, 0, tzinfo=TZ)


def b64(obj):
    return base64.b64encode(json.dumps(obj).encode()).decode()


def assessment(**k):
    a = {"status": "green", "state": "assessed", "confidence": "high", "score": 88, "work_shift_context": "", "sleep_context": "night_sleep",
         "current": {"date": "2026-10-18", "sleep_hours": 7.8, "sleep_score": 87, "sources": {"sleep_hours": "garmin_sleep_history"},
                     "sleep_start_local": "2026-10-18T00:00:00+02:00", "sleep_end_local": "2026-10-18T08:00:00+02:00"}}
    a.update(k)
    return a


SOURCES = {
    "sleep": {"days": {"2026-10-18": {"window_confirmed": True}}},
    "hrv": {"days": {"2026-10-18": {"last_sample_local": "2026-10-18T07:30:00+02:00"}}},
    "heart_timeline": {"days": {"2026-10-18": {"last_sample_local": "2026-10-18T10:50:00+02:00"}}},
    "battery": {"days": {"2026-10-18": {"bodyBatteryValuesArray": [[1792310000000, 70]]}}},
    "feedback": {"activities": {}},
}


class Helpers(unittest.TestCase):
    def test_time_and_number(self):
        self.assertIsNone(r._time(None))
        self.assertIsNone(r._time(""))
        self.assertIsNone(r._time("x"))
        self.assertEqual(r._time("2026-10-18T10:00:00").hour, 10)
        self.assertEqual(r._time("2026-10-18T10:00:00", utc_if_naive=True).hour, 12)
        self.assertEqual(r._time(86400).year, 1970)
        self.assertIsNone(r._number(True))
        self.assertIsNone(r._number(" "))
        self.assertIsNone(r._number(99, 0, 10))
        self.assertEqual(r._number("2"), 2.0)

    def test_json_and_day(self):
        self.assertEqual(r._json("/no/existe.json"), {})
        self.assertEqual(r._day({"days": {"d": {"a": 1}}}, "d"), {"a": 1})
        self.assertEqual(r._day({"days": {"d": 5}}, "d"), {})
        self.assertEqual(r._day(None, "d"), {})

    def test_observed_states(self):
        ts = NOW - timedelta(minutes=30)
        self.assertEqual(r._observed(ts, NOW)["state"], "recent")
        self.assertEqual(r._observed(NOW - timedelta(minutes=120), NOW)["state"], "delayed")
        self.assertEqual(r._observed(NOW - timedelta(minutes=300), NOW)["state"], "old_measurement")
        self.assertEqual(r._observed(NOW + timedelta(minutes=60), NOW)["state"], "future_timestamp")
        self.assertEqual(r._observed(None, NOW)["state"], "unverified_timestamp")


class Provenance(unittest.TestCase):
    def test_healthy(self):
        p = r.measurement_provenance(assessment(), NOW, SOURCES, {})
        self.assertFalse(p["invalid_core_episode"])
        self.assertEqual(p["sources"]["confirmed_sleep"]["garmin_episode_confirmed"], True)
        self.assertEqual(p["sources"]["heart_rate_live"]["state"], "recent")

    def test_invalid_window_and_unverified(self):
        a = assessment()
        a["current"]["sleep_end_local"] = "2026-10-17T20:00:00+02:00"
        p = r.measurement_provenance(a, NOW, SOURCES, {})
        self.assertTrue(p["invalid_core_episode"])
        self.assertEqual(p["sources"]["confirmed_sleep"]["state"], "invalid_sleep_window")
        src = dict(SOURCES, sleep={"days": {}})
        p2 = r.measurement_provenance(assessment(), NOW, src, {})
        self.assertEqual(p2["sources"]["confirmed_sleep"]["state"], "time_known_confirmation_unverified")

    def test_hrv_outside_sleep_and_delayed_battery(self):
        src = dict(SOURCES, hrv={"days": {"2026-10-18": {"last_sample_local": "2026-10-18T10:00:00+02:00"}}})
        p = r.measurement_provenance(assessment(), NOW, src, {"garmin_metrics": {"body_battery": {"latest_sample_timestamp": 1792300000000}}})
        self.assertEqual(p["sources"]["sleep_hrv"]["state"], "sample_outside_sleep")
        self.assertTrue(p["invalid_core_episode"])
        self.assertTrue(p["live_data_limited"])
        self.assertIn("body_battery_live", p["limited_live_metrics"])


class Context(unittest.TestCase):
    def test_private_checkin(self):
        old = os.environ.get("RECOVERY_CHECKIN_B64")
        try:
            os.environ["RECOVERY_CHECKIN_B64"] = b64({"2026-10-18": {"sleepiness": 1}})
            self.assertEqual(r._private_checkin("2026-10-18"), {"sleepiness": 1})
            self.assertIsNone(r._private_checkin("2026-10-17"))
            os.environ["RECOVERY_CHECKIN_B64"] = "%%%"
            self.assertIsNone(r._private_checkin("2026-10-18"))
            os.environ["RECOVERY_CHECKIN_B64"] = ""
            self.assertIsNone(r._private_checkin("2026-10-18"))
        finally:
            if old is None:
                os.environ.pop("RECOVERY_CHECKIN_B64", None)
            else:
                os.environ["RECOVERY_CHECKIN_B64"] = old

    def test_naps(self):
        naps = [{"start_local": "2026-10-18T15:00:00+02:00", "end_local": "2026-10-18T16:00:00+02:00"},
                {"start_local": "2026-10-18T15:30:00+02:00", "end_local": "2026-10-18T16:30:00+02:00"},   # solapa con la anterior
                {"start_local": "2026-10-18T02:00:00+02:00", "end_local": "2026-10-18T03:00:00+02:00"},   # solapa con el principal
                {"start_local": "2026-10-18T20:00:00+02:00", "end_local": "2026-10-19T08:00:00+02:00"},   # >6 h
                "x"]
        out = r.sleep_context(assessment(), {"naps": naps})
        self.assertEqual(out["validation"], "accepted")
        self.assertTrue(out["reported_naps_excluded_from_core_score"])
        self.assertEqual(r.sleep_context(assessment(), None)["validation"], "not_supplied_or_not_verified")

    def test_subjective_flags(self):
        self.assertEqual(r._subjective_flags(None), (False, False))
        self.assertEqual(r._subjective_flags({"sleepiness": 1}), (True, False))
        self.assertEqual(r._subjective_flags({"physical_fatigue": 3}), (True, True))
        self.assertEqual(r._subjective_flags({"headache": 4, "headache_usual": False}), (True, True))
        self.assertEqual(r._subjective_flags({"headache": 4, "headache_usual": True}), (True, False))
        self.assertEqual(r._subjective_flags({}), (False, False))


class Guidance(unittest.TestCase):
    def test_levels(self):
        self.assertEqual(r.session_guidance(assessment(), {"count": 2, "high_count": 1})["guidance_level"], "individualize")
        self.assertEqual(r.session_guidance(assessment(status="yellow"), {})["guidance_level"], "conservative")
        self.assertEqual(r.session_guidance(assessment(confidence="low"), {})["guidance_level"], "conservative")
        self.assertEqual(r.session_guidance(assessment(status="red"), {})["guidance_level"], "restrict")
        self.assertEqual(r.session_guidance(assessment(state="pending"), {})["guidance_level"], "restrict")
        g = assessment()
        g["v23"] = {"intensity_guardrail": "avoid_maximum"}
        self.assertEqual(r.session_guidance(g, {})["guidance_level"], "restrict")

    def test_recent_rpe(self):
        fb = {"activities": {"a": {"date": "2026-10-17", "rpe": 9}, "b": {"date": "2026-10-16", "rpe": 5},
                             "c": {"date": "2026-10-10", "rpe": 9}, "d": "x", "e": {"date": "2026-10-18", "rpe": 11}}}
        self.assertEqual(r.recent_rpe_summary("2026-10-18", fb), {"count": 2, "high_count": 1})
        self.assertEqual(r.recent_rpe_summary("2026-10-18", {"activities": []}), {"count": 0, "high_count": 0})


class Enhance(unittest.TestCase):
    def test_healthy_keeps_green(self):
        out = r.enhance_assessment(assessment(), {}, {}, NOW, sources=SOURCES)
        self.assertEqual(out["status"], "green")
        self.assertEqual(out["methodology_version"], "recovery-reliability-v2.3.1")
        self.assertEqual(out["v23"]["training_guidance"]["guidance_level"], "individualize")

    def test_invalid_core_goes_pending(self):
        a = assessment()
        a["current"]["sleep_end_local"] = "2026-10-17T20:00:00+02:00"
        out = r.enhance_assessment(a, {}, {}, NOW, sources=SOURCES)
        self.assertEqual((out["state"], out["status"], out["score"]), ("pending", "unavailable", None))
        self.assertEqual(out["v23"]["intensity_guardrail"], "avoid_maximum")

    def test_private_symptoms_block_green_and_env_restored(self):
        chk = b64({"2026-10-18": {"sleepiness": 3, "physical_fatigue": 0, "headache": 0, "headache_usual": True}})
        before = os.environ.get("RECOVERY_CHECKIN_B64")
        out = r.enhance_assessment(assessment(), {}, {}, NOW.replace(tzinfo=None), sources=SOURCES, checkin_encoded=chk)
        self.assertEqual(os.environ.get("RECOVERY_CHECKIN_B64"), before)
        self.assertEqual((out["status"], out["score"]), ("yellow", 74))
        self.assertIn("private_guardrail", out["v23"]["reason_codes"])
        self.assertFalse(out["v23"]["subjective_values_exported"])

    def test_live_limited_reason(self):
        src = dict(SOURCES, heart_timeline={"days": {}})
        out = r.enhance_assessment(assessment(), {}, {}, NOW, sources=src)
        self.assertIn("live_measurement_uncertain", out["v23"]["reason_codes"])


if __name__ == "__main__":
    unittest.main()
