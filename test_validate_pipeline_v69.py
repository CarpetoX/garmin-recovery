import contextlib
import io
import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

from garmin_recovery import validate_pipeline as vp

TZ = ZoneInfo("Europe/Madrid")
NOW = datetime(2026, 10, 18, 11, 0, tzinfo=TZ)
FILES = ("daily_summary", "weekly_summary", "garmin_status", "garmin_heart_rate", "advanced_analytics", "data_quality")


def run(files: dict, raw: dict | None = None):
    """Ejecuta main() en una carpeta temporal; devuelve (código de salida, informe JSON)."""
    old = os.getcwd()
    with tempfile.TemporaryDirectory() as d:
        for name, obj in files.items():
            Path(d, name + ".json").write_text(json.dumps(obj), encoding="utf-8")
        for name, text in (raw or {}).items():
            Path(d, name + ".json").write_text(text, encoding="utf-8")
        out = io.StringIO()
        code = 0
        try:
            os.chdir(d)
            with mock.patch.object(vp, "NOW", NOW), contextlib.redirect_stdout(out):
                try:
                    vp.main()
                except SystemExit as exc:
                    code = exc.code
        finally:
            os.chdir(old)
    return code, json.loads(out.getvalue())


def fresh(**k):
    base = {"generated_at": "2026-10-18T10:30:00+02:00"}
    base.update(k)
    return base


class Validate(unittest.TestCase):
    def test_all_missing(self):
        code, rep = run({})
        self.assertEqual(code, 1)
        self.assertEqual(rep["status"], "error")
        self.assertTrue(all(any(e == f"missing:{n}.json" for e in rep["errors"]) for n in FILES))

    def test_invalid_json_and_non_finite(self):
        raw = {n: "{roto" for n in FILES}
        code, rep = run({}, raw)
        self.assertEqual(code, 1)
        self.assertTrue(any(e.startswith("invalid_json:daily_summary.json") for e in rep["errors"]))
        raw = {n: json.dumps(fresh()) for n in FILES}
        raw["daily_summary"] = '{"generated_at": "2026-10-18T10:30:00+02:00", "x": NaN}'
        _, rep = run({}, raw)
        self.assertTrue(any(e.startswith("non_finite:daily_summary.json.x") for e in rep["errors"]))

    def test_freshness_errors(self):
        files = {n: fresh() for n in FILES}
        files["daily_summary"] = {"generated_at": "2026-10-18T08:00:00+02:00"}
        files["weekly_summary"] = {"generated_at": "2026-10-18T12:00:00+02:00"}
        files["data_quality"] = {}
        _, rep = run(files)
        errs = " | ".join(rep["errors"])
        self.assertIn("stale:daily_summary.json", errs)
        self.assertIn("generated_at_in_future:weekly_summary.json", errs)
        self.assertIn("missing_or_invalid_generated_at:data_quality.json", errs)

    def test_heart_rate_checks_and_status(self):
        files = {n: fresh() for n in FILES}
        files["garmin_heart_rate"] = fresh(days={"2026-10-17": {"daytime_avg_hr": 400, "daytime_sample_count": -1},
                                                 "2026-10-16": "x"}, rolling={"3d": {}})
        files["garmin_status"] = fresh(status="error", error="boom")
        _, rep = run(files)
        errs = " | ".join(rep["errors"])
        for needle in ("implausible_hr:2026-10-17:daytime_avg_hr:400", "negative_sample_count:2026-10-17:daytime_sample_count:-1",
                       "hr_day_not_object:2026-10-16", "heart_rate_missing_rolling:7d", "heart_rate_missing_rolling:28d",
                       "garmin_status_error:boom", "weekly_missing_advanced_analytics"):
            self.assertIn(needle, errs)

    def test_status_partial_and_unknown(self):
        files = {n: fresh() for n in FILES}
        files["garmin_status"] = fresh(status="partial", error="algo")
        _, rep = run(files)
        self.assertIn("garmin_status_partial:algo", rep["warnings"])
        files["garmin_status"] = fresh(status="???")
        _, rep = run(files)
        self.assertTrue(any(e.startswith("garmin_status_unknown") for e in rep["errors"]))


if __name__ == "__main__":
    unittest.main()
