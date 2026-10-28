"""V8.7: sesiones enteras por tipo, complex de halterofilia, resultados de metcon y cifras únicas entre pantallas."""
import unittest
from datetime import datetime, timezone

from garmin_recovery import cycle_delivery, muscle_load, strength_patterns, training_blocks as tb
from garmin_recovery.crossfit import sets_volume
from garmin_recovery.session_kind import categorize


class SessionKind(unittest.TestCase):
    def test_wod_with_olympic_lifts_is_wod(self):
        self.assertEqual(categorize("WOD E3MO3M x8 - SkiErg/Assault Bike / DB hang clean + S2OH / box jump"), "WOD")
        self.assertEqual(categorize("WOD AMRAP 12 min - squat snatch / burpee over bar / toes to bar"), "WOD")
        self.assertEqual(categorize("EMOM 12 min - echo bike / squat clean"), "WOD")

    def test_warmup_and_technique_by_name(self):
        self.assertEqual(categorize("Calentamiento - WOD E3MO3M"), "Calentamiento")
        self.assertEqual(categorize("Técnica - toes to bar"), "Técnica")

    def test_weightlifting_session_whole(self):
        self.assertEqual(categorize("Halterofilia - complex squat clean + front squat + split jerk"), "Halterofilia")
        self.assertEqual(categorize("Fuerza - Squat snatch"), "Halterofilia")
        self.assertEqual(categorize("Fuerza - complex", exercises=["front squat", "squat clean"]), "Halterofilia")

    def test_strength_stays_strength(self):
        self.assertEqual(categorize("Fuerza - pecho: press banca, inclinados, aperturas, bíceps y abdominales"), "Fuerza")
        self.assertEqual(categorize("Fuerza - EMOM 8 min: DB split squat / ring row pies elevados"), "Fuerza")

    def test_without_sheet_label(self):
        self.assertEqual(categorize(None, "HIIT"), "Sin detalle")
        self.assertEqual(categorize(None, "Fuerza"), "Fuerza")


def _entry(aid, name, loads, title):
    sets = [{"reps": 1, "load": x, "count": 1} for x in loads]
    return {"date": "2026-10-28", "activity_id": aid, "activity": title, "exercise": name, "key": name, "unit": "kg_total_barra",
            "unit_label": "barra", "top_load": max(loads), "top_reps": 1, "volume": float(sum(loads)), "volume_complete": True,
            "work_sets": len(loads), "sets": sets, "rpe": 7.5}


TITLE = "Halterofilia - complex squat clean + front squat + split jerk / complex 2 squat clean + split jerk / complex squat clean + split jerk"


class WholeSessions(unittest.TestCase):
    def setUp(self):
        self.entries = {
            "a": _entry("i1", "squat clean", [60, 65, 68, 70], TITLE),
            "b": _entry("i1", "front squat", [60, 65, 68, 70], TITLE),
            "c": _entry("i1", "split jerk", [60, 65, 68, 70], TITLE),
            "d": _entry("i2", "press banca", [80, 90], "Fuerza - pecho"),
        }
        self.cx = {"i1": tb.complexes_of({"complexes": [
            {"name": "Complex squat clean + front squat + split jerk (4 x 1)", "sets": 4, "interval_seconds": 60,
             "reps": {"squat clean": 1, "front squat": 1, "split jerk": 1}, "loads_kg": [60, 65, 68, 70]}]})}

    def test_front_squat_of_a_complex_is_not_split_off(self):
        hl = tb.lift_sessions(self.entries, {}, True, complexes=self.cx)
        fz = tb.lift_sessions(self.entries, {}, False, complexes=self.cx)
        self.assertEqual([s["activity_id"] for s in hl], ["i1"])
        self.assertEqual(sorted(e["name"] for e in hl[0]["exercises"]), ["front squat", "split jerk", "squat clean"])
        self.assertEqual([s["activity_id"] for s in fz], ["i2"])

    def test_complexes_and_totals(self):
        s = tb.lift_sessions(self.entries, {}, True, complexes=self.cx)[0]
        c = s["complexes"][0]
        self.assertEqual((c["scheme"], c["interval"], c["top"], c["sets"]), ("1+1+1", "cada 1'", 70, 4))
        self.assertEqual(s["total_reps"], 12)
        self.assertEqual(s["bar_volume"], 789)

    def test_weekly_volume_follows_the_session(self):
        hv = tb.weekly_volume(self.entries, True, "2026-10-28")
        fv = tb.weekly_volume(self.entries, False, "2026-10-28")
        self.assertEqual(hv[-1]["volume"], 789)
        self.assertEqual(fv[-1]["volume"], 170)

    def test_card_shows_complexes(self):
        from garmin_recovery.dashboard import _lifts_html
        html = _lifts_html(tb.lift_sessions(self.entries, {}, True, complexes=self.cx), "Sesiones de halterofilia", "")
        self.assertIn("lf-cx", html)
        self.assertIn("60 · 65 · 68 · 70 kg", html)
        self.assertIn("Por movimiento (3)", html)
        self.assertIn("4 series de complex", html)

    def test_interval_text(self):
        self.assertEqual(tb._interval(90), "cada 1'30\"")
        self.assertEqual(tb._interval(150), "cada 2'30\"")


class Metcons(unittest.TestCase):
    def _card(self, detail):
        return tb.metcon_card({"date": "2026-10-28", "activity_id": "i9"}, {"activity": "WOD", "detail_json": detail})

    def test_rounds_format_is_a_result(self):
        m = self._card({"type": "metcon", "format": "E3MO3M", "performed": {"rounds": 8, "all_rounds_completed": True,
                        "totals": {"calories": 120, "db_hang_clean_s2oh_reps": 160, "box_jump_reps": 120}}})
        self.assertEqual(m["result"], "8 de 8 rondas completas · 280 reps en total")  # V8.9: suma de reps
        self.assertEqual(m["totals"], ["120 cal", "160 DB hang clean S2OH", "120 box jump"])

    def test_reps_summed_from_detail_totals(self):  # V8.9: parejas con totales fuera de «performed»
        m = self._card({"type": "metcon", "format": "3 RFT", "rounds_completed": 3,
                        "totals": {"calories_shared_by_pair": 120, "burpee_synchronized_reps": 60, "dumbbell_snatch_synchronized_reps": 60}})
        self.assertEqual(m["result"], "3 rondas · 120 reps en total")

    def test_amrap_with_distance_and_reps(self):
        m = self._card({"type": "metcon", "format": "AMRAP", "performed": {"rounds_complete": 6, "extra_distance_m": 200, "extra_reps": 10,
                        "totals": {"run_m": 1400, "wall_ball_reps": 82, "pull_up_reps": 54}}})
        self.assertTrue(m["result"].startswith("6 rondas + 200 m + 10 reps"))
        self.assertEqual(m["totals"][0], "1.400 m de carrera")


class Clip(unittest.TestCase):
    def test_cuts_on_a_word_with_ellipsis(self):
        out = tb.clip(TITLE, 60)
        self.assertTrue(out.endswith("…"))
        self.assertLessEqual(len(out), 60)
        self.assertFalse(out[:-1].endswith(" "))
        self.assertEqual(tb.clip("corto", 60), "corto")


class WebStage(unittest.TestCase):
    AFTER = datetime(2026, 10, 28, 11, 42, tzinfo=timezone.utc)

    def test_superseded_cancel_is_not_a_failure(self):
        runs = [{"id": 1, "created_at": "2026-10-28T11:42:50Z", "status": "completed", "conclusion": "cancelled"},
                {"id": 2, "created_at": "2026-10-28T11:43:25Z", "status": "completed", "conclusion": "success"}]
        run = cycle_delivery.find_pages_run(runs, self.AFTER)
        self.assertEqual(run["id"], 2)
        st = cycle_delivery.web_stage(run)
        self.assertEqual(st["state"], "ok")
        self.assertIn("no es un fallo", st["note"])

    def test_waits_for_the_newer_deploy(self):
        runs = [{"id": 1, "created_at": "2026-10-28T11:42:50Z", "status": "completed", "conclusion": "cancelled"},
                {"id": 2, "created_at": "2026-10-28T11:43:25Z", "status": "in_progress", "conclusion": None}]
        self.assertEqual(cycle_delivery.web_stage(cycle_delivery.find_pages_run(runs, self.AFTER))["state"], "pending")

    def test_lone_cancel_still_fails(self):
        runs = [{"id": 1, "created_at": "2026-10-28T11:42:50Z", "status": "completed", "conclusion": "cancelled"}]
        self.assertEqual(cycle_delivery.web_stage(cycle_delivery.find_pages_run(runs, self.AFTER))["state"], "failed")


class ReportWording(unittest.TestCase):
    def test_confirmed_month_day_is_free(self):
        from garmin_recovery.fullreport import _shift_es
        cal = {"days": {"2026-10-29": "TN"}, "confirmed_months": ["2026-10"]}
        self.assertEqual(_shift_es("2026-10-28", cal), "libre")
        self.assertEqual(_shift_es("2026-10-29", cal), "TN (15–08)")
        self.assertEqual(_shift_es("2026-10-30", cal), "libre tras la noche")
        self.assertEqual(_shift_es("2026-12-02", cal), "sin turno registrado")

    def test_week_plan_table_in_spanish(self):
        from garmin_recovery import week_plan
        md = week_plan.to_markdown([{"date": "2026-10-28", "dow": "mié", "shift": "free", "kind": "light", "why": "x"},
                                    {"date": "2026-10-30", "dow": "vie", "shift": "post-TN", "kind": "rest", "why": "y"}])
        self.assertIn("| libre |", md)
        self.assertIn("| tras TN |", md)
        self.assertNotIn("free", md)

    def test_hrv_rule_uses_the_score_average(self):
        from garmin_recovery.improvement import _hrv
        comp = {"n_rolling": 7, "rolling_ms": 49.4, "baseline_ms": 57.0, "normal_low_ms": 52.9, "normal_high_ms": 61.4}
        f = _hrv([], "2026-10-28", comp)
        self.assertIn("49,4 ms", f["observed"])
        self.assertIn("-13 %", f["observed"])
        self.assertEqual(f["severity"], 3)


class StrengthFigures(unittest.TestCase):
    def test_empty_bar_left_out_like_the_app(self):
        detail = {"exercises": [{"name": "press banca", "load_unit": "kg_total_barra",
                                 "sets": [{"reps": 30, "load_kg": 20, "bar_empty": True}, {"reps": 6, "load_kg": 90}]}]}
        self.assertEqual(sets_volume(detail)[0], 540.0)

    def test_patterns(self):
        self.assertEqual(muscle_load.classify("ring row feet elevated"), "horizontal_pull")
        self.assertEqual(muscle_load.classify("chin up lastrado"), "vertical_pull")
        self.assertEqual(muscle_load.classify("isometric pull up"), "vertical_pull")
        self.assertEqual(muscle_load.classify("curl de bíceps en máquina unilateral"), "biceps_isolation")
        self.assertEqual(muscle_load.classify("curl femoral tumbado"), "knee_flexion")
        self.assertEqual(muscle_load.classify("aperturas en banco inclinado con mancuernas"), "chest_isolation")
        self.assertEqual(muscle_load.classify("squat clean"), "olympic_lift")
        self.assertEqual(muscle_load.classify("front squat"), "squat")
        self.assertEqual(muscle_load.classify("split jerk"), "olympic_lift")

    def test_declared_bodyweight_sets_count(self):
        rows = [{"date": "2026-10-26", "activity_id": "i1", "exercise": "sit-ups", "equipment": "bodyweight",
                 "movement_pattern": "core", "known_sets": 0, "total_sets": 4}]
        res = strength_patterns.compute(rows, "2026-10-28")
        self.assertEqual(res["7d"]["core"]["sets"], 4)
        self.assertIn("| Otros |", strength_patterns.to_markdown({"7d": {"other": res["7d"]["core"]}, "28d": {}}))


class LastSessionChip(unittest.TestCase):
    def test_uses_the_sheet_type(self):
        from garmin_recovery.glance import compose
        chips = compose({"date": "2026-10-28", "sessions_28d": [
            {"date": "2026-10-28", "start_local": "2026-10-28T10:21:50", "name": "HIIT", "rpe": 7.5, "duration_min": 55.9,
             "label": TITLE}]})
        self.assertTrue(chips[0]["value"].startswith("Halterofilia · RPE 7,5"))


if __name__ == "__main__":
    unittest.main()
