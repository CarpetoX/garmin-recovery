"""V8.8: carreras con todos los datos de Garmin e Intervals, tipo «Carrera» y comparación entre carreras parecidas."""
import unittest
from datetime import datetime, timezone

from garmin_recovery import garmin_runs, running, training_blocks as tb
from garmin_recovery.session_kind import categorize

GARMIN_RAW = {
    "activityId": 24605352759, "activityName": "Orense Carrera", "startTimeLocal": "2026-10-04 17:20:35",
    "activityType": {"typeKey": "running"}, "distance": 8300.0, "duration": 2580.0, "movingDuration": 2570.0,
    "averageSpeed": 3.23, "maxSpeed": 3.9, "averageHR": 154.0, "maxHR": 173.0,
    "averageRunningCadenceInStepsPerMinute": 160.0, "avgStrideLength": 121.0, "avgVerticalOscillation": 9.8,
    "avgGroundContactTime": 275.0, "avgVerticalRatio": 8.2, "elevationGain": 40.0, "elevationLoss": 41.0,
    "aerobicTrainingEffect": 3.8, "anaerobicTrainingEffect": 0.0, "trainingEffectLabel": "LACTATE_THRESHOLD",
    "activityTrainingLoad": 163.0, "calories": 714.0, "vO2MaxValue": 46.0, "fastestSplit_1000": 290.0,
    "hrTimeInZone_1": 60, "hrTimeInZone_2": 300, "hrTimeInZone_3": 1200, "hrTimeInZone_4": 900, "hrTimeInZone_5": 120,
}
FRAGMENT = dict(GARMIN_RAW, activityId=24605350942, startTimeLocal="2026-10-04 17:18:07", distance=300.0, duration=108.0,
                movingDuration=90.0)
INTERVALS_TODAY = {
    "id": "i202804127", "external_id": "24882628767", "type": "Run", "name": "Orense Carrera",
    "start_date_local": "2026-10-28T15:38:52", "distance": 8015.01, "moving_time": 2475, "elapsed_time": 2479,
    "average_speed": 3.233, "max_speed": 3.798, "gap": 3.233119, "average_heartrate": 157, "max_heartrate": 177,
    "average_cadence": 81.12171, "average_stride": 1.1976033, "average_vertical_oscillation": 95.828224,
    "average_stance_time": 268.66357, "average_vertical_ratio": 8.061937, "total_elevation_gain": 33.575874,
    "total_elevation_loss": 33.36956, "calories": 655, "icu_training_load": 45, "trimp": 76.714134,
}


def _splits(paces_hr):
    return [{"lap": i + 1, "distance_m": 1000.0, "moving_s": p, "avg_hr": h} for i, (p, h) in enumerate(paces_hr)]


class GarminCollector(unittest.TestCase):
    def test_summary_keeps_every_running_field(self):
        r = garmin_runs.summarize_run(GARMIN_RAW)
        self.assertEqual(r["garmin_id"], "24605352759")
        self.assertEqual(r["date"], "2026-10-04")
        for k in ("distance_m", "cadence_spm", "stride_cm", "vertical_oscillation_cm", "ground_contact_ms", "vertical_ratio_pct",
                  "elev_gain_m", "aerobic_te", "garmin_load", "vo2max", "fastest_1k_s"):
            self.assertIn(k, r)
        self.assertEqual(r["hr_zone_s"], [60, 300, 1200, 900, 120])

    def test_non_runs_are_ignored(self):
        self.assertIsNone(garmin_runs.summarize_run(dict(GARMIN_RAW, activityType={"typeKey": "hiit"})))

    def test_splits_and_merge_keep_downloaded_laps(self):
        laps = garmin_runs.summarize_splits({"lapDTOs": [{"distance": 1000, "movingDuration": 310, "averageHR": 150},
                                                        {"distance": 0}]})
        self.assertEqual(len(laps), 1)
        now = datetime(2026, 10, 28, tzinfo=timezone.utc)
        first = garmin_runs.merge({}, [dict(garmin_runs.summarize_run(GARMIN_RAW), splits=laps)], now)
        again = garmin_runs.merge(first, [garmin_runs.summarize_run(GARMIN_RAW)], now)
        self.assertEqual(again["runs"]["24605352759"]["splits"], laps)


class Runs(unittest.TestCase):
    def setUp(self):
        hist = {"runs": {"24605352759": garmin_runs.summarize_run(GARMIN_RAW),
                         "24605350942": garmin_runs.summarize_run(FRAGMENT)}}
        self.res = running.build(hist, [INTERVALS_TODAY], "2026-10-28", {"i202804127": 7}, {"i202804127": "Carrera - 8 km"})

    def test_both_runs_fragment_dropped(self):
        self.assertEqual([r["date"] for r in self.res["runs"]], ["2026-10-28", "2026-10-04"])
        self.assertEqual(self.res["summary"]["count"], 2)

    def test_units_and_derived(self):
        today, old = self.res["runs"]
        self.assertAlmostEqual(today["cadence_spm"], 162.2, places=1)  # Intervals da la cadencia por pierna
        self.assertAlmostEqual(today["vertical_oscillation_cm"], 9.6, places=1)  # mm → cm
        self.assertEqual(round(old["stride_m"], 2), 1.21)  # cm → m
        self.assertEqual(running.pace_text(today["pace_s_km"]), "5:09")
        self.assertAlmostEqual(today["m_per_beat"], 1.236, places=2)
        self.assertEqual((today["rpe"], today["title"]), (7, "Carrera - 8 km"))
        self.assertEqual(old["te_label"], "umbral")

    def test_comparison_with_similar_run(self):
        c = self.res["runs"][0]["comparison"]
        self.assertEqual(c["vs_date"], "2026-10-04")
        self.assertIn("Frente a la del 04/10", c["text"])
        self.assertIn("FC media +3 lpm", c["text"])
        self.assertIsNone(self.res["runs"][1]["comparison"])

    def test_garmin_and_intervals_merge_by_garmin_id(self):
        raw = dict(GARMIN_RAW, activityId=24882628767, startTimeLocal="2026-10-28 15:38:52", averageHR=158.0)
        res = running.build({"runs": {"24882628767": garmin_runs.summarize_run(raw)}}, [INTERVALS_TODAY], "2026-10-28")
        r = res["runs"][0]
        self.assertEqual(len(res["runs"]), 1)
        self.assertEqual(r["sources"], ["Garmin", "Intervals"])
        self.assertEqual(r["avg_hr"], 158.0)  # Garmin manda
        self.assertEqual(r["intervals_id"], "i202804127")
        self.assertEqual(r["trimp"], 76.714134)  # Intervals añade lo suyo

    def test_decoupling_from_splits(self):
        self.assertEqual(running.decoupling_from_splits(running._splits(_splits([(300, 150)] * 4))), 0.0)
        self.assertGreater(running.decoupling_from_splits(running._splits(_splits([(300, 150), (300, 150), (300, 160), (300, 162)]))), 5)
        self.assertIsNone(running.decoupling_from_splits(running._splits(_splits([(300, 150)] * 3))))
        tail = running._splits([{"distance_m": 1000, "moving_s": 300, "avg_hr": 150}, {"distance_m": 15, "moving_s": 7, "avg_hr": 177}])
        self.assertEqual(len(tail), 1)  # el resto de 15 m al parar el reloj no es un parcial

    def test_card_and_report(self):
        from garmin_recovery.dashboard import _runs_html
        html = _runs_html(self.res)
        for txt in ("Carrera", "5:09", "Metros por latido", "Frente a la del 04/10", "Oscilación vertical", "Contacto con el suelo"):
            self.assertIn(txt, html)
        self.assertIn("Aún no hay carreras", _runs_html({"runs": []}))
        md = running.to_markdown(self.res)
        self.assertIn("| 28/10 | 8,02 |", md)
        self.assertIn("Frente a la del 04/10", md)


class RunKind(unittest.TestCase):
    def test_run_is_its_own_type(self):
        self.assertEqual(categorize("Carrera - 8 km"), "Carrera")
        self.assertEqual(categorize(None, "Orense Carrera"), "Carrera")
        self.assertEqual(categorize(None, "Lunch", sport="Run"), "Carrera")
        self.assertEqual(categorize("WOD AMRAP 15 min - carrera / wall ball / pull-ups"), "WOD")
        self.assertEqual(categorize("WOD 5 Rounds For Time - wall ball / double unders"), "WOD")

    def test_run_leaves_the_technique_tab(self):
        cf = {"activities": [{"activity_id": "i202804127", "date": "2026-10-28", "name": "Orense Carrera",
                              "manual_blocks": [{"activity": "Carrera - 8 km", "detail_json": {"type": "aerobic"}}]}]}
        b = tb.build(cf, {}, "2026-10-28")
        self.assertEqual(b["otros"], [])
        self.assertEqual(b["summary7"]["carrera"], 1)


if __name__ == "__main__":
    unittest.main()
