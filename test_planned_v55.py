"""Tests V5.5: sesiones planificadas ajustadas y RPE no aplicable."""
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from garmin_recovery import planned as pl
from garmin_recovery.quality import rpe_not_applicable, training_integrity

TZ = ZoneInfo("Europe/Madrid")
ROOT = Path(__file__).resolve().parent
CSV = """Fecha,Hora,Actividad,Formato,Carga prevista (kg),Estado,RPE real,Notas,Tipo,Ejercicio principal,RPE objetivo,Duración (min),Unidad de carga,ID actividad
2026-10-17,18:00,Sentadilla trasera,5 × 3,150–160,PREVISTO,,,Fuerza,Sentadilla trasera,8,,kg_total_barra,
2026-10-17,18:40,WOD Fran,21-15-9,43,,,,WOD,,9,12,,
2026-10-17,19:00,Snatch técnica,6x2,60,,,,Halterofilia,Snatch,7,,kg_total_barra,
2026-10-18,10:00,Peso muerto,4x5,170,,,,Fuerza,,,,,
2026-10-09,17:15,Sentadilla trasera,7 × 2 (progresivo),180–185,REALIZADO DIFERENTE,9,,Fuerza,,,,,i195481427
"""


class ParseTests(unittest.TestCase):
    def test_parse_rows_and_helpers(self):
        rows = pl.parse_rows(CSV)
        self.assertEqual(len(rows), 5)
        self.assertEqual(pl.parse_scheme("7 × 2 (progresivo)"), (7, 2))
        self.assertEqual(pl.parse_scheme("4x5"), (4, 5))
        self.assertEqual(pl.parse_loads("180–185"), [180.0, 185.0])
        self.assertEqual(pl.plate(137.0), 135.0)

    def test_load_from_local_file_and_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(pl.load_planned(tmp, env={})[1], "no_configurado")
            Path(tmp, "planned_sessions.csv").write_text(CSV, encoding="utf-8")
            rows, src = pl.load_planned(tmp, env={})
            self.assertEqual((len(rows), src), (5, "planned_sessions.csv"))

    def test_url_failure_never_raises(self):
        def boom(*a, **k):
            raise OSError("down")
        rows, src = pl.load_planned("/nonexistent", env={"PLANNED_CSV_URL": "https://x"}, opener=boom)
        self.assertEqual(rows, [])
        self.assertTrue(src.startswith("error_lectura"))


class AdjustTests(unittest.TestCase):
    rows = pl.parse_rows(CSV)

    def by_zone(self, zone, cap):
        return {a["planned"].split(" · ")[0]: a for a in
                (pl.adjust(r, zone, cap) for r in self.rows if r["date"] == "2026-10-17")}

    def test_green_keeps_plan_but_caps_rpe(self):
        a = self.by_zone("green", 9)
        self.assertEqual(a["Sentadilla trasera"]["action"], "mantener")
        self.assertEqual(a["WOD Fran"]["rpe_max"], 9)

    def test_yellow_reduces_volume_and_load(self):
        a = self.by_zone("yellow", 7)
        sq = a["Sentadilla trasera"]
        self.assertIn("4 × 3", sq["adjusted"])
        self.assertIn("135–142,5 kg", sq["adjusted"])  # 90 % redondeado a 2,5 kg
        self.assertEqual(sq["rpe_max"], 7)
        self.assertIn("9 min en lugar de 12", a["WOD Fran"]["adjusted"])
        self.assertIn("80 %", a["Snatch técnica"]["adjusted"])

    def test_red_substitutes_heavy_work(self):
        a = self.by_zone("red", 4)
        self.assertEqual(a["Sentadilla trasera"]["action"], "sustituir")
        self.assertIn("Sin cargas", a["Sentadilla trasera"]["adjusted"])
        self.assertIn("Zona 2", a["WOD Fran"]["adjusted"])
        self.assertTrue(all(x["rpe_max"] <= 4 for x in a.values()))

    def test_never_exceeds_decision_cap(self):
        for zone, cap in (("green", 9), ("yellow", 7), ("red", 4), ("unavailable", 6)):
            for r in self.rows:
                self.assertLessEqual(pl.adjust(r, zone, cap)["rpe_max"], cap)

    def test_plan_block_today_tomorrow_and_done(self):
        sessions = [{"id": "i195481427", "date": "2026-10-09", "rpe": 9.0, "load": 4}]
        b = pl.plan_block(self.rows, "2026-10-17", "2026-10-18", {"zone": "red", "guidance": {"rpe_max": 4}},
                          sessions, "test")
        self.assertEqual(len(b["today"]), 3)
        self.assertEqual(len(b["tomorrow"]), 1)
        b9 = pl.plan_block(self.rows, "2026-10-09", "2026-10-10", {"zone": "yellow", "guidance": {"rpe_max": 7}},
                           sessions, "test")
        self.assertEqual(b9["today"], [])  # ya realizado
        self.assertTrue(b9["done_check"][0]["exceeded"])


class RpeNotApplicableTests(unittest.TestCase):
    def test_declared_warmup_and_skill(self):
        self.assertTrue(rpe_not_applicable({"rpe": None, "detail_json": json.dumps({"type": "warmup"})}))
        self.assertTrue(rpe_not_applicable({"rpe": "", "notes": "RPE no declarado: no imputar"}))
        self.assertFalse(rpe_not_applicable({"rpe": None, "notes": "WOD"}))
        self.assertFalse(rpe_not_applicable({"rpe": 8, "detail_json": json.dumps({"type": "warmup"})}))

    def test_integrity_uses_sheet_rows_without_rpe(self):
        sessions = {"a": {"id": "a", "date": "2026-10-16", "rpe": None}, "b": {"id": "b", "date": "2026-10-16", "rpe": 8}}
        fb = {"activities": {"b": {"date": "2026-10-16", "rpe": 8}},
              "source_rows_AH": [{"ID actividad": "a", "Fecha": "2026-10-16", "RPE": "", "Notas": "Calentamiento",
                                  "Detalle JSON": json.dumps({"type": "warmup"}), "Actividad": "Calentamiento"}]}
        t = training_integrity(sessions, fb, "2026-10-17")
        self.assertEqual(t["without_rpe"], [])
        self.assertEqual(t["rpe_coverage_pct"], 100.0)
        self.assertEqual(t["status"], "ok")


class ReportIntegrationTests(unittest.TestCase):
    def test_report_shows_adjusted_plan(self):
        from garmin_recovery.pipeline import run
        if not (ROOT / "garmin_hrv_timeline.json").exists():
            self.skipTest("sin datos")
        with tempfile.TemporaryDirectory() as tmp:
            for p in list(ROOT.glob("*.json")) + list(ROOT.glob("*.csv")):
                Path(tmp, p.name).write_bytes(p.read_bytes())
            today = datetime.now(TZ).date().isoformat()
            Path(tmp, "planned_sessions.csv").write_text(CSV.replace("2026-10-17", today), encoding="utf-8")
            res = run(tmp, now=datetime.now(TZ))
            md = Path(tmp, "app", "informe.md").read_text(encoding="utf-8")
            if res["readiness"]["date"] == today and res["planned"]["today"]:
                self.assertIn("Tu sesión planificada, ajustada", md)
                cap = res["decision"]["guidance"]["rpe_max"]
                self.assertTrue(all(p["rpe_max"] <= cap for p in res["planned"]["today"]))


if __name__ == "__main__":
    unittest.main()
