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
        rows = list(csv.DictReader(Path(self.tmp.name, "history", "daily.csv").open(encoding="utf-8")))
        today = [r for r in rows if r["date"] == self.result["date"]][0]
        self.assertEqual(today["decision_zone"], self.result["decision"]["zone"])


if __name__ == "__main__":
    unittest.main()
