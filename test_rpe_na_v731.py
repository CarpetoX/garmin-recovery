"""V7.31: técnica, calentamientos y sesiones «sin RPE» no cuentan como RPE pendiente en ningún contador."""
import unittest
from datetime import datetime

from garmin_recovery import glance
from garmin_recovery.notify import TZ, rpe_pending_tip
from garmin_recovery.records import build_sessions, rpe_pending

ROW_SKILL = {"ID actividad": "i2", "RPE": "", "Notas": "Técnica de HSPU.", "Detalle JSON": '{"type": "skill"}'}
ACTS = [{"id": "i1", "start_date_local": "2026-10-26T09:25:52", "moving_time": 1476, "icu_training_load": 10},
        {"id": "i2", "start_date_local": "2026-10-26T10:26:00", "moving_time": 2826, "icu_training_load": 12},
        {"id": "i3", "start_date_local": "2026-10-26T11:30:00", "moving_time": 900, "icu_training_load": 8}]


def sessions():
    fb = {"activities": {"i1": {"rpe": 7, "activity": "Fuerza"}}, "source_rows_AH": [ROW_SKILL]}
    return build_sessions({"activities": ACTS, "feedback": fb})


class RpeNotApplicable(unittest.TestCase):
    def test_flag_only_on_declared_sessions(self):
        by = {s["id"]: s for s in sessions()}
        self.assertTrue(by["i2"].get("rpe_na"))
        self.assertNotIn("rpe_na", by["i1"])
        self.assertNotIn("rpe_na", by["i3"])          # sin fila en la hoja: sigue pendiente
        self.assertEqual([s["id"] for s in by.values() if rpe_pending(s)], ["i3"])

    def test_glance_and_notify_ignore_technique(self):
        ss = sessions()
        result = {"date": "2026-10-26", "sessions_28d": ss}
        reg = next(c for c in glance.compose(result) if c["id"] == "registros")
        self.assertEqual(reg["value"], "1 de 2 con RPE")
        self.assertIn("1 sin RPE a propósito", reg["sub"])
        tip = rpe_pending_tip(result, datetime(2026, 10, 26, 15, 0, tzinfo=TZ))
        self.assertTrue(tip.startswith("1 sesión de hoy sin RPE"))
        only_skill = {"date": "2026-10-26", "sessions_28d": [s for s in ss if s["id"] != "i3"]}
        self.assertIsNone(rpe_pending_tip(only_skill, datetime(2026, 10, 26, 15, 0, tzinfo=TZ)))
        last = next(c for c in glance.compose({"date": "2026-10-26", "sessions_28d": [s for s in ss if s["id"] == "i2"]})
                    if c["id"] == "ultimo")
        self.assertIn("no lleva RPE", last["value"])
        self.assertEqual(last["tone"], "neutral")


if __name__ == "__main__":
    unittest.main()
