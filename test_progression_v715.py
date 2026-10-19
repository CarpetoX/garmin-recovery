import json
import unittest
from pathlib import Path

from garmin_recovery import dashboard, progression as pg


def act(date, aid, exercises, rpe=7):
    return {"activity_id": aid, "date": date, "manual_blocks": [{"activity": "Fuerza", "rpe": rpe,
            "detail_json": {"type": "strength", "exercises": exercises, "rpe": rpe}}]}


def squat(*sets, unit="kg_total_barra"):
    return {"name": "Sentadilla trasera", "load_unit": unit, "sets": [{"reps": r, "load_kg": k} for r, k in sets]}


CF = {"activities": [
    act("2026-10-09", "a1", [squat((2, 160), (2, 170))]),
    act("2026-10-18", "a2", [{"name": "sentadilla  trasera", "load_unit": "kg_total_barra",
                              "sets": [{"reps": 10, "load_kg": 20, "bar_empty": True}, {"reps": 1, "load_kg": 185}]},
                             {"name": "Peso muerto", "load_unit": "kg_total_barra", "sets": [{"reps": 5, "load_kg": None}, {"reps": 1, "load_kg": 180}]}]),
]}


class Extract(unittest.TestCase):
    def test_names_are_normalised_and_bar_is_skipped(self):
        entries, seen = pg.extract_entries(CF)
        self.assertEqual(seen, {"a1", "a2"})
        sq = [e for e in entries.values() if e["key"] == "sentadilla trasera"]
        self.assertEqual(len(sq), 2)
        last = max(sq, key=lambda e: e["date"])
        self.assertEqual((last["top_load"], last["top_reps"], last["volume"], last["work_sets"]), (185.0, 1.0, 185.0, 1))

    def test_unknown_load_marks_volume_incomplete(self):
        entries, _ = pg.extract_entries(CF)
        dl = [e for e in entries.values() if e["key"] == "peso muerto"][0]
        self.assertFalse(dl["volume_complete"])

    def test_skips_metcon_warmup_and_bodyweight(self):
        cf = {"activities": [{"activity_id": "m", "date": "2026-10-10", "manual_blocks": [
            {"detail_json": {"type": "metcon", "exercises": [{"name": "thruster", "load_unit": "kg", "sets": [{"reps": 5, "load_kg": 20}]}]}},
            {"detail_json": {"type": "strength", "exercises": [{"name": "Fondos", "load_unit": "peso_corporal", "sets": [{"reps": 8, "load_kg": 90}]},
                                                               {"name": "Complejo calentamiento", "load_unit": "kg_total_barra", "sets": [{"reps": 1, "load_kg": 40}]}]}}]}]}
        self.assertEqual(pg.extract_entries(cf)[0], {})


class Compare(unittest.TestCase):
    def test_series_and_verdict(self):
        b = pg.build(None, CF)
        s = [x for x in b["items"] if x["name"].lower().startswith("sentadilla")][0]
        self.assertTrue(s["comparable"])
        self.assertEqual((s["state"], s["delta_prev"], s["new_best"]), ("up", 15.0, True))
        self.assertFalse(s["rep_scheme_differs"])  # 2 → 1 repeticiones: menos de 2 de diferencia
        dl = [x for x in b["items"] if x["name"] == "Peso muerto"][0]
        self.assertFalse(dl["comparable"])
        self.assertEqual(b["summary"]["comparable"], 1)
        self.assertIn("1 ejercicio con más de una sesión", b["summary"]["text"])

    def test_history_survives_when_activity_leaves_window_and_is_replaced_when_corrected(self):
        first = pg.build(None, CF)["entries"]
        later = {"activities": [act("2026-11-20", "a9", [squat((1, 190))])]}
        merged = pg.build({"entries": first}, later)
        self.assertEqual(len([e for e in merged["entries"].values() if e["key"] == "sentadilla trasera"]), 3)
        fixed = {"activities": [act("2026-10-09", "a1", [squat((2, 165))])]}
        again = pg.build({"entries": merged["entries"]}, fixed)
        tops = sorted(e["top_load"] for e in again["entries"].values() if e["activity_id"] == "a1")
        self.assertEqual(tops, [165.0])

    def test_no_comparable_summary(self):
        b = pg.build(None, {"activities": [act("2026-10-09", "a1", [squat((2, 160))])]})
        self.assertFalse(b["summary"]["available"])
        self.assertIsNone(b["summary"]["text"])


class Html(unittest.TestCase):
    def test_card(self):
        b = pg.build(None, CF)
        html = dashboard._progression_html({"items": b["items"], "summary": b["summary"]})
        self.assertIn('aria-label="Progresión por ejercicio"', html)
        self.assertIn("Sentadilla trasera", html)
        self.assertIn("sube +15 kg", html)
        self.assertIn("Todavía sin repetir (1)", html)
        self.assertEqual(dashboard._progression_html(None), "")

    def test_in_dashboard(self):
        res = json.loads((Path(__file__).resolve().parent / "app" / "readiness_v3.json").read_text(encoding="utf-8"))
        b = pg.build(None, CF)
        html = dashboard.render(res, {"progression": {"items": b["items"], "summary": b["summary"]}})
        self.assertIn('id="progresion"', html)
        self.assertNotIn('id="progresion"', dashboard.render(res, {}))


if __name__ == "__main__":
    unittest.main()
