"""El resumen diario/semanal extraído de sync.yml produce el mismo contrato que el publicado."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class SyncDailyAnalysis(unittest.TestCase):
    def test_step_calls_script(self):
        wf = (ROOT / ".github/workflows/sync.yml").read_text(encoding="utf-8")
        self.assertIn("run: python -m garmin_recovery.sync_daily_analysis", wf)

    def test_outputs_keep_published_contract(self):
        if not (ROOT / "wellness.json").exists() or not (ROOT / "activities.json").exists():
            self.skipTest("sin datos de Intervals")
        with tempfile.TemporaryDirectory() as tmp:
            for f in ("wellness.json", "activities.json"):
                shutil.copy(ROOT / f, tmp)
            subprocess.run([sys.executable, "-m", "garmin_recovery.sync_daily_analysis"], cwd=tmp, check=True,
                           env={**os.environ, "PYTHONPATH": str(ROOT)})
            for f in ("daily_summary.json", "weekly_summary.json"):
                new = json.loads((Path(tmp) / f).read_text(encoding="utf-8"))
                published = json.loads((ROOT / f).read_text(encoding="utf-8"))
                # etapas posteriores (Advanced) añaden claves; las del Sync deben seguir todas
                self.assertTrue(set(new) <= set(published), (f, set(new) - set(published)))
                self.assertGreater(len(new), 5, f)


if __name__ == "__main__":
    unittest.main()
