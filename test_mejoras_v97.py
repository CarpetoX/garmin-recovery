"""V9.7: adherencia a la decisión, fases de sueño dudosas, molestias por zona, olímpicos y falsa alarma del respaldo."""
import unittest
from datetime import datetime, timezone

from garmin_recovery import athlete_progress as ap
from garmin_recovery import backtest as bt
from garmin_recovery import discomfort as dc
from garmin_recovery import monitor as mon
from garmin_recovery import sleep_stages as ss


class SleepStagesTests(unittest.TestCase):
    def test_flags(self):
        self.assertEqual(ss.check(5.2, 103, 0)["code"], "rem_zero")
        self.assertIn("5,2 h", ss.check(5.2, 103, 0)["text"])
        self.assertEqual(ss.check(4.2, 0, 0)["code"], "no_stages")
        self.assertEqual(ss.check(4.0, 150, 20)["code"], "deep_excess")

    def test_plausible_or_missing(self):
        self.assertIsNone(ss.check(7.5, 71, 99))
        self.assertIsNone(ss.check(2.0, 40, 0))  # episodio corto: puede no haber REM
        self.assertIsNone(ss.check(6.0, None, None))
        self.assertIsNone(ss.check(None, 50, 0))


def survey(day, lvl, zones):
    labels = ["Ninguna", "Leves", "Moderadas", "Fuertes"]
    e = {"date": day, "molestias": {"level": lvl, "label": labels[lvl]}}
    if zones:
        e["zonas"] = zones
    return e


class DiscomfortTests(unittest.TestCase):
    def setUp(self):
        self.entries = [survey("2026-11-10", 1, ["Rodilla derecha"]), survey("2026-11-12", 1, ["Rodilla derecha"]),
                        survey("2026-11-13", 2, ["Rodilla derecha", "Hombro"]), survey("2026-11-15", 0, None),
                        survey("2026-11-18", 1, ["Rodilla"])]

    def test_history_groups_by_joint(self):
        h = dc.zone_history(self.entries, "2026-11-18")
        knee = h[0]
        self.assertEqual((knee["joint"], knee["label"], knee["days_7"], knee["days_28"]), ("rodilla", "Rodilla derecha", 3, 4))
        self.assertEqual((knee["max_level"], knee["max_label"], knee["last"]), (2, "Moderadas", "2026-11-18"))
        self.assertEqual(h[1]["joint"], "hombro")
        self.assertEqual(len(dc.observation(h)), 1)  # solo la rodilla se repite (3 de 7)

    def test_loading_sessions(self):
        sessions = [
            {"id": "a", "date": "2026-11-17", "label": "WOD - wall ball / thruster", "rpe": 9},
            {"id": "b", "date": "2026-11-17", "label": "Técnica - butterfly pull-up", "rpe": None},
            {"id": "c", "date": "2026-11-14", "label": "WOD - box jump", "rpe": 8},
            {"id": "d", "date": "2026-11-18", "label": "HIIT", "blocks": [{"activity": "Halterofilia",
                                                                          "detail_json": {"exercises": [{"name": "squat snatch"}]}}]},
        ]
        out = dc.loading_sessions("rodilla", ["2026-11-18"], sessions)
        self.assertEqual([x["id"] for x in out], ["d", "a"])
        self.assertIn("thruster", out[1]["moves"])


class OlympicTests(unittest.TestCase):
    ENTRIES = [
        {"date": "2026-10-26", "exercise": "squat snatch", "unit": "kg_total_barra", "sets": [{"load": 70, "reps": 2}, {"load": 75, "reps": 1}]},
        {"date": "2026-11-18", "exercise": "squat snatch", "unit": "kg_total_barra", "sets": [{"load": 60, "reps": 3}, {"load": 63, "reps": 3}]},
        {"date": "2026-11-18", "exercise": "3-position squat snatch", "unit": "kg_total_barra", "sets": [{"load": 48, "reps": 3}]},
        {"date": "2026-11-10", "exercise": "sentadilla trasera", "unit": "kg_total_barra", "sets": [{"load": 140, "reps": 6}]},
    ]

    def test_olympic_real_loads(self):
        ol = ap.olympic_lifts(self.ENTRIES)
        sn = next(o for o in ol if o["name"] == "squat snatch")
        self.assertEqual(sn["kind"], "lift")
        self.assertEqual(sn["best"], {"load": 75, "reps": 1, "date": "2026-10-26"})
        self.assertEqual([(r["reps"], r["load"]) for r in sn["by_reps"]], [(1, 75), (2, 70), (3, 63)])
        self.assertEqual(sn["last"], {"date": "2026-11-18", "load": 63, "reps": 3})
        self.assertFalse(sn["last_is_best"])
        cx = next(o for o in ol if o["name"] == "3-position squat snatch")
        self.assertEqual(cx["kind"], "complex")
        self.assertNotIn("sentadilla trasera", [o["name"] for o in ol])

    def test_epley_excludes_olympic(self):
        self.assertEqual([m["name"] for m in ap.estimated_max(self.ENTRIES)], ["sentadilla trasera"])


class AdherenceTests(unittest.TestCase):
    def test_summary(self):
        preds = {f"2026-11-{d:02d}": {"rpe_cap": cap, "decision_zone": z, "v2_score": v2}
                 for d, cap, z, v2 in [(1, 4, "red", 50), (2, 9, "green", 60), (3, 4, "red", 40), (4, 9, "green", 70),
                                       (5, 7, "yellow", 55), (6, 9, "green", 65), (7, 4, "red", 45), (8, 9, "green", 80)]}
        rpe = {"2026-11-01": 8, "2026-11-02": 7, "2026-11-03": 9, "2026-11-04": 8, "2026-11-05": 6, "2026-11-06": 9, "2026-11-07": 8}
        daily = {d: {"hrv_ms": 50} for d in preds}
        a = bt.adherence(preds, preds, daily, rpe, "2026-11-08")
        self.assertEqual((a["trained_days"], a["over"], a["within"], a["over_red"]), (7, 3, 4, 3))
        self.assertEqual(a["next_v2_after_over"], round((60 + 70 + 80) / 3, 1))
        self.assertEqual(a["next_v2_after_within"], round((40 + 55 + 65 + 45) / 4, 1))
        self.assertEqual(a["days"][0]["excess"], 4.0)

    def test_small_groups_have_no_mean(self):
        preds = {"2026-11-01": {"rpe_cap": 4, "decision_zone": "red"}, "2026-11-02": {"rpe_cap": 9, "v2_score": 60}}
        a = bt.adherence(preds, preds, {}, {"2026-11-01": 8}, "2026-11-02")
        self.assertIsNone(a["next_v2_after_over"])


def run(event, conclusion, created):
    return {"event": event, "conclusion": conclusion, "status": "completed", "created_at": created, "updated_at": created}


class BackupMonitorTests(unittest.TestCase):
    def test_backup_not_needed(self):
        apps = run("workflow_dispatch", "success", "2026-11-18T07:33:00Z")
        cron = run("schedule", "cancelled", "2026-11-18T16:37:00Z")
        self.assertTrue(mon.backup_not_needed(cron, [cron, apps]))
        self.assertFalse(mon.backup_not_needed(run("schedule", "cancelled", "2026-11-19T16:37:00Z"), [apps]))  # > 14 h
        self.assertFalse(mon.backup_not_needed(run("workflow_dispatch", "cancelled", "2026-11-18T09:00:00Z"), [apps]))
        self.assertFalse(mon.backup_not_needed(run("schedule", "failure", "2026-11-18T09:00:00Z"), [apps]))

    def test_monitor_alert_is_info(self):
        now = datetime(2026, 11, 18, 18, 0, tzinfo=timezone.utc)
        runs = [run("schedule", "cancelled", "2026-11-18T16:37:00Z"), run("workflow_dispatch", "success", "2026-11-18T15:48:00Z")]
        fn = vars(mon)["__monitor_before_v231"]  # comprobación base, sin la auditoría de franjas (necesita red)
        res = fn(now, "o/r", "t", fetcher=lambda repo, token, wf: runs if wf == "sync.yml" else [run("push", "success", "2026-11-18T15:50:00Z")])
        codes = {(a["code"], a["severity"]) for a in res["alerts"] if a.get("workflow") == "sync.yml"}
        self.assertIn(("backup_sync_not_needed", "info"), codes)
        self.assertNotIn("latest_run_failed", {c for c, _ in codes})


if __name__ == "__main__":
    unittest.main()
