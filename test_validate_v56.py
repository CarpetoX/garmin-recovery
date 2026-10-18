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


class RollbackStepTests(unittest.TestCase):
    """Ejecuta el paso real del workflow en un repo git temporal con un 'python' simulado."""

    def run_step(self, app_outcome, validator_exit, writes_json):
        import subprocess
        import yaml
        wf = yaml.safe_load((ROOT / ".github/workflows/crossfit-insights.yml").read_text(encoding="utf-8"))
        step = [x for x in wf["jobs"]["crossfit"]["steps"] if x.get("id") == "validate_v56"][0]
        self.assertEqual(step["shell"], "bash {0}")
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        def sh(*a):
            return subprocess.run(a, cwd=tmp, check=True, capture_output=True)
        sh("git", "init", "-q"); sh("git", "config", "user.email", "t@t"); sh("git", "config", "user.name", "t")
        (tmp / "app").mkdir(); (tmp / "history").mkdir()
        (tmp / "app" / "informe.md").write_text("VIEJO"); (tmp / "app" / "validation.json").write_text('{"status":"ok"}')
        (tmp / "history" / "daily.csv").write_text("viejo")
        sh("git", "add", "-A"); sh("git", "commit", "-qm", "base")
        (tmp / "app" / "informe.md").write_text("NUEVO"); (tmp / "app" / "nuevo.svg").write_text("x")
        (tmp / "history" / "daily.csv").write_text("nuevo")
        bindir = tmp / "bin"; bindir.mkdir()
        body = ("echo '{\"status\":\"failed\",\"errors\":[\"x\"]}' > app/validation.json\n" if writes_json else "") + f"exit {validator_exit}\n"
        (bindir / "python").write_text("#!/bin/bash\n" + body); (bindir / "python").chmod(0o755)
        out_file = tmp / "gh_output"
        env = {"PATH": f"{bindir}:/usr/bin:/bin", "APP_OUTCOME": app_outcome, "GITHUB_OUTPUT": str(out_file),
               "RUNNER_TEMP": str(tmp), "HOME": str(tmp)}
        r = subprocess.run(["bash", "-c", step["run"]], cwd=tmp, env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return tmp, out_file.read_text()

    def test_validator_crash_restores_previous(self):
        tmp, out = self.run_step("success", 1, writes_json=False)
        self.assertIn("valid=false", out)
        self.assertEqual((tmp / "app" / "informe.md").read_text(), "VIEJO")
        self.assertEqual((tmp / "history" / "daily.csv").read_text(), "viejo")
        self.assertFalse((tmp / "app" / "nuevo.svg").exists())
        self.assertIn("failed", (tmp / "app" / "validation.json").read_text())

    def test_app_failure_restores_previous(self):
        tmp, out = self.run_step("failure", 0, writes_json=True)
        self.assertIn("valid=false", out)
        self.assertEqual((tmp / "app" / "informe.md").read_text(), "VIEJO")
        self.assertIn("app_outcome:failure", (tmp / "app" / "validation.json").read_text())

    def test_validation_failure_keeps_reason(self):
        tmp, out = self.run_step("success", 1, writes_json=True)
        self.assertEqual((tmp / "app" / "informe.md").read_text(), "VIEJO")
        self.assertIn('"x"', (tmp / "app" / "validation.json").read_text())

    def test_success_publishes_new(self):
        tmp, out = self.run_step("success", 0, writes_json=False)
        self.assertIn("valid=true", out)
        self.assertEqual((tmp / "app" / "informe.md").read_text(), "NUEVO")
