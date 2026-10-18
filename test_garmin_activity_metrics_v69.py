import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from garmin_recovery import garmin_activity_metrics as am


class Identify(unittest.TestCase):
    def test_id_date_type(self):
        self.assertEqual(am.activity_id_of({"activityId": 7}), 7)
        self.assertEqual(am.activity_id_of({"id": 8}), 8)
        self.assertIsNone(am.activity_id_of("x"))
        self.assertEqual(am.activity_date_of({"startTimeLocal": "2026-10-18 10:30:00"}), "2026-10-18")
        self.assertEqual(am.activity_date_of({"calendarDate": "2026-10-17"}), "2026-10-17")
        self.assertIsNone(am.activity_date_of({"startTimeLocal": "x"}))
        self.assertIsNone(am.activity_date_of(None))
        self.assertEqual(am.activity_type_key({"activityType": {"typeKey": "strength_training"}}), "strength_training")
        self.assertEqual(am.activity_type_key({"activityType": "run"}), "run")
        self.assertIsNone(am.activity_type_key({"activityType": ""}))
        self.assertIsNone(am.activity_type_key(3))

    def test_strength_detection(self):
        self.assertTrue(am.looks_like_strength_activity({"activityType": {"typeKey": "strength_training"}}))
        self.assertTrue(am.looks_like_strength_activity({"activityName": "CrossFit WOD"}))
        self.assertTrue(am.looks_like_strength_activity({"totalSets": 5}))
        self.assertFalse(am.looks_like_strength_activity({"activityName": "Paseo", "totalSets": 0}))
        self.assertFalse(am.looks_like_strength_activity(None))


def sets_payload():
    ex = lambda n: [{"name": n, "category": "SQUAT"}]  # noqa: E731
    return {"exerciseSets": [
        {"setType": "ACTIVE", "duration": 30, "repetitionCount": 5, "weight": 100000, "exercises": ex("BACK_SQUAT")},
        {"setType": "ACTIVE", "duration": 30, "repetitionCount": 3, "weight": 120000, "exercises": ex("BACK_SQUAT")},
        {"setType": "REST", "duration": 90, "exercises": []},
        {"setType": "ACTIVE", "duration": None, "repetitionCount": None, "exercises": "mal"},
        "x",
    ]}


class Sets(unittest.TestCase):
    def test_summary(self):
        r = am.summarize_exercise_sets(sets_payload())
        self.assertEqual((r["total_sets"], r["active_sets"], r["rest_sets"]), (5, 3, 1))
        self.assertEqual(r["total_reps"], 8)
        self.assertEqual(r["volume_kg"], 860.0)
        self.assertEqual(r["work_minutes"], 1.0)
        self.assertEqual(r["rest_minutes"], 1.5)
        sq = r["exercises"]["BACK_SQUAT"]
        self.assertEqual((sq["sets"], sq["reps"], sq["volume_kg"], sq["max_weight_kg"]), (2, 8, 860.0, 120.0))
        self.assertIn("UNKNOWN", r["exercises"])

    def test_invalid(self):
        self.assertIsNone(am.summarize_exercise_sets(None))
        self.assertIsNone(am.summarize_exercise_sets({"exerciseSets": "x"}))


class Activity(unittest.TestCase):
    def test_merge_load(self):
        merged = am.merge_activity_load({"activityTrainingLoad": None, "aerobicTrainingEffect": 3.0},
                                        {"activityTrainingLoad": 80, "aerobicTrainingEffect": 9, "trainingEffectLabel": "TEMPO"})
        self.assertEqual((merged["activityTrainingLoad"], merged["aerobicTrainingEffect"], merged["trainingEffectLabel"]), (80, 3.0, "TEMPO"))
        self.assertEqual(am.merge_activity_load({"a": 1}, None), {"a": 1})
        self.assertEqual(am.merge_activity_load(None, {"x": 1}), {})

    def test_summarize_activity_and_day(self):
        a = am.summarize_activity({"activityId": 1, "activityName": "WOD", "duration": 3600, "movingDuration": 3000,
                                   "averageHR": 140, "aerobicTrainingEffect": 3.1, "activityTrainingLoad": 90.04,
                                   "activityType": {"typeKey": "strength_training"}}, {"x": 1})
        self.assertEqual((a["duration_minutes"], a["moving_minutes"], a["activity_type"], a["exercise_sets"]), (60.0, 50.0, "strength_training", {"x": 1}))
        self.assertIsNone(am.summarize_activity(None))
        self.assertIsNone(am.summarize_activity({"activityType": "x"})["activity_type"])
        b = am.summarize_activity({"activityId": 2, "activityTrainingLoad": 10, "anaerobicTrainingEffect": 2.0})
        day = am.summarize_activity_day([a, b, "x"])
        self.assertEqual(day["activity_count"], 2)
        self.assertEqual(day["total_training_load"], 100.0)
        self.assertEqual((day["max_aerobic_training_effect"], day["max_anaerobic_training_effect"]), (3.1, 2.0))
        empty = am.summarize_activity_day([])
        self.assertIsNone(empty["total_training_load"])

    def test_status_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "garmin_status.json"
            with mock.patch.object(am, "STATUS_PATH", p):
                am.update_status(True, days_present=3)
                data = am.load_json(p, {})
                self.assertTrue(data["activity_metrics_available"])
                self.assertEqual(data["activity_metrics_days_present"], 3)
                am.update_status(False, error="boom", set_errors={"1": "x"})
                data = am.load_json(p, {})
                self.assertEqual((data["activity_metrics_error"], data["activity_strength_set_errors"]), ("boom", {"1": "x"}))
                p.write_text("[1]", encoding="utf-8")
                am.update_status(True)
                self.assertTrue(am.load_json(p, {})["activity_metrics_available"])
            self.assertEqual(am.load_json(Path(d) / "no.json", 5), 5)
            self.assertTrue(os.path.isdir(d))


if __name__ == "__main__":
    unittest.main()
