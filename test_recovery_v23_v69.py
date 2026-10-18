import base64
import json
import unittest

from garmin_recovery import recovery_v23 as r


def b64(obj):
    return base64.b64encode(json.dumps(obj).encode()).decode()


def assessment(**k):
    a = {"status": "green", "score": 88, "work_shift_context": "", "sleep_context": "night_sleep",
         "current": {"date": "2026-10-18", "sleep_hours": 7.8, "sleep_score": 87,
                     "sleep_start_local": "2026-10-18T00:00:00+02:00", "sleep_end_local": "2026-10-18T08:00:00+02:00"}}
    a.update(k)
    return a


def ev(start_gmt, minutes, kind="SLEEP"):
    return {"event.eventType": kind, "event.eventStartTimeGmt": start_gmt, "event.durationInMilliseconds": minutes * 60000}


class Helpers(unittest.TestCase):
    def test_as_local(self):
        self.assertIsNone(r._as_local(None))
        self.assertIsNone(r._as_local("basura"))
        self.assertIsNone(r._as_local(0))
        self.assertEqual(r._as_local(86400).year, 1970)
        naive = "2026-10-18T10:00:00"
        self.assertEqual(r._as_local(naive).hour, 10)
        self.assertEqual(r._as_local(naive, utc_if_naive=True).hour, 12)

    def test_number(self):
        self.assertIsNone(r._number(True, 0, 5))
        self.assertIsNone(r._number("x", 0, 5))
        self.assertIsNone(r._number(9, 0, 5))
        self.assertEqual(r._number("3", 0, 5), 3.0)


class Integrity(unittest.TestCase):
    def test_side_episode_vs_overlap(self):
        ext = {"days": {"2026-10-18": {"body_battery_events": {"events": [
            ev("2026-10-18T14:00:00", 60),            # 16:00-17:00 local: episodio aparte
            ev("2026-10-18T03:00:00", 60),            # solapa con el principal
            ev("2026-10-18T15:00:00", 5),             # demasiado corto
            ev("2026-10-18T16:00:00", 60, "NAP"), "x"]}}}}
        out = r.sleep_integrity(assessment(), ext)
        self.assertEqual((out["unconfirmed_separate_events"], out["unconfirmed_separate_minutes"], out["overlapping_body_battery_events"]),
                         (1, 60, 1))
        self.assertEqual(out["minutes_added_to_sleep"], 0)
        self.assertTrue(out["main_sleep_confirmed"])
        self.assertEqual(out["main_sleep_minutes"], 468)

    def test_without_data(self):
        a = assessment()
        a["current"] = {"date": "2026-10-18"}
        out = r.sleep_integrity(a, {})
        self.assertFalse(out["main_sleep_confirmed"])
        self.assertIsNone(out["main_sleep_minutes"])


class ScoreAudit(unittest.TestCase):
    def test_flags(self):
        a = assessment()
        far = {"days": {"2026-10-18": {"training_readiness": {"sleep_score": 60}}}}
        self.assertEqual(r.score_source_audit(a, {}, far)["status"], "different_fields_not_interchangeable")
        near = {"days": {"2026-10-18": {"training_readiness": {"sleep_score": 85}}}}
        self.assertEqual(r.score_source_audit(a, {}, near)["status"], "close_values")
        self.assertEqual(r.score_source_audit(a, {}, {})["status"], "missing_comparison")
        daily = {"garmin_metrics": {"training_readiness": {"sleep_score": 86}}}
        self.assertEqual(r.score_source_audit(a, daily, {})["status"], "close_values")


class Checkin(unittest.TestCase):
    def test_read(self):
        good = {"2026-10-18": {"sleepiness": 1, "physical_fatigue": 2, "headache": 3, "headache_usual": True}}
        self.assertEqual(r._read_checkin("2026-10-18", b64(good)), (1.0, 2.0, 3.0, True))
        self.assertIsNone(r._read_checkin("2026-10-17", b64(good)))
        self.assertIsNone(r._read_checkin("2026-10-18", ""))
        self.assertIsNone(r._read_checkin("2026-10-18", "%%%no-base64"))
        bad = {"2026-10-18": {"sleepiness": 9, "physical_fatigue": 2, "headache": 3, "headache_usual": True}}
        self.assertIsNone(r._read_checkin("2026-10-18", b64(bad)))
        nobool = {"2026-10-18": {"sleepiness": 1, "physical_fatigue": 2, "headache": 3, "headache_usual": "si"}}
        self.assertIsNone(r._read_checkin("2026-10-18", b64(nobool)))
        self.assertIsNone(r._read_checkin("2026-10-18", b64([1])))


class Enhance(unittest.TestCase):
    def test_invalid(self):
        with self.assertRaises(ValueError):
            r.enhance_assessment("x", {}, {})

    def test_clean_day_unchanged(self):
        out = r.enhance_assessment(assessment(), {}, {})
        self.assertEqual((out["status"], out["score"]), ("green", 88))
        self.assertEqual(out["v23"]["intensity_guardrail"], "use_v22_guidance")
        self.assertEqual(out["v23"]["subjective_checkin"], "not_provided")

    def test_post_tn_short_sleep_blocks_green(self):
        a = assessment(work_shift_context="post-TN")
        a["current"]["sleep_hours"] = 4.5
        out = r.enhance_assessment(a, {}, {})
        self.assertEqual((out["status"], out["score"]), ("yellow", 74))
        self.assertEqual(out["v23"]["raw_score_before_guardrail"], 88)
        self.assertIn("green_clearance_blocked", out["v23"]["reason_codes"])
        self.assertIn("short_sleep", out["v23"]["reason_codes"])
        self.assertEqual(out["v23"]["intensity_guardrail"], "avoid_maximum")
        self.assertIn("evitar cargas máximas", out["recommendation"])

    def test_private_checkin_guardrail_and_red(self):
        chk = {"2026-10-18": {"sleepiness": 3, "physical_fatigue": 0, "headache": 0, "headache_usual": False}}
        out = r.enhance_assessment(assessment(), {}, {}, checkin_encoded=b64(chk))
        self.assertEqual(out["status"], "yellow")
        self.assertIn("private_subjective_guardrail", out["v23"]["reason_codes"])
        self.assertFalse(out["v23"]["subjective_values_exported"])
        red = r.enhance_assessment(assessment(status="red"), {}, {})
        self.assertEqual(red["status"], "red")
        self.assertEqual(red["v23"]["intensity_guardrail"], "avoid_maximum")

    def test_day_sleep_baseline_caution(self):
        a = assessment(sleep_context="day_sleep", baseline_28d={"hrv_ms": {"scope": "overall"}})
        self.assertEqual(r.enhance_assessment(a, {}, {})["v23"]["baseline_caution"], "day_sleep_baseline_not_mature")


if __name__ == "__main__":
    unittest.main()
