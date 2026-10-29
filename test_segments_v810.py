"""V8.10: una actividad de Garmin partida en tramos (técnica sin RPE + WOD con RPE) con el mismo ID."""
import json
import unittest

from garmin_recovery import segments, training_blocks
from garmin_recovery.records import build_sessions

AID = "i999"
TECH = {"schema_version": 1, "type": "skill", "exercise": "handstand push-up", "rpe": None,
        "segment": {"start_s": 0, "end_s": 2420}, "notes": "Sin RPE: sesión no puntuada por decisión del atleta"}
WOD = {"schema_version": 1, "type": "metcon", "format": "21-15-9 For Time", "rpe": 5, "time_cap_minutes": 9,
       "finish_time_seconds": 234, "segment": {"start_s": 2420, "end_s": 2656},
       "prescribed_round": [{"name": "push press", "reps": 21, "load_kg": 50}, {"name": "butterfly pull-up", "reps": 18}],
       "performed": {"completed": True, "total_reps": 81}}
ROWS = [
    {"Fecha": "2026-10-29", "ID actividad": AID, "Actividad": "Técnica - handstand push-up déficit", "RPE": "",
     "Notas": "Sin RPE: sesión no puntuada por decisión del atleta.", "Detalle JSON": json.dumps(TECH)},
    {"Fecha": "2026-10-29", "ID actividad": AID, "Actividad": "WOD 21-15-9 - push press / butterfly pull-up", "RPE": "5",
     "Notas": "", "Detalle JSON": json.dumps(WOD)},
]


class Segments(unittest.TestCase):
    def test_scored_seconds_only_rated_segments(self):
        self.assertEqual(segments.scored_seconds_from_rows(ROWS, AID), 236)

    def test_no_segments_means_full_duration(self):
        self.assertIsNone(segments.scored_seconds([(5, {"type": "metcon"})]))

    def test_rated_block_without_segment_falls_back(self):
        self.assertIsNone(segments.scored_seconds([(5, {"type": "metcon"}), (None, TECH)]))

    def test_split_ids_only_when_all_rows_have_segment(self):
        self.assertEqual(segments.split_ids(ROWS), {AID})
        bad = [ROWS[0], dict(ROWS[1], **{"Detalle JSON": "{}"})]
        self.assertEqual(segments.split_ids(bad), set())

    def test_hr_in_segment(self):
        curve = {"points": [[t, 100 if t < 2420 else 170] for t in range(0, 3000, 10)]}
        self.assertEqual(segments.hr_in(curve, 2420, 2656), {"average": 170, "max": 170})


class Sessions(unittest.TestCase):
    def test_srpe_uses_wod_segment_and_label_joins_parts(self):
        inputs = {"activities": [{"id": AID, "start_date_local": "2026-10-29T09:00:00", "moving_time": 3300}],
                  "feedback": {"activities": {AID: {"rpe": 5, "activity": ROWS[1]["Actividad"]}}, "source_rows_AH": ROWS}}
        s = build_sessions(inputs)[0]
        self.assertEqual(s["rpe"], 5)
        self.assertEqual(s["srpe"], round(5 * 236 / 60, 1))
        self.assertEqual(s["duration_min"], 55.0)
        self.assertIn("Técnica", s["label"])
        self.assertIn("WOD", s["label"])


class Cards(unittest.TestCase):
    def test_metcon_card_uses_segment(self):
        act = {"activity_id": AID, "date": "2026-10-29", "recorded_minutes": 55, "heart_rate": {"average": 120, "max": 175}}
        curves = {AID: {"points": [[t, 150 + (t >= 2420) * 20] for t in range(0, 3000, 10)]}}
        m = training_blocks.metcon_card(act, {"activity": "WOD", "detail_json": WOD}, curves)
        self.assertEqual(m["minutes"], 3.9)
        self.assertTrue(m["segment"])
        self.assertEqual(m["hr"]["average"], 170)
        self.assertIn("Tramo 40:20–44:16 del reloj", m["timing"])
        self.assertIn("Oficial 3:54", m["timing"])

    def test_technique_part_listed_in_others(self):
        cf = {"activities": [{"activity_id": AID, "date": "2026-10-29", "rpe_used": 5, "recorded_minutes": 55,
                              "manual_blocks": [{"activity": ROWS[0]["Actividad"], "rpe": None, "detail_json": TECH},
                                                {"activity": ROWS[1]["Actividad"], "rpe": 5, "detail_json": WOD}]}]}
        tb = training_blocks.build(cf, {}, "2026-10-29")
        self.assertEqual(len(tb["metcons"]), 1)
        self.assertEqual([(o["kind"], o["rpe"], o["minutes"]) for o in tb["otros"]], [("skill", None, 40.3)])


if __name__ == "__main__":
    unittest.main()
