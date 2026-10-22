import unittest

from garmin_recovery import progression, training_blocks as tb


def _act(aid, date, blocks, rpe=8.0):
    return {"activity_id": aid, "date": date, "rpe_used": rpe, "recorded_minutes": 12.0,
            "manual_blocks": [{"activity": b.get("title", "x"), "detail_json": b} for b in blocks]}


STRENGTH = {"type": "strength", "title": "Fuerza pierna", "rpe": 7,
            "exercises": [{"name": "sentadilla trasera", "load_unit": "kg_total_barra",
                           "sets": [{"reps": 5, "load_kg": 100}, {"reps": 5, "load_kg": 100}, {"reps": 3, "load_kg": 120}]}]}
OLY = {"type": "strength", "title": "Halterofilia", "rpe": 8,
       "exercises": [{"name": "squat clean", "load_unit": "kg_total_barra", "sets": [{"reps": 1, "load_kg": 90, "count": 2}, {"reps": 1, "load_kg": 95}]}]}
EMOM = {"type": "metcon", "format": "EMOM", "rpe": 9, "recorded_garmin_minutes": 11.8,
        "prescribed_round": [{"name": "Echo Bike", "calories": "16/12"}, {"name": "squat clean", "reps": "máximas", "load_kg": 70}, {"name": "descanso", "minutes": 1}],
        "performed": {"rounds_complete": 4, "rounds": [{"round": i + 1, "squat_clean_reps": r} for i, r in enumerate([9, 6, 5, 4])],
                      "totals": {"squat_clean_reps": 24}}}
PARTNER = {"type": "metcon", "format": "3 Rounds For Time", "partner_workout": True, "rpe": 8, "rounds_completed": 3,
           "time_cap_seconds": 1080, "finish_time_seconds": 808, "garmin_recorded_seconds": 795,
           "rounds": [{"round": 1, "machine": "SkiErg", "calories_shared": 40, "burpee_sync_reps": 20}]}
SKILL = {"type": "skill", "exercise": "toes to bar", "rpe": 1}
CF = {"activities": [_act("a1", "2026-10-19", [OLY, EMOM]), _act("a2", "2026-10-18", [STRENGTH]),
                     _act("a3", "2026-10-15", [PARTNER]), _act("a4", "2026-10-19", [SKILL], 1.0)]}


class TrainingBlocks(unittest.TestCase):
    def setUp(self):
        self.entries, _ = progression.extract_entries(CF)
        self.r = tb.build(CF, self.entries, "2026-10-19")

    def test_olympic_classification(self):
        self.assertTrue(tb.is_olympic("Power clean + squat clean (complex 1+1)"))
        self.assertTrue(tb.is_olympic("squat snatch"))
        self.assertFalse(tb.is_olympic("sentadilla trasera"))
        self.assertFalse(tb.is_olympic("press de pecho"))

    def test_lifts_split(self):
        self.assertEqual([e["name"] for s in self.r["fuerza"]["sessions"] for e in s["exercises"]], ["sentadilla trasera"])
        self.assertEqual([e["name"] for s in self.r["halterofilia"]["sessions"] for e in s["exercises"]], ["squat clean"])
        self.assertEqual(self.r["fuerza"]["sessions"][0]["rpe"], 8.0)

    def test_sets_text_and_volume(self):
        ex = self.r["fuerza"]["sessions"][0]["exercises"][0]
        self.assertIn("5 @ 100", ex["sets"])
        self.assertEqual(ex["volume"], 5 * 100 * 2 + 3 * 120)
        self.assertEqual(self.r["halterofilia"]["weekly"][-1]["volume"], 90 * 2 + 95)

    def test_weekly_trims_empty_history_but_keeps_three(self):
        self.assertGreaterEqual(len(self.r["fuerza"]["weekly"]), 3)
        self.assertTrue(self.r["halterofilia"]["weekly"][-1]["current"])

    def test_metcon_emom_rounds(self):
        m = next(m for m in self.r["metcons"] if m["format"] == "EMOM")
        self.assertEqual(m["rounds"]["values"], [9.0, 6.0, 5.0, 4.0])
        self.assertIn("24 squat clean", m["result"])
        self.assertEqual(m["rpe"], 9)
        self.assertNotIn("descanso", " ".join(m["prescription"]))

    def test_metcon_keeps_official_and_watch_times(self):
        m = next(m for m in self.r["metcons"] if m["partner"])
        self.assertIn("Oficial 13:28", m["timing"])
        self.assertIn("Reloj 13:15", m["timing"])
        self.assertIn("Cap 18:00", m["timing"])
        self.assertTrue(any("40 cal compartidas" in x for x in m["prescription"]))

    def test_skill_and_warmup_not_counted(self):
        self.assertEqual(len(self.r["metcons"]), 2)
        self.assertEqual(self.r["otros"][0]["kind"], "skill")
        self.assertEqual(self.r["summary7"]["metcons"], 2)
        self.assertEqual(self.r["summary7"]["metcon_rpe_mean"], 8.5)

    def test_empty_inputs(self):
        r = tb.build(None, None, "2026-10-19")
        self.assertEqual(r["metcons"], [])
        self.assertEqual(r["summary7"]["fuerza"], 0)

    def test_no_rounds_chart_when_all_equal(self):
        d = {"performed": {"rounds": [{"x_reps": 5}] * 4}}
        self.assertIsNone(tb._round_series(d))




class OthersPaneV729(unittest.TestCase):
    """V7.29: ninguna actividad del registro queda fuera de Entrenos."""

    def test_every_activity_has_a_card(self):
        import json
        from pathlib import Path

        from garmin_recovery import progression, training_blocks
        root = Path(__file__).resolve().parent
        cf = json.loads((root / "crossfit_insights.json").read_text(encoding="utf-8"))
        hist = json.loads((root / "exercise_history.json").read_text(encoding="utf-8"))
        tb = training_blocks.build(cf, progression.build(hist, cf)["entries"], "2026-10-22")
        shown = {str(x["activity_id"]) for k in ("fuerza", "halterofilia") for x in tb[k]["sessions"]}
        shown |= {str(m["activity_id"]) for m in tb["metcons"]} | {o["activity_id"] for o in tb["otros"]}
        self.assertEqual({str(a["activity_id"]) for a in cf["activities"]} - shown, set())
        self.assertTrue(all(o["kind"] in ("warmup", "skill", "other") for o in tb["otros"]))

    def test_pane_renders_with_hr_slot(self):
        from garmin_recovery.dashboard import _others_html
        out = _others_html([{"date": "2026-10-19", "activity_id": "i9", "kind": "skill", "title": "Técnica - toes to bar",
                             "rpe": None, "minutes": 47.68, "note": "Sin RPE"}])
        self.assertIn("Técnica", out)
        self.assertIn("RPE —", out)
        self.assertIn("47,7 min", out)
        self.assertIn('data-id="i9"', out)


if __name__ == "__main__":
    unittest.main()
