"""Validación prospectiva de modelos (V5.8)."""
import tempfile
import unittest
from pathlib import Path

from garmin_recovery import backtest as bt
from garmin_recovery.config import DEFAULTS
from garmin_recovery.report import categorize, validation_block


def result(day, v2=60, v3=55, zone="yellow", trained=False, gen="T08:40:00+02:00"):
    return {"date": day, "generated_at": day + gen,
            "decision": {"zone": zone, "guidance": {"rpe_max": 7},
                         "registry": [{"id": "recovery_assessment_v2", "score": v2, "zone": zone},
                                      {"id": "readiness_hybrid", "score": 50, "zone": zone},
                                      {"id": "readiness_v3", "score": v3, "zone": "yellow"}]},
            "readiness": {"state": "assessed"},
            "sessions_28d": [{"date": day}] if trained else []}


class RecordPrediction(unittest.TestCase):
    def test_updates_until_training_then_freezes(self):
        rows = bt.record_prediction({}, result("2026-10-20", v2=40), "mañana")
        rows = bt.record_prediction(rows, result("2026-10-20", v2=62), "mañana")  # sueño confirmado
        self.assertEqual(rows["2026-10-20"]["v2_score"], 62)
        rows = bt.record_prediction(rows, result("2026-10-20", v2=30, trained=True), "tarde")
        self.assertEqual(rows["2026-10-20"]["v2_score"], 62)  # se conserva la previa al entrenamiento
        self.assertEqual(rows["2026-10-20"]["frozen"], 1)
        rows = bt.record_prediction(rows, result("2026-10-20", v2=10, trained=True), "noche")
        self.assertEqual(rows["2026-10-20"]["v2_score"], 62)

    def test_first_run_after_training_is_flagged_and_excluded(self):
        rows = bt.record_prediction({}, result("2026-10-20", trained=True), "noche")
        self.assertEqual(rows["2026-10-20"]["after_training"], 1)
        sessions = {"a": {"id": "a", "date": "2026-10-20", "srpe": 400, "load": 20, "rpe": 8, "name": "WOD"}}
        ev = bt.evaluate(rows, {}, sessions, "2026-10-20", DEFAULTS, categorize)
        self.assertEqual(ev["training_days"], 0)

    def test_csv_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "h" / "model_predictions.csv"
            bt.write_predictions(p, bt.record_prediction({}, result("2026-10-20"), "mañana"))
            self.assertEqual(bt.read_predictions(p)["2026-10-20"]["v3_score"], "55")


class Stats(unittest.TestCase):
    def test_spearman_perfect_and_ties(self):
        self.assertEqual(bt.spearman([(i, -i) for i in range(10)])["rho"], -1.0)
        self.assertEqual(bt._ranks([3, 1, 1, 2]), [4.0, 1.5, 1.5, 3.0])
        self.assertIsNone(bt.spearman([(1, 1)] * 4))
        self.assertIsNone(bt.spearman([(1, i) for i in range(8)]))  # sin variación en x

    def test_effort_standardised_within_session_type(self):
        sessions = {}
        for i in range(6):  # WOD: carga alta y sRPE moderado; fuerza: carga baja y sRPE alto
            sessions[f"w{i}"] = {"date": f"2026-10-{10 + i:02d}", "name": "WOD", "srpe": 300 + 10 * i, "load": 60}
            sessions[f"f{i}"] = {"date": f"2026-10-{10 + i:02d}", "name": "Fuerza", "srpe": 300 + 10 * i, "load": 6}
        e = bt.effort_by_day(sessions, categorize)
        self.assertLess(abs(e["2026-10-10"] - e["2026-10-15"] * -1), 0.5)  # simétrico: sin sesgo por tipo
        sessions["x"] = {"date": "2026-10-16", "name": "Halterofilia", "srpe": 100, "load": 5}
        self.assertNotIn("2026-10-16", bt.effort_by_day(sessions, categorize))  # < 5 de su tipo


class Evaluate(unittest.TestCase):
    def build(self, n, v3_tracks_effort=True):
        rows, sessions = {}, {}
        for i in range(n):
            d = f"2026-11-{1 + i:02d}"
            effort = (i % 7) - 3
            v3 = 70 - 8 * effort if v3_tracks_effort else 55 + ((i // 7) * 5) % 20
            rows[d] = bt.prediction_row(result(d, v2=55 + (i * 13) % 20, v3=v3), "mañana", False)
            for k in range(2):
                sessions[f"s{i}{k}"] = {"date": d, "name": "WOD", "rpe": 7,
                                        "srpe": round(300 * (2.718 ** (0.2 * effort))), "load": 40}
        return rows, sessions

    def test_no_verdict_before_minimum(self):
        rows, sessions = self.build(10)
        ev = bt.evaluate(rows, {}, sessions, "2026-11-30", DEFAULTS, categorize)
        self.assertEqual(ev["status"], "acumulando")
        self.assertIn("10/20", ev["verdict"])

    def test_v3_better_when_it_tracks_effort(self):
        rows, sessions = self.build(25)
        ev = bt.evaluate(rows, {}, sessions, "2026-11-30", DEFAULTS, categorize)
        v3 = next(m for m in ev["models"] if m["id"] == "v3")
        self.assertLess(v3["effort"]["rho"], -0.9)
        self.assertEqual(ev["status"], "v3_mejor")

    def test_unrelated_v3_is_not_promoted(self):
        rows, sessions = self.build(25, v3_tracks_effort=False)
        self.assertIn(bt.evaluate(rows, {}, sessions, "2026-11-30", DEFAULTS, categorize)["status"],
                      ("v3_no_probado", "v3_util"))
        self.assertNotEqual(bt.evaluate(rows, {}, sessions, "2026-11-30", DEFAULTS, categorize)["status"], "v3_mejor")

    def test_days_over_cap(self):
        rows, sessions = self.build(3)
        sessions["s00"]["rpe"] = 9  # cap 7
        self.assertEqual(bt.evaluate(rows, {}, sessions, "2026-11-30", DEFAULTS, categorize)["days_over_cap"], 1)

    def test_report_block(self):
        rows, sessions = self.build(25)
        md = "\n".join(validation_block(bt.evaluate(rows, {}, sessions, "2026-11-30", DEFAULTS, categorize)))
        self.assertIn("## Validación de modelos", md)
        self.assertIn("| v3 (en pruebas) |", md)
        self.assertEqual(validation_block(None), [])


class ReviewFindings(unittest.TestCase):
    build = Evaluate.build

    def test_gate_uses_v3_days_and_common_days(self):
        rows, sessions = self.build(25)
        for i, d in enumerate(sorted(rows)):
            if i >= 6:
                rows[d]["v3_score"] = None  # v3 pendiente casi siempre
        ev = bt.evaluate(rows, {}, sessions, "2026-11-30", DEFAULTS, categorize)
        self.assertEqual(ev["status"], "acumulando")
        self.assertEqual(ev["paired"]["n"], 6)

    def test_missing_v2_does_not_make_v3_better(self):
        rows, sessions = self.build(25)
        for d in rows:
            rows[d]["v2_score"] = 60  # sin variación: no hay correlación del v2
        self.assertNotEqual(bt.evaluate(rows, {}, sessions, "2026-11-30", DEFAULTS, categorize)["status"], "v3_mejor")

    def test_ci_never_collapses(self):
        r = bt.spearman([(i, -i) for i in range(6)])
        self.assertGreater(r["ci90"][1] - r["ci90"][0], 0.01)

    def test_prediction_recorded_after_training_started_is_excluded(self):
        rows, sessions = self.build(3)
        d = sorted(rows)[0]
        rows[d]["recorded_at"] = d + "T15:00:00+01:00"
        for s_ in sessions.values():
            if s_["date"] == d:
                s_["start_local"] = d + "T10:00:00"
        ev = bt.evaluate(rows, {}, sessions, "2026-11-30", DEFAULTS, categorize)
        self.assertEqual(ev["training_days"], 2)

    def test_pending_decision_is_not_a_readiness_level(self):
        self.assertNotIn("unavailable", bt.ZONE_SCORE)


if __name__ == "__main__":
    unittest.main()
