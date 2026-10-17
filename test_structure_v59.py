"""Estructura V5.9: sync.yml sin código inline y scripts antiguos sin efectos al importarlos."""
import importlib
import io
import json
import os
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent


class SyncSteps(unittest.TestCase):
    def test_no_inline_python_left(self):
        wf = (ROOT / ".github/workflows/sync.yml").read_text(encoding="utf-8")
        self.assertNotIn("python - <<'PY'", wf)
        for script in ("sync_fetch_wellness.py", "sync_fetch_activities.py", "sync_daily_analysis.py"):
            self.assertIn(f"run: python {script}", wf)
        self.assertEqual(wf.count("INTERVALS_API_KEY: ${{ secrets.INTERVALS_API_KEY }}"), 2)

    def _run_with_fake_api(self, script):
        if not (ROOT / "wellness.json").exists():
            self.skipTest("sin datos")

        class Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def fake(req, timeout=None):
            name = "wellness.json" if "wellness" in req.full_url else "activities.json"
            return Resp((ROOT / name).read_bytes())

        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(urllib.request, "urlopen", fake), \
                mock.patch.dict(os.environ, {"INTERVALS_API_KEY": "x"}):
            cwd = os.getcwd()
            os.chdir(tmp)
            try:
                code = compile((ROOT / script).read_text(encoding="utf-8"), script, "exec")
                exec(code, {"__name__": "__main__"})
                return {p.name: p.read_bytes() for p in Path(tmp).iterdir()}
            finally:
                os.chdir(cwd)

    def test_wellness_script_writes_same_json(self):
        out = self._run_with_fake_api("sync_fetch_wellness.py")
        self.assertEqual(json.loads(out["wellness.json"]), json.loads((ROOT / "wellness.json").read_bytes()))
        self.assertTrue(out["recovery.csv"].startswith(b"date,hrv,hrvSDNN"))

    def test_activities_script_writes_outputs(self):
        out = self._run_with_fake_api("sync_fetch_activities.py")
        self.assertIn("activities.json", out)
        self.assertIn("activities.csv", out)


class ImportWithoutSideEffects(unittest.TestCase):
    def test_legacy_scripts_do_not_run_on_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            os.chdir(tmp)
            sys.path.insert(0, str(ROOT))
            try:
                for name in ("garmin_metrics", "garmin_activity_metrics", "validate_pipeline"):
                    sys.modules.pop(name, None)
                    mod = importlib.import_module(name)
                    self.assertTrue(callable(getattr(mod, "main", None)), name)
                self.assertEqual(list(Path(tmp).iterdir()), [])  # nada escrito al importar
            finally:
                os.chdir(cwd)
                sys.path.remove(str(ROOT))


if __name__ == "__main__":
    unittest.main()
