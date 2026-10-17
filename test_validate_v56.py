"""Tests V5.6: validación de salidas publicadas."""
import json
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from garmin_recovery.validate import validate

TZ = ZoneInfo("Europe/Madrid")
ROOT = Path(__file__).resolve().parent


class ValidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from garmin_recovery.pipeline import run
        if not (ROOT / "garmin_hrv_timeline.json").exists():
            raise unittest.SkipTest("sin datos")
        cls.base = tempfile.TemporaryDirectory()
        for p in list(ROOT.glob("*.json")) + list(ROOT.glob("*.csv")):
            Path(cls.base.name, p.name).write_bytes(p.read_bytes())
        run(cls.base.name, now=datetime.now(TZ))

    @classmethod
    def tearDownClass(cls):
        cls.base.cleanup()

    def copy(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        shutil.copytree(self.base.name, tmp, dirs_exist_ok=True)
        return Path(tmp)

    def test_fresh_outputs_are_valid(self):
        res = validate(self.base.name)
        self.assertEqual(res["status"], "ok", res["errors"])
        self.assertGreater(res["checks"], 20)

    def test_detects_tampered_recommendation(self):
        d = self.copy()
        md = (d / "app" / "informe.md").read_text(encoding="utf-8")
        data = json.loads((d / "app" / "readiness_v3.json").read_text(encoding="utf-8"))
        md = md.replace(data["decision"]["guidance"]["text"], "Entrena a tope.")
        (d / "app" / "informe.md").write_text(md, encoding="utf-8")
        self.assertIn("md: la recomendación no coincide con decision.guidance", validate(d)["errors"])

    def test_detects_non_conservative_decision(self):
        d = self.copy()
        p = d / "app" / "readiness_v3.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        for m in data["decision"]["registry"]:
            if m["used_in_decision"]:
                m["zone"] = "red"
        data["decision"]["zone"] = "green"
        p.write_text(json.dumps(data), encoding="utf-8")
        self.assertIn("json: la decisión no es la más conservadora de los modelos", validate(d)["errors"])

    def test_detects_missing_chart_and_bad_id(self):
        d = self.copy()
        (d / "app" / "charts" / "hrv.svg").unlink()
        md = (d / "app" / "informe.md").read_text(encoding="utf-8")
        (d / "app" / "informe.md").write_text(md.replace("`GR-", "`XX-"), encoding="utf-8")
        errs = validate(d)["errors"]
        self.assertTrue(any(e.startswith("svg: hrv.svg") for e in errs))
        self.assertIn("md: identificador GR ausente o mal formado", errs)

    def test_detects_duplicate_report_ids(self):
        d = self.copy()
        p = d / "history" / "reports.csv"
        lines = p.read_text(encoding="utf-8").strip().splitlines()
        p.write_text("\n".join(lines + [lines[-1]]) + "\n", encoding="utf-8")
        self.assertIn("historial: identificadores GR duplicados", validate(d)["errors"])

    def test_unreadable_json_fails_closed(self):
        d = self.copy()
        (d / "app" / "readiness_v3.json").write_text("{roto", encoding="utf-8")
        self.assertEqual(validate(d)["status"], "failed")

    def test_plan_above_cap_detected(self):
        d = self.copy()
        p = d / "app" / "readiness_v3.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        data.setdefault("planned", {})["today"] = [{"rpe_max": 10}]
        p.write_text(json.dumps(data), encoding="utf-8")
        self.assertIn("json: un ajuste del plan supera el RPE máximo de la decisión", validate(d)["errors"])


if __name__ == "__main__":
    unittest.main()
