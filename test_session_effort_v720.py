"""V7.20: FC en cada sesión de Entrenos y RPE frente a FC."""
import json
import math
import unittest
from pathlib import Path

from garmin_recovery import backtest, session_effort
from garmin_recovery.dashboard import _hr_slot, _lifts_html, _metcons_html
from garmin_recovery.report import categorize, sessions_table

ROOT = Path(__file__).resolve().parent


def _wod(i, rpe, load=15, minutes=12.0, day=None):
    return {"id": f"i{i}", "date": day or f"2026-10-{i:02d}", "label": "WOD AMRAP", "name": "HIIT",
            "duration_min": minutes, "load": load, "rpe": rpe, "srpe": None if rpe is None else rpe * minutes,
            "avg_hr": 150, "max_hr": 175, "removed": 0}


def _sessions():
    rows = [_wod(i, 8, load=load) for i, load in enumerate((14, 15, 16, 15, 14, 16, 15), start=1)]
    rows += [_wod(8, 3), _wod(9, None)]  # una sesión con RPE muy bajo para su carga y otra sin RPE
    return {s["id"]: s for s in rows}


class EffortBySession(unittest.TestCase):
    def test_flags_outlier_and_skips_missing_rpe(self):
        eff = session_effort.compute(_sessions())
        self.assertNotIn("i9", eff)  # sin RPE no se rellena
        self.assertEqual(eff["i8"]["flag"], "bajo")
        self.assertTrue(all(eff[f"i{i}"]["flag"] is None for i in range(1, 8)))
        self.assertEqual(eff["i8"]["category"], "WOD")

    def test_day_mean_matches_previous_definition(self):
        sess = _sessions()
        per = backtest.effort_by_session(sess, categorize)
        days = backtest.effort_by_day(sess, categorize)
        for e in per.values():
            same_day = [x["z"] for x in per.values() if x["date"] == e["date"]]
            self.assertTrue(math.isclose(days[e["date"]], sum(same_day) / len(same_day)))

    def test_needs_reference(self):
        few = {k: v for k, v in list(_sessions().items())[:3]}
        self.assertEqual(session_effort.compute(few), {})

    def test_classify(self):
        self.assertEqual(session_effort.classify(1.5), "alto")
        self.assertEqual(session_effort.classify(-1.5), "bajo")
        self.assertIsNone(session_effort.classify(1.49))
        self.assertIsNone(session_effort.classify(None))


class CycleReport(unittest.TestCase):
    def test_table_has_max_hr_and_flag(self):
        sess = list(_sessions().values())
        md = sessions_table(sess, day="2026-10-08", effort={"i8": {"flag": "bajo", "z": -3}})
        self.assertIn("FC media / máx.", md)
        self.assertIn("150 / 175", md)
        self.assertIn(session_effort.TEXT["bajo"], md)
        self.assertNotIn("⚠️", sessions_table(sess, day="2026-10-01", effort={"i8": {"flag": "bajo"}}))


class EntrenosCards(unittest.TestCase):
    def test_cards_carry_activity_slot(self):
        lift = [{"date": "2026-10-20", "activity_id": "i123", "title": "Fuerza", "rpe": 7, "exercises": []}]
        self.assertIn('class="hrmini" data-id="i123"', _lifts_html(lift, "Fuerza", ""))
        metcon = [{"date": "2026-10-20", "activity_id": "i456", "format": "AMRAP", "partner": False, "rpe": 9,
                   "prescription": [], "timing": [], "minutes": 12, "hr": {"average": 150, "max": 175},
                   "rounds": None, "result": "", "note": ""}]
        out = _metcons_html(metcon)
        self.assertIn('data-id="i456"', out)
        self.assertIn('class="rx-chip hrchip"', out)  # la web la quita cuando hay curva
        self.assertEqual(_hr_slot(""), "")

    def test_site_exposes_effort_and_curves(self):
        from garmin_recovery.dashboard import render
        result = json.loads((ROOT / "app" / "readiness_v3.json").read_text(encoding="utf-8"))
        page = render(result, {"session_effort": {"i1": {"z": 2.0, "flag": "alto"}},
                               "hr_curves": {"step_s": 10, "activities": {}}})
        self.assertIn('"session_effort"', page)
        self.assertIn("function miniHr", page)
        # las constantes de esfuerzo se declaran antes de pintar la tabla de sesiones
        self.assertLess(page.index("const EFF ="), page.index("$('sessions').innerHTML"))



class UnscoredSessions(unittest.TestCase):
    """Una sesión que la hoja declara sin RPE deja de llevar el RPE antiguo en el historial."""

    ACT = {"id": "i1", "start_date_local": "2026-10-20T11:36:05", "moving_time": 964, "icu_training_load": 7,
           "average_heartrate": 120, "max_heartrate": 151}

    def _hist(self, snapshot):
        from garmin_recovery.history import merge
        from garmin_recovery.records import build_sessions
        old = {"i1": {"id": "i1", "date": "2026-10-20", "rpe": 1.0, "srpe": 16.1, "avg_hr": 120}}
        fresh = build_sessions({"activities": [self.ACT], "feedback": snapshot})
        return merge(old, {s["id"]: s for s in fresh})["i1"]

    def test_declared_without_rpe_clears_old_value(self):
        row = {"ID actividad": "i1", "RPE": "", "Notas": "Sin RPE: sesión no puntuada por decisión del atleta.",
               "Detalle JSON": '{"type": "strength", "rpe": null}'}
        h = self._hist({"activities": {}, "source_rows_AH": [row]})
        self.assertIsNone(h["rpe"])
        self.assertIsNone(h["srpe"])
        self.assertNotIn("_clear", h)
        self.assertEqual(h["avg_hr"], 120)

    def test_missing_snapshot_keeps_history(self):
        self.assertEqual(self._hist({"activities": {}})["rpe"], 1.0)
        self.assertEqual(self._hist(None)["rpe"], 1.0)

    def test_pending_rpe_is_not_cleared(self):
        row = {"ID actividad": "i1", "RPE": "", "Notas": "RPE pendiente.", "Detalle JSON": '{"type": "strength"}'}
        self.assertEqual(self._hist({"activities": {}, "source_rows_AH": [row]})["rpe"], 1.0)


class EnrichmentDropsStaleRpe(unittest.TestCase):
    """V7.22: la copia de la hoja no arrastra el RPE de una fila que ahora dice «sin RPE»."""

    def _run(self, remote_rows, fail=False):
        import os
        import tempfile
        from unittest import mock

        from garmin_recovery import rpe_enrichment as rp
        old = {"activities": {"i1": {"rpe": 1.0, "date": "2026-10-20"}, "i2": {"rpe": 8.0, "date": "2026-10-20"}}}
        with tempfile.TemporaryDirectory() as d:
            cwd = os.getcwd()
            os.chdir(d)
            try:
                Path("training_feedback.json").write_text(json.dumps(old), encoding="utf-8")
                Path("activities.json").write_text("[]", encoding="utf-8")

                def fetch(url):
                    if fail:
                        raise OSError("sin red")
                    return {"i2": {"rpe": 8.0, "date": "2026-10-20"}}, remote_rows
                with mock.patch.dict(os.environ, {"RPE_CSV_URL": "https://x"}), \
                        mock.patch.object(rp, "feedback_from_csv", fetch), \
                        mock.patch("garmin_recovery.advanced.main", lambda: None):
                    rp.main()
                return json.loads(Path("training_feedback.json").read_text(encoding="utf-8"))["activities"]
            finally:
                os.chdir(cwd)

    ROWS = [{"ID actividad": "i1", "RPE": "", "Notas": "Sin RPE: sesión no puntuada por decisión del atleta.",
             "Detalle JSON": '{"type": "strength", "rpe": null}'},
            {"ID actividad": "i2", "RPE": "8", "Notas": "", "Detalle JSON": ""}]

    def test_unscored_row_drops_old_value(self):
        acts = self._run(self.ROWS)
        self.assertNotIn("i1", acts)
        self.assertEqual(acts["i2"]["rpe"], 8.0)

    def test_failed_download_keeps_everything(self):
        self.assertEqual(self._run(self.ROWS, fail=True)["i1"]["rpe"], 1.0)


if __name__ == "__main__":
    unittest.main()
