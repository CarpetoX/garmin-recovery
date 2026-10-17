"""Tests de las correcciones de la auditoría (V5.7): un test por hallazgo."""
import json
import shutil
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from garmin_recovery.config import DEFAULTS
from garmin_recovery.decision import CROSSFIT, operative_decision, operative_zone
from garmin_recovery.readiness import GUIDANCE, assess

TZ = ZoneInfo("Europe/Madrid")
ROOT = Path(__file__).resolve().parent
TODAY = date(2026, 10, 17)


def decide(v2, hybrid, v3, v2_state="assessed", v3_state="assessed", v2_date="2026-10-17", ds_date="2026-10-17"):
    return operative_decision({"zone": v3, "state": v3_state, "score": 60, "model_version": "v3"},
                              {"status": v2, "state": v2_state, "score": 45, "current": {"date": v2_date}},
                              {"date": ds_date, "readiness_hybrid": {"status": hybrid, "score": 36}},
                              5, GUIDANCE, False, today="2026-10-17")


class F1RedBeatsPending(unittest.TestCase):
    def test_red_prevails_over_pending(self):
        d = decide("red", "red", "unavailable", v3_state="pending")
        self.assertEqual(d["zone"], "red")
        self.assertEqual(d["guidance"]["rpe_max"], 4)

    def test_pending_without_red_stays_pending(self):
        self.assertEqual(decide("green", "yellow", "unavailable", v3_state="pending")["zone"], "unavailable")
        self.assertEqual(decide("green", None, "green")["zone"], "unavailable")

    def test_order_matches_guidance_strictness(self):
        zones = ["red", "unavailable", "yellow", "green"]
        caps = [GUIDANCE[z]["rpe_max"] for z in zones]
        self.assertEqual(caps, sorted(caps))
        self.assertEqual(operative_zone([None, "red"]), "red")


class F12StaleModels(unittest.TestCase):
    def test_v2_from_yesterday_does_not_decide(self):
        d = decide("green", "green", "green", v2_date="2026-10-16")
        self.assertEqual(d["zone"], "unavailable")
        self.assertIn("recovery_assessment_v2", d["missing_models"])

    def test_stale_but_red_elsewhere_is_red(self):
        self.assertEqual(decide("green", "red", "green", v2_date="2026-10-16")["zone"], "red")


class ValidatorFixes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from garmin_recovery.pipeline import run
        if not (ROOT / "garmin_hrv_timeline.json").exists():
            raise unittest.SkipTest("sin datos")
        cls.base = tempfile.TemporaryDirectory()
        for p in list(ROOT.glob("*.json")) + list(ROOT.glob("*.csv")):
            Path(cls.base.name, p.name).write_bytes(p.read_bytes())
        cls.now = datetime.now(TZ)
        cls.result = run(cls.base.name, now=cls.now)

    @classmethod
    def tearDownClass(cls):
        cls.base.cleanup()

    def copy(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        shutil.copytree(self.base.name, tmp, dirs_exist_ok=True)
        return Path(tmp)

    def test_json_and_report_from_different_runs_fail(self):
        from garmin_recovery.validate import validate
        d = self.copy()
        p = d / "app" / "readiness_v3.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        gen = datetime.fromisoformat(data["generated_at"]) + timedelta(hours=3)
        data["generated_at"] = gen.isoformat()
        p.write_text(json.dumps(data), encoding="utf-8")
        errs = validate(d)["errors"]
        self.assertTrue(any("no corresponde a este JSON" in e for e in errs), errs)

    def test_guidance_must_match_zone(self):
        from garmin_recovery.validate import validate
        d = self.copy()
        p = d / "app" / "readiness_v3.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        data["decision"]["guidance"] = dict(GUIDANCE["green"])
        p.write_text(json.dumps(data), encoding="utf-8")
        self.assertIn("json: la pauta no corresponde a la zona de la decisión", validate(d)["errors"])

    def test_stale_output_fails_with_max_age(self):
        from garmin_recovery.validate import validate
        self.assertEqual(validate(self.base.name, max_age_minutes=60, now=self.now + timedelta(minutes=10))["status"], "ok")
        res = validate(self.base.name, max_age_minutes=60, now=self.now + timedelta(hours=5))
        self.assertTrue(any("generada hace" in e for e in res["errors"]))

    def test_sessions_chart_uses_full_window(self):
        from garmin_recovery.report import chart_sessions
        window = [s for s in self.result["sessions_28d"]
                  if s["date"] >= (date.fromisoformat(self.result["date"]) - timedelta(days=13)).isoformat() and s.get("load")]
        svg = chart_sessions(self.result["sessions_28d"], self.result["date"])
        legend = sum(1 for c in ("WOD", "Fuerza", "Halterofilia", "Técnica", "Sin detalle") if f">{c}<" in svg)
        shapes = svg.count('<path d="M') + svg.count("<rect x=") - legend
        self.assertEqual(shapes, len(window))


def daily_with(hrv_values):
    daily = {}
    n = len(hrv_values)
    for i, v in enumerate(hrv_values):
        d = (TODAY - timedelta(days=n - 1 - i)).isoformat()
        daily[d] = {"date": d, "hrv_ms": v, "resting_hr": 55.0, "night_hr": 60.0, "sleep_hours": 7.6, "sleep_score": 80.0}
    return daily


class F6RobustHrv(unittest.TestCase):
    def test_single_outlier_does_not_widen_normal_range(self):
        base = [(52, 54, 55, 56, 58)[i % 5] for i in range(30)]
        clean = assess(daily_with(base), TODAY.isoformat(), DEFAULTS)["components"]["hrv"]
        dirty_vals = list(base)
        dirty_vals[5] = 20
        dirty = assess(daily_with(dirty_vals), TODAY.isoformat(), DEFAULTS)["components"]["hrv"]
        width = lambda h: h["normal_high_ms"] - h["normal_low_ms"]
        self.assertLess(abs(width(dirty) - width(clean)), 0.2 * width(clean))


class F7F8Load(unittest.TestCase):
    def build(self, days, srpe=300.0, load=20.0):
        from garmin_recovery.load import compute_load
        daily, sessions = {}, {}
        for i in range(days):
            d = (TODAY - timedelta(days=i)).isoformat()
            daily[d] = {"date": d, "load": load, "srpe": srpe, "sessions": 1}
            sessions[f"s{i}"] = {"id": f"s{i}", "date": d, "rpe": 6.0}
        return compute_load(daily, sessions, TODAY.isoformat(), DEFAULTS)

    def test_constant_load_gives_acwr_one_without_startup_bias(self):
        load = self.build(28)
        self.assertAlmostEqual(load["acwr"], 1.0, places=2)
        self.assertEqual(load["acwr_basis"], "srpe_media_7_vs_28")

    def test_monotony_uses_srpe(self):
        load = self.build(10)
        self.assertEqual(load["internal_load_basis"], "srpe_foster")
        self.assertIsNone(load["monotony"])  # sRPE constante: sin variación definida

    def test_seeded_ewma_is_unbiased(self):
        from garmin_recovery.stats import ewma
        self.assertAlmostEqual(ewma([50.0] * 10, 42, seed=50.0)[-1], 50.0)
        self.assertLess(ewma([50.0] * 10, 42)[-1], 15)


class F9OlympicConsistency(unittest.TestCase):
    def test_same_percentage_everywhere(self):
        from garmin_recovery.planned import adjust
        txt = " ".join(CROSSFIT["yellow"])
        self.assertIn("80 %", txt)
        self.assertNotIn("70 %", txt)
        self.assertIn("80 %", adjust({"type": "Halterofilia", "activity": "x"}, "yellow", 7)["adjusted"])


class MinorFixes(unittest.TestCase):
    def test_plan_parsing(self):
        from garmin_recovery import planned as pl
        self.assertEqual(pl.parse_load_spec("80 % 1RM"), {"kind": "percent", "values": [80.0]})
        self.assertEqual(pl.parse_load_spec("2x20")["kind"], "per_implement")
        self.assertEqual(pl.parse_loads("150,160"), [150.0, 160.0])
        self.assertEqual(pl.parse_loads("167,5"), [167.5])
        self.assertEqual(pl.parse_rpe("7-8"), 7.0)
        self.assertEqual([pl.reduced_sets(n) for n in (1, 2, 3, 4, 5)], [1, 1, 2, 3, 4])
        adj = pl.adjust({"type": "Fuerza", "activity": "x", "format": "5x3", "load_text": "80 % 1RM", "rpe_target": "7-8"}, "green", 9)
        self.assertEqual(adj["rpe_max"], 7)
        self.assertIn("80 % 1RM", adj["planned"])
        self.assertNotIn("1RM kg", adj["planned"])
        self.assertIn("150–160 kg", pl.adjust({"type": "Fuerza", "activity": "x", "load_text": "150–160"}, "green", 9)["planned"])
        self.assertNotIn("kg kg", pl.adjust({"type": "Fuerza", "activity": "x", "load_text": "100 kg"}, "green", 9)["planned"])
        self.assertNotIn("kg", pl.adjust({"type": "Fuerza", "activity": "x", "load_text": "80 % 1RM"}, "yellow", 7)["adjusted"].split("intensidad")[1].split(";")[0])

    def test_removed_sessions_flagged_and_excluded(self):
        from garmin_recovery.history import flag_removed_sessions, recompute_daily_load
        sessions = {"a": {"id": "a", "date": "2026-10-10", "load": 10.0},
                    "b": {"id": "b", "date": "2026-10-12", "load": 30.0},
                    "c": {"id": "c", "date": "2026-10-14", "load": 5.0}}
        fresh = [{"id": "a", "date": "2026-10-10"}, {"id": "c", "date": "2026-10-14"}]
        flag_removed_sessions(sessions, fresh)
        self.assertEqual(sessions["b"]["removed"], 1)
        self.assertEqual(sessions["a"]["removed"], 0)
        daily = {"2026-10-12": {"date": "2026-10-12", "load": 30.0}}
        recompute_daily_load(daily, sessions)
        self.assertIsNone(daily["2026-10-12"]["load"])
        self.assertEqual(flag_removed_sessions({"x": {"id": "x", "date": "2026-10-12"}}, [])["x"].get("removed"), None)

    def test_now_with_other_offset_uses_madrid_date(self):
        from garmin_recovery.pipeline import run
        if not (ROOT / "garmin_hrv_timeline.json").exists():
            self.skipTest("sin datos")
        with tempfile.TemporaryDirectory() as tmp:
            for p in list(ROOT.glob("*.json")) + list(ROOT.glob("*.csv")):
                Path(tmp, p.name).write_bytes(p.read_bytes())
            res = run(tmp, now=datetime(2026, 10, 17, 23, 30, tzinfo=ZoneInfo("UTC")), write=False)
            self.assertEqual(res["date"], "2026-10-18")

    def test_provisional_threshold_is_configurable(self):
        daily = daily_with([(52, 54, 55, 56, 58)[i % 5] for i in range(30)])
        cfg = dict(DEFAULTS, provisional_below_n=40)
        self.assertEqual(assess(daily, TODAY.isoformat(), cfg)["state"], "provisional")
        self.assertNotIn("mature_baseline_n", DEFAULTS)


class ReviewFixes(unittest.TestCase):
    """Hallazgos de la revisión independiente del PR."""

    def test_acwr_needs_rpe_history_not_just_sessions(self):
        from garmin_recovery.load import compute_load
        daily, sessions = {}, {}
        for i in range(35):
            d = (TODAY - timedelta(days=i)).isoformat()
            has_rpe = i < 7
            daily[d] = {"date": d, "load": 20.0, "srpe": 300.0 if has_rpe else 0.0, "sessions": 1}
            sessions[f"s{i}"] = {"id": f"s{i}", "date": d, "rpe": 6.0 if has_rpe else None}
        load = compute_load(daily, sessions, TODAY.isoformat(), DEFAULTS)
        self.assertIsNone(load["acwr"])
        self.assertNotEqual(load["component_basis"], "acwr")

    def test_monotony_needs_rpe_coverage(self):
        from garmin_recovery.load import compute_load
        daily, sessions = {}, {}
        for i in range(7):
            d = (TODAY - timedelta(days=i)).isoformat()
            has_rpe = i < 3
            daily[d] = {"date": d, "load": 20.0, "srpe": (200.0 + 50 * i) if has_rpe else 0.0, "sessions": 1}
            sessions[f"s{i}"] = {"id": f"s{i}", "date": d, "rpe": 6.0 if has_rpe else None}
        self.assertIsNone(compute_load(daily, sessions, TODAY.isoformat(), DEFAULTS)["monotony"])

    def test_percent_ignores_sets_and_reps(self):
        from garmin_recovery.planned import parse_load_spec
        self.assertEqual(parse_load_spec("80% x3")["values"], [80.0])
        self.assertEqual(parse_load_spec("3x2 @ 85 %")["values"], [85.0])
        self.assertEqual(parse_load_spec("75-80 %")["values"], [75.0, 80.0])

    def test_stale_model_score_not_recorded_as_today(self):
        d = decide("green", "green", "green", v2_date="2026-10-16")
        v2 = next(m for m in d["registry"] if m["id"] == "recovery_assessment_v2")
        self.assertIsNone(v2["score"])
        self.assertEqual(v2["stale_score"], 45)

    def test_stale_red_still_caps(self):
        d = decide("red", "green", "green", v2_date="2026-10-16")
        self.assertEqual(d["zone"], "red")
        self.assertEqual(d["guidance"]["rpe_max"], 4)


if __name__ == "__main__":
    unittest.main()
