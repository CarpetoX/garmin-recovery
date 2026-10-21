"""Tests del motor de informes V5.3 (datos ausentes, gráficas vacías, fechas y contradicciones)."""
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from garmin_recovery import report as rp

TZ = ZoneInfo("Europe/Madrid")
ROOT = Path(__file__).resolve().parent


def minimal_result(**over):
    base = {"date": "2026-10-17", "generated_at": "2026-10-17T08:45:00+02:00", "app_version": "x", "model_version": "y",
            "trend_28d": [], "recent_sessions": [], "load": {}, "readiness": {"components": {}},
            "decision": {}, "certificate": {}, "training_integrity": {}}
    base.update(over)
    return base


class EmptyDataTests(unittest.TestCase):
    def test_report_builds_with_no_data(self):
        md, charts = rp.build_report(minimal_result())
        self.assertIn("Decisión: pendiente", md)
        for name, svg in charts.items():
            self.assertIn("<svg", svg, name)
            self.assertNotIn("NaN", svg, name)
        self.assertIn("Sin datos suficientes", charts["hrv.svg"])
        self.assertNotIn("None", md)
        self.assertNotIn("nan", md.lower().replace("monotonía", ""))

    def test_empty_chart_never_divides_by_zero(self):
        c = rp.Chart(["2026-10-17"], [5, 5])
        c.axes()
        c.line([5])
        self.assertIn("<svg", c.render())


class SlotAndCategoryTests(unittest.TestCase):
    def test_slot_by_sync_time(self):
        for hhmm, slot in (("08:44", "mañana"), ("16:52", "tarde"), ("22:51", "noche")):
            res = minimal_result(certificate={"cycle": {"data_synced_at": f"2026-10-17T{hhmm}:00+02:00"}})
            self.assertEqual(rp.slot_for(res), slot)

    def test_categories(self):
        self.assertEqual(rp.categorize({"label": "Fuerza - Squat snatch EMOM 8 min"}), "Halterofilia")
        self.assertEqual(rp.categorize({"label": "WOD parejas - 3 Rounds For Time"}), "WOD")
        self.assertEqual(rp.categorize({"label": "Fuerza - pierna: sentadilla, prensa y femoral"}), "Fuerza")
        self.assertEqual(rp.categorize({"name": "HIIT"}), "Sin detalle")


class RealDataTests(unittest.TestCase):
    """Pipeline completo sobre los datos del repositorio, en una copia temporal."""

    @classmethod
    def setUpClass(cls):
        from garmin_recovery.pipeline import run
        if not (ROOT / "garmin_hrv_timeline.json").exists():
            raise unittest.SkipTest("sin datos publicados")
        cls.tmp = tempfile.TemporaryDirectory()
        for p in ROOT.glob("*.json"):
            Path(cls.tmp.name, p.name).write_bytes(p.read_bytes())
        for p in ROOT.glob("*.csv"):
            Path(cls.tmp.name, p.name).write_bytes(p.read_bytes())
        cls.result = run(cls.tmp.name, now=datetime.now(TZ), write=True)
        cls.md = Path(cls.tmp.name, "app", "informe.md").read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_no_contradiction_with_decision(self):
        g = self.result["decision"]["guidance"]
        self.assertIn(g["text"], self.md)
        self.assertIn(f"| {g['rpe_max']} |", self.md)
        # La recomendación del v3 no aparece como recomendación si es distinta de la decisión
        v3 = self.result["readiness"]["guidance"]
        if v3["text"] != g["text"]:
            self.assertNotIn(f"**Recomendación:** {v3['text']}", self.md)

    def test_chart_dates_sorted_and_end_today(self):
        dates = [t["date"] for t in self.result["trend_28d"]]
        self.assertEqual(dates, sorted(dates))
        self.assertEqual(dates[-1], self.result["date"])
        self.assertEqual(len(set(dates)), len(dates))

    def test_all_linked_charts_exist_and_are_valid(self):
        import re
        import xml.dom.minidom
        for name in re.findall(r"\(charts/([a-z_]+\.svg)\)", self.md):
            path = Path(self.tmp.name, "app", "charts", name)
            self.assertTrue(path.exists(), name)
            xml.dom.minidom.parseString(path.read_text(encoding="utf-8"))

    def test_no_missing_value_artifacts(self):
        self.assertNotIn("None", self.md)
        self.assertNotIn("NaN", self.md)
        json.loads(Path(self.tmp.name, "app", "readiness_v3.json").read_text(encoding="utf-8"))

    def test_history_records_model_scores(self):
        import csv
        with Path(self.tmp.name, "history", "daily.csv").open(encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        today = [r for r in rows if r["date"] == self.result["date"]][0]
        self.assertEqual(today["decision_zone"], self.result["decision"]["zone"])


if __name__ == "__main__":
    unittest.main()


class V54Tests(unittest.TestCase):
    def test_load_units_are_explicit(self):
        self.assertEqual(rp.format_load({"peak_declared_load_kg": 80.0, "load_unit": "kg_total_dos_mancuernas"}),
                         "80,0 kg total (2 × 40,0 kg)")
        self.assertIn("máquina", rp.format_load({"peak_declared_load_kg": 120.0, "load_unit": "kg_indicado_maquina"}))
        self.assertIn("sin especificar", rp.format_load({"peak_declared_load_kg": 68.0, "load_unit": None}))
        self.assertEqual(rp.format_load({"equipment": "bodyweight", "load_unit": "peso_corporal"}), "peso corporal")
        self.assertIn("lateralidad", rp.format_load({"peak_declared_load_kg": 40.0, "load_unit": "kg_total_barra",
                                                     "laterality_unconfirmed": True}))

    def test_changes_since_previous(self):
        prev = {"report_id": "GR-a", "generated_at": "2026-10-17T08:45:00+02:00", "date": "2026-10-17",
                "decision_zone": "red", "v2_score": "45", "hrv_ms": "46", "sleep_hours": "7.84", "resting_hr": "60",
                "sessions_today": "0", "load_today": "0", "rpe_with": "15"}
        cur = dict(prev, report_id="GR-b", decision_zone="yellow", v2_score=60, sessions_today=1, load_today=20.0,
                   hrv_ms=46.0, sleep_hours=7.84, rpe_with=16)
        txt = " ".join(rp.changes_since(prev, cur))
        self.assertIn("rojo → **ámbar**", txt)
        self.assertIn("45 → 60", txt)
        self.assertIn("Sesiones nuevas desde entonces: **1**", txt)
        self.assertIn("15 → 16", txt)
        self.assertNotIn("Nueva noche", txt)
        self.assertIn("Primer informe", rp.changes_since(None, cur)[0])
        self.assertIn("Sin cambios", " ".join(rp.changes_since(prev, dict(prev))))

    def test_pending_actions_list_ids(self):
        res = minimal_result(training_integrity={"without_rpe": [
            {"id": "i1", "start_local": "2026-10-14T20:40:27", "type": "HIIT", "duration_min": 7.9, "load": 5}]})
        acts = rp.pending_actions(res, [{"exercise": "X", "peak_declared_load_kg": 60, "load_unit": None, "equipment": "unspecified"}])
        self.assertTrue(any("i1" in a and "No se estima" in a for a in acts))
        self.assertTrue(any("**X**" in a for a in acts))

    def test_crossfit_guidance_matches_zone(self):
        from garmin_recovery.decision import CROSSFIT
        self.assertTrue(all("WOD" in t or "Sin WOD" in t or "zona 2" in t for t in CROSSFIT["red"]))
        self.assertFalse(any("intensidad alta si" in t for t in CROSSFIT["red"] + CROSSFIT["yellow"]))

    def test_report_id_in_header_and_certificate(self):
        res = minimal_result()
        md, _ = rp.build_report(res, report_id="GR-test")
        self.assertIn("`GR-test`", md.splitlines()[2])
        self.assertIn("**Identificador del informe:** `GR-test`", md)


class SnapshotLedgerTests(unittest.TestCase):
    def test_one_snapshot_per_run_and_previous_is_used(self):
        from garmin_recovery.pipeline import run
        if not (ROOT / "garmin_hrv_timeline.json").exists():
            self.skipTest("sin datos")
        with tempfile.TemporaryDirectory() as tmp:
            for p in list(ROOT.glob("*.json")) + list(ROOT.glob("*.csv")):
                Path(tmp, p.name).write_bytes(p.read_bytes())
            run(tmp, now=datetime(2026, 10, 17, 8, 50, tzinfo=TZ))
            run(tmp, now=datetime(2026, 10, 17, 16, 55, tzinfo=TZ))
            rows = Path(tmp, "history", "reports.csv").read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(rows), 3)  # cabecera + 2 informes
            md = Path(tmp, "app", "informe.md").read_text(encoding="utf-8")
            self.assertIn("Frente al informe GR-2026-10-17-0850", md)
