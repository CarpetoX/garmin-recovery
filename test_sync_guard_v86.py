"""V8.6: el Sync de respaldo del cron se cancela si el ciclo de las 08:30 ya está certificado; el certificador anota el motivo."""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from garmin_recovery import delivery_gate, sync_guard

TZ = ZoneInfo("Europe/Madrid")
NOW = datetime(2026, 10, 27, 14, 25, tzinfo=TZ)


def root_with(cycles):
    d = tempfile.mkdtemp()
    if cycles is not None:
        Path(d, "report_cycles.json").write_text(json.dumps({"cycles": [{"cycle_id": c} for c in cycles]}))
    return Path(d)


class Guard(unittest.TestCase):
    def test_skips_late_cron_when_morning_certified(self):
        out = sync_guard.decide("schedule", root_with(["2026-10-26-2245", "2026-10-27-0830-post-sleep"]), NOW)
        self.assertTrue(out["skip"])
        self.assertEqual(out["cycle_id"], "2026-10-27-0830-post-sleep")

    def test_runs_otherwise(self):
        self.assertFalse(sync_guard.decide("schedule", root_with(["2026-10-26-2245"]), NOW)["skip"])
        self.assertFalse(sync_guard.decide("schedule", root_with(None), NOW)["skip"])          # ilegible: sincroniza
        self.assertFalse(sync_guard.decide("workflow_dispatch", root_with(["2026-10-27-0830"]), NOW)["skip"])

    def test_workflow_cancels_only_on_schedule(self):
        wf = (Path(__file__).resolve().parent / ".github" / "workflows" / "sync.yml").read_text(encoding="utf-8")
        self.assertIn("python -m garmin_recovery.sync_guard", wf)
        self.assertIn("github.event_name == 'schedule' && steps.guard.outputs.skip == 'true'", wf)
        self.assertIn('gh run cancel "${{ github.run_id }}"', wf)
        self.assertIn("actions: write", wf)
        self.assertLess(wf.index("sync_guard"), wf.index("Verificar origen antes de sincronizar"))


class GateAnnotations(unittest.TestCase):
    def test_reasons_are_annotated(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            delivery_gate._annotate(["not_generated_in_cycle:crossfit_insights.json"])
            delivery_gate._annotate(["sync_outside_report_slot"])
        lines = buf.getvalue().splitlines()
        self.assertEqual(lines[0], "::error title=Certificado no emitido::not_generated_in_cycle:crossfit_insights.json")
        self.assertTrue(lines[1].startswith("::notice "))


if __name__ == "__main__":
    unittest.main()
