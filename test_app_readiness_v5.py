"""Tests del paquete garmin_recovery (app v5, modelo readiness v3)."""
import json
import math
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from garmin_recovery.config import DEFAULTS, load_config
from garmin_recovery.history import merge, read_table, update_history, write_table
from garmin_recovery.load import compute_load, form_zone
from garmin_recovery.readiness import assess, component_score
from garmin_recovery.records import DAILY_FIELDS, SESSION_FIELDS, aggregate_sessions
from garmin_recovery import stats

TZ = ZoneInfo("Europe/Madrid")
TODAY = date(2026, 10, 17)


def make_daily(days=40, hrv=55.0, rhr=55.0, night=60.0, sleep=7.6, score=80.0, today=None):
    daily = {}
    for i in range(days, 0, -1):
        d = (TODAY - timedelta(days=i)).isoformat()
        wobble = (-1) ** i
        daily[d] = {"date": d, "hrv_ms": hrv + 5 * wobble, "resting_hr": rhr + wobble,
                    "night_hr": night + wobble, "sleep_hours": sleep, "sleep_score": score}
    daily[TODAY.isoformat()] = {"date": TODAY.isoformat(), "hrv_ms": hrv, "resting_hr": rhr,
                                "night_hr": night, "sleep_hours": sleep, "sleep_score": score,
                                **(today or {})}
    return daily


class StatsTests(unittest.TestCase):
    def test_robust_z_ignores_outlier(self):
        ref = [50, 51, 49, 50, 52, 48, 50, 200]
        self.assertAlmostEqual(stats.robust_z(50, ref), 0.0, places=6)

    def test_ewma_converges(self):
        self.assertAlmostEqual(stats.ewma([10.0] * 400, 7)[-1], 10.0, places=3)

    def test_component_score_is_continuous(self):
        self.assertEqual(component_score(0), 75)
        self.assertLess(abs(component_score(-1.0) - component_score(-1.01)), 0.2)
        self.assertEqual(component_score(-10), 0)
        self.assertIsNone(component_score(None))


class ReadinessTests(unittest.TestCase):
    cfg = DEFAULTS

    def test_normal_day_is_green(self):
        res = assess(make_daily(), TODAY.isoformat(), self.cfg)
        self.assertEqual(res["state"], "assessed")
        self.assertEqual(res["zone"], "green")
        self.assertGreaterEqual(res["score"], 70)

    def test_missing_hrv_is_pending_and_never_scores(self):
        daily = make_daily(today={"hrv_ms": None})
        res = assess(daily, TODAY.isoformat(), self.cfg)
        self.assertEqual(res["state"], "pending")
        self.assertIsNone(res["score"])
        self.assertEqual(res["zone"], "unavailable")
        self.assertLessEqual(res["guidance"]["rpe_max"], 6)

    def test_unconfirmed_morning_sleep_is_pending(self):
        morning = {"date": TODAY.isoformat(), "is_definitive": False, "state": "possible_sleep_in_progress"}
        res = assess(make_daily(), TODAY.isoformat(), self.cfg, morning=morning)
        self.assertEqual(res["state"], "pending")
        self.assertTrue(any(r.startswith("sueno_no_confirmado") for r in res["reasons"]))

    def test_short_baseline_never_green(self):
        res = assess(make_daily(days=18), TODAY.isoformat(), self.cfg)
        self.assertEqual(res["state"], "provisional")
        self.assertNotEqual(res["zone"], "green")

    def test_tiny_baseline_has_no_score(self):
        res = assess(make_daily(days=4), TODAY.isoformat(), self.cfg)
        self.assertEqual(res["state"], "pending")
        self.assertIsNone(res["score"])

    def test_single_bad_night_hurts_less_than_bad_week(self):
        one = make_daily()
        one[TODAY.isoformat()]["hrv_ms"] = 40.0
        week = make_daily()
        for i in range(0, 7):
            week[(TODAY - timedelta(days=i)).isoformat()]["hrv_ms"] = 40.0
        s_one = assess(one, TODAY.isoformat(), self.cfg)["components"]["hrv"]["score"]
        s_week = assess(week, TODAY.isoformat(), self.cfg)["components"]["hrv"]["score"]
        self.assertLess(s_week, s_one)
        self.assertEqual(assess(week, TODAY.isoformat(), self.cfg)["components"]["hrv"]["band"], "suprimida")

    def test_poor_recovery_is_red(self):
        daily = make_daily(today={"hrv_ms": 35.0, "resting_hr": 66.0, "night_hr": 72.0,
                                  "sleep_hours": 4.2, "sleep_score": 45.0})
        for i in range(1, 4):
            daily[(TODAY - timedelta(days=i)).isoformat()]["hrv_ms"] = 38.0
        res = assess(daily, TODAY.isoformat(), self.cfg)
        self.assertEqual(res["zone"], "red")
        self.assertLessEqual(res["guidance"]["rpe_max"], 4)

    def test_short_sleep_caps_green(self):
        daily = make_daily(hrv=55, today={"sleep_hours": 4.8, "sleep_score": 95.0, "hrv_ms": 70.0})
        res = assess(daily, TODAY.isoformat(), self.cfg)
        self.assertNotEqual(res["zone"], "green")

    def test_subjective_scale_one_is_best(self):
        good = assess(make_daily(today={"fatigue": 1, "soreness": 1}), TODAY.isoformat(), self.cfg)
        bad = assess(make_daily(today={"fatigue": 4, "soreness": 4}), TODAY.isoformat(), self.cfg)
        self.assertGreater(good["score"], bad["score"])

    def test_night_shift_notes(self):
        daily = make_daily(today={"shift": "TN"})
        res = assess(daily, TODAY.isoformat(), self.cfg)
        self.assertTrue(any("turno de noche" in n for n in res["notes"]))

    def test_output_is_json_serialisable(self):
        json.dumps(assess(make_daily(), TODAY.isoformat(), self.cfg), allow_nan=False)


class LoadTests(unittest.TestCase):
    cfg = DEFAULTS

    def test_low_ctl_form_not_interpreted(self):
        daily = make_daily()
        daily[TODAY.isoformat()].update({"icu_ctl": 3.9, "icu_atl": 15.0})
        load = compute_load(daily, {}, TODAY.isoformat(), self.cfg)
        self.assertFalse(load["form_interpretable"])
        self.assertIsNone(load["component_z"])
        self.assertAlmostEqual(load["tsb"], -11.1)

    def test_form_interpreted_with_enough_ctl(self):
        daily = make_daily()
        daily[TODAY.isoformat()].update({"icu_ctl": 60.0, "icu_atl": 90.0})
        load = compute_load(daily, {}, TODAY.isoformat(), self.cfg)
        self.assertEqual(load["form_pct"], -50.0)
        self.assertEqual(load["form_zone"], "riesgo_alto")
        self.assertLess(load["component_z"], -2)

    def test_form_zones(self):
        self.assertEqual(form_zone(25), "transicion")
        self.assertEqual(form_zone(10), "fresco")
        self.assertEqual(form_zone(0), "neutro")
        self.assertEqual(form_zone(-20), "optimo")

    def test_monotony_and_week_load(self):
        daily = make_daily()
        sessions = {}
        for i in range(7):
            d = (TODAY - timedelta(days=i)).isoformat()
            daily[d]["load"] = 20.0 if i % 2 else 40.0
            sessions[f"s{i}"] = {"id": f"s{i}", "date": d}
        load = compute_load(daily, sessions, TODAY.isoformat(), self.cfg)
        self.assertEqual(load["week_load"], 220.0)
        self.assertIsNotNone(load["monotony"])

    def test_aggregate_sessions_srpe(self):
        agg = aggregate_sessions([
            {"date": "2026-10-10", "duration_min": 60, "load": 30, "srpe": 420},
            {"date": "2026-10-10", "duration_min": 20, "load": 10, "srpe": None},
        ])
        self.assertEqual(agg["2026-10-10"]["load"], 40)
        self.assertEqual(agg["2026-10-10"]["srpe"], 420)
        self.assertEqual(agg["2026-10-10"]["rpe_sessions"], 1)


class HistoryTests(unittest.TestCase):
    def test_merge_never_erases(self):
        old = {"2026-10-01": {"date": "2026-10-01", "hrv_ms": 50.0, "sleep_hours": 7.0}}
        new = {"2026-10-01": {"date": "2026-10-01", "hrv_ms": None, "sleep_hours": 7.5},
               "2026-10-02": {"date": "2026-10-02", "hrv_ms": 55.0}}
        out = merge(old, new)
        self.assertEqual(out["2026-10-01"]["hrv_ms"], 50.0)
        self.assertEqual(out["2026-10-01"]["sleep_hours"], 7.5)
        self.assertIn("2026-10-02", out)

    def test_round_trip_and_upsert(self):
        with tempfile.TemporaryDirectory() as tmp:
            rec = {f: None for f in DAILY_FIELDS} | {"date": "2026-10-01", "hrv_ms": 51.25, "sessions": 2, "shift": "MT"}
            sess = {f: None for f in SESSION_FIELDS} | {"id": "i1", "date": "2026-10-01", "load": 12.0}
            update_history(tmp, {"2026-10-01": rec}, [sess])
            update_history(tmp, {}, [{"id": "i2", "date": "2026-10-02", "load": 5.0}])
            daily = read_table(Path(tmp) / "daily.csv", DAILY_FIELDS, "date")
            sessions = read_table(Path(tmp) / "sessions.csv", SESSION_FIELDS, "id")
            self.assertEqual(daily["2026-10-01"]["hrv_ms"], 51.25)
            self.assertEqual(daily["2026-10-01"]["sessions"], 2)
            self.assertEqual(daily["2026-10-01"]["shift"], "MT")
            self.assertEqual(set(sessions), {"i1", "i2"})

    def test_config_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "app_config.json").write_text('{"sleep_need_hours": 8, "weights": {"hrv": 0.5}}')
            cfg = load_config(tmp)
            self.assertEqual(cfg["sleep_need_hours"], 8)
            self.assertEqual(cfg["weights"]["hrv"], 0.5)
            self.assertEqual(cfg["weights"]["sleep"], DEFAULTS["weights"]["sleep"])


class PipelineOnRepoDataTests(unittest.TestCase):
    """Ejecuta el pipeline completo sobre los datos reales del repositorio, sin escribir."""

    def test_dry_run_on_repo_snapshot(self):
        from garmin_recovery.pipeline import run
        root = Path(__file__).resolve().parent
        if not (root / "garmin_hrv_timeline.json").exists():
            self.skipTest("sin datos publicados")
        with tempfile.TemporaryDirectory() as tmp:
            # Copia mínima para no tocar history/ ni app/ reales
            for name in ("wellness.json", "garmin_hrv_timeline.json", "garmin_sleep_history.json",
                         "garmin_extended.json", "garmin_heart_rate.json", "garmin_stress.json",
                         "garmin_body_battery.json", "activities.json", "training_feedback.json",
                         "shift_calendar.json", "morning_sleep_status.json", "recovery_assessment.json",
                         "recovery.csv"):
                if (root / name).exists():
                    Path(tmp, name).write_bytes((root / name).read_bytes())
            now = datetime.now(TZ)
            res = run(tmp, now=now, write=True)
            self.assertIn(res["readiness"]["state"], ("assessed", "provisional", "pending"))
            self.assertTrue(Path(tmp, "app", "dashboard.html").exists())
            self.assertTrue(Path(tmp, "history", "daily.csv").exists())
            json.loads(Path(tmp, "app", "readiness_v3.json").read_text())
            html = Path(tmp, "app", "dashboard.html").read_text()
            self.assertIn("<title>", html)
            self.assertNotIn("NaN", Path(tmp, "app", "readiness_v3.json").read_text())


if __name__ == "__main__":
    unittest.main()


class QualityTests(unittest.TestCase):
    def test_data_and_recommendation_confidence_are_separate(self):
        res = assess(make_daily(days=40), TODAY.isoformat(), DEFAULTS)
        self.assertEqual(res["data_confidence"]["level"], "alta")
        # Sin validar el modelo, la recomendación nunca pasa de "media"
        self.assertEqual(res["recommendation_confidence"]["level"], "media")
        self.assertFalse(res["recommendation_confidence"]["model_validated"])

    def test_validated_model_can_reach_high_recommendation_confidence(self):
        cfg = load_config("/nonexistent") | {"model_validated": True}
        res = assess(make_daily(days=40), TODAY.isoformat(), cfg)
        self.assertEqual(res["recommendation_confidence"]["level"], "alta")

    def test_missing_today_lowers_data_confidence(self):
        res = assess(make_daily(today={"sleep_hours": None}), TODAY.isoformat(), DEFAULTS)
        self.assertEqual(res["data_confidence"]["level"], "baja")
        self.assertEqual(res["recommendation_confidence"]["level"], "baja")

    def test_training_integrity_matches_by_id(self):
        from garmin_recovery.quality import training_integrity
        sessions = {"a": {"id": "a", "date": "2026-10-16", "rpe": 8.0},
                    "b": {"id": "b", "date": "2026-10-16", "rpe": None, "start_local": "2026-10-16T10:00:00"}}
        feedback = {"activities": {"a": {"date": "2026-10-16", "rpe": 8},
                                   "zzz": {"date": "2026-10-15", "rpe": 7}}}
        out = training_integrity(sessions, feedback, TODAY.isoformat())
        self.assertEqual(out["with_rpe"], 1)
        self.assertEqual([x["id"] for x in out["without_rpe"]], ["b"])
        self.assertEqual(out["rpe_without_activity"], ["zzz"])
        self.assertEqual(out["status"], "revisar")

    def test_consistency_detects_mismatch(self):
        from garmin_recovery.quality import consistency
        rd = {"date": "2026-10-17", "components": {"hrv": {"today_ms": 46.0}, "cardiac": {"resting_hr": 60.0},
                                                   "sleep": {"hours": 7.84}}}
        same = {"current": {"date": "2026-10-17", "hrv_ms": 46.0, "resting_hr": 60.0, "sleep_hours": 7.84}}
        diff = {"current": {"date": "2026-10-17", "hrv_ms": 52.0, "resting_hr": 60.0, "sleep_hours": 7.84}}
        self.assertEqual(consistency(rd, same, 0.05)["status"], "ok")
        self.assertEqual(consistency(rd, diff, 0.05)["status"], "discrepancia")

    def test_data_age_uses_sample_timestamps(self):
        from garmin_recovery.quality import data_age
        now = datetime(2026, 10, 17, 9, 0, tzinfo=TZ)
        inputs = {"sleep": {"days": {"2026-10-17": {"sleep_end_local": "2026-10-17T07:30:00+02:00",
                                                    "window_confirmed": True}}},
                  "hr_timeline": {"days": {"2026-10-17": {"last_sample_local": "2026-10-17T03:00:00+02:00"}}}}
        ages = data_age(inputs, now, TZ)
        self.assertEqual(ages["confirmed_sleep"]["state"], "reciente")
        self.assertEqual(ages["confirmed_sleep"]["age_minutes"], 90)
        self.assertEqual(ages["heart_rate_live"]["state"], "antigua")
        self.assertEqual(ages["sleep_hrv"]["state"], "sin_marca_temporal")
