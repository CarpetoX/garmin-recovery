"""V8.13: benchmarks, máximos estimados, gimnasia, historial de carga, intensidad, tipo de día y tramos sugeridos."""
import unittest

from garmin_recovery import athlete_progress as ap, dashboard_v813 as v, recovery_context as rc, split_detect as sd


def row(d, name, detail, rpe="8", id_="i1"):
    return {"date": d, "id": id_, "name": name, "rpe": rpe, "notes": "", "detail": detail}


class Benchmarks(unittest.TestCase):
    def test_repeated_identical_wod_is_benchmark(self):
        rows = [row("2026-10-01", "WOD Fran", {"type": "metcon", "finish_time_seconds": 300}),
                row("2026-10-20", "WOD Fran", {"type": "metcon", "finish_time_seconds": 280}),
                row("2026-10-21", "WOD único", {"type": "metcon", "performed": {"total_reps": 100}})]
        b = ap.benchmarks(rows)
        self.assertEqual([x["name"] for x in b], ["WOD Fran"])
        self.assertEqual(b[0]["state"], "up")  # menos tiempo = mejora
        self.assertTrue(b[0]["is_best"])

    def test_marked_benchmark_shows_even_once(self):
        b = ap.benchmarks([row("2026-10-01", "Chin up máximo", {"benchmark": "Chin up lastrado 1RM", "benchmark_load_kg": 32.5})])
        self.assertEqual(b[0]["name"], "Chin up lastrado 1RM")
        self.assertIsNone(b[0]["state"])

    def test_capped_for_time_uses_reps(self):
        d = {"type": "metcon", "finish_time_seconds": 600, "performed": {"completed": False, "total_reps": 153, "rounds_complete": 3, "extra_reps": 18}}
        value, better, text = ap._result(d)
        self.assertEqual((value, better), (153, "higher"))
        self.assertIn("3 rondas + 18", text)


class Maxes(unittest.TestCase):
    def test_epley_lower_bound_and_real_single(self):
        entries = {"a": {"date": "2026-10-08", "exercise": "peso muerto", "unit": "kg_total_barra",
                         "sets": [{"reps": 5, "load": 170}, {"reps": 1, "load": 180}, {"reps": 15, "load": 100}]},
                   "b": {"date": "2026-10-09", "exercise": "complex clean + jerk", "unit": "kg_total_barra", "sets": [{"reps": 1, "load": 90}]},
                   "c": {"date": "2026-10-09", "exercise": "chin up lastrado", "unit": "lastre_kg", "sets": [{"reps": 4, "load": 15}]}}
        m = ap.estimated_max(entries)
        self.assertEqual(len(m), 1)  # sin complex ni lastre
        self.assertEqual(m[0]["e1rm"], 198.5)
        self.assertEqual(m[0]["single"], 180)
        self.assertIn("198,5", v.maxes_html(m))


class Skills(unittest.TestCase):
    def test_milestones_and_technique(self):
        rows = [row("2026-10-29", "Hito - primer bar muscle up", {"type": "skill", "milestone": "Primer bar muscle up",
                                                                  "performed": {"reps": 4, "unbroken": False}}, rpe=""),
                row("2026-10-26", "Técnica - toes to bar", {"type": "skill", "exercise": "toes to bar"}, rpe=""),
                row("2026-10-26", "Calentamiento", {"type": "warmup"}, rpe="")]
        s = ap.skills(rows)
        self.assertEqual([x["kind"] for x in s], ["hito", "tecnica"])
        self.assertEqual(s[0]["sub"], "4 repeticiones sueltas")
        self.assertIn("🏅", v.skills_html(s))


class LoadHistory(unittest.TestCase):
    def test_short_history_note(self):
        lh = ap.load_history(["2026-10-06", "2026-10-30"], "2026-10-30")
        self.assertFalse(lh["reliable"])
        self.assertIn("25 días", lh["note"])
        self.assertIsNone(ap.load_history(["2026-08-01"], "2026-10-30")["note"])


class Intensity(unittest.TestCase):
    def test_hard_and_easy_counts_skip_weeks_before_data(self):
        s = [{"date": "2026-10-26", "rpe": "9"}, {"date": "2026-10-26", "rpe": ""}, {"date": "2026-10-27", "rpe": "4"},
             {"date": "2026-10-28", "rpe": "8"}, {"date": "2026-10-28", "rpe": "7"}]
        w = rc.weekly_intensity(s, "2026-10-30")
        self.assertEqual(len(w), 1)
        self.assertEqual((w[0]["sessions"], w[0]["scored"], w[0]["hard"], w[0]["hard_pct"]), (5, 4, 2, 50))
        self.assertEqual(w[0]["easy_days"], 3)  # 27 (RPE 4), 29 y 30 sin sesión
        self.assertIn("Suaves", v.intensity_html({"weekly": w}))


class DayTypes(unittest.TestCase):
    def test_post_tn_classification_and_minimum_days(self):
        shifts = {"2026-10-01": "TN", "2026-10-03": "MT"}
        self.assertEqual(rc.day_type("2026-10-02", shifts), "post_tn")
        self.assertEqual(rc.day_type("2026-10-01", shifts), "tn")
        self.assertEqual(rc.day_type("2026-10-03", shifts), "mt")
        self.assertEqual(rc.day_type("2026-10-04", shifts), "libre")
        daily = [{"date": f"2026-10-{d:02d}", "v3_score": "60", "hrv_ms": "50", "sleep_hours": "7"} for d in range(4, 10)]
        out = rc.by_day_type(daily, [], shifts, "2026-10-30")
        libre = next(r for r in out["rows"] if r["type"] == "libre")
        self.assertTrue(libre["enough"])
        self.assertFalse(next(r for r in out["rows"] if r["type"] == "tn")["enough"])

    def test_today_flags_post_tn_and_over_max_yesterday(self):
        t = rc.today_context({"date": "2026-10-30"}, [{"date": "2026-10-29", "decision_zone": "red"}],
                             [{"date": "2026-10-29", "rpe": "8"}], {"2026-10-29": "TN"})
        self.assertEqual(t["type"], "post_tn")
        self.assertEqual(t["over_yesterday"], {"rpe": 8.0, "max": 4})
        self.assertIn("Post-TN", v.today_html({"today": t}))


class Splits(unittest.TestCase):
    def curve(self):
        pts = [[t, 95] for t in range(0, 1800, 10)] + [[t, 160] for t in range(1800, 2400, 10)]
        return {"i9": {"available": True, "date": "2026-10-30", "type": "HighIntensityIntervalTraining", "points": pts}}

    def test_sharp_change_is_proposed(self):
        p = sd.propose(self.curve(), [row("2026-10-30", "Técnica - HSPU", {}, id_="i9")], "2026-10-30")
        self.assertEqual(p[0]["cut_mmss"], "30:00")

    def test_not_proposed_if_already_split_or_ramp_or_run(self):
        rows = [row("2026-10-30", "a", {"segment": {}}, id_="i9"), row("2026-10-30", "b", {"segment": {}}, id_="i9")]
        self.assertEqual(sd.propose(self.curve(), rows, "2026-10-30"), [])
        ramp = [[t, 100 + t / 40] for t in range(0, 2400, 10)]
        self.assertIsNone(sd.change_point(ramp))
        c = self.curve()
        c["i9"]["type"] = "Run"
        self.assertEqual(sd.propose(c, [row("2026-10-30", "x", {}, id_="i9")], "2026-10-30"), [])


if __name__ == "__main__":
    unittest.main()
