"""Salida idéntica de la extracción de fuerza/WOD (``garmin_recovery/crossfit.py`` y módulos asociados).

Sobre el día real congelado (17/10/2026 17:05, sin red) ejecuta v2 + fiabilidad + CrossFit Insights con
filas de RPE sintéticas y series de fuerza (18 ejercicios) y compara el hash de ``crossfit_insights.json``,
``report_history.json`` y la salida estándar. Si un cambio es intencionado, actualizar los hashes y
declararlo en el PR.
"""
import contextlib
import datetime as dtmod
import hashlib
import importlib
import io
import json
import os
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
FIXTURE = ROOT / "tests_fixtures" / "e2e_2026-10-17.tar.gz"
NOW = dtmod.datetime(2026, 10, 17, 17, 5, tzinfo=ZoneInfo("Europe/Madrid"))
GOLDEN = {"crossfit_insights.json": "0d36813b471b1fd3", "report_history.json": "09fb061d3f213d07",
          "stdout": "cdddda1edd4f2556", "strength_exercises": 18}


class FrozenDatetime(dtmod.datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW


def synthetic_rows(activities):
    rows = []
    for i, a in enumerate(sorted((x for x in activities if isinstance(x, dict)), key=lambda x: str(x.get("id")))[-25:]):
        detail = {"exercises": [{"name": "Back Squat", "sets": [{"reps": 5, "load_kg": 100 + i, "count": 3}]},
                                {"name": "Strict Press", "sets": [{"reps": 8, "load_kg": 40}]}]} if i % 2 == 0 else {}
        rows.append({"Fecha": str(a.get("start_date_local") or a.get("date") or "2026-10-01")[:10],
                     "ID actividad": str(a.get("id")), "Actividad": str(a.get("name")), "RPE": str(6 + i % 4),
                     "Sensaciones": "ok", "Notas": "n", "Registrado": "2026-10-17", "Detalle JSON": json.dumps(detail)})
    return rows


def run_crossfit(modname: str) -> dict:
    cwd = os.getcwd()
    saved_env = {k: os.environ.pop(k, None) for k in ("INTERVALS_API_KEY", "DAY_CONTEXT_B64", "RPE_CSV_URL", "GITHUB_EVENT_NAME")}
    sys.path.insert(0, str(ROOT))
    try:
        with tempfile.TemporaryDirectory() as tmp:
            with tarfile.open(FIXTURE) as tf:
                tf.extractall(tmp, filter="data")
            os.chdir(tmp)
            adv = importlib.import_module("garmin_recovery.advanced")
            saved = adv.NOW, adv.TODAY
            adv.NOW, adv.TODAY = NOW, NOW.date()
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    adv.main()
            finally:
                adv.NOW, adv.TODAY = saved
            rel = importlib.import_module("garmin_recovery.reliability")
            real = rel.produce
            rel.produce = lambda *a, **k: real(now=NOW)
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    rel.main()
            finally:
                rel.produce = real
            m = importlib.import_module(modname)
            saved_dt, saved_rows = m.datetime, m.sheet_rows
            rows = synthetic_rows(json.loads(Path("activities.json").read_text()))
            m.datetime, m.sheet_rows = FrozenDatetime, (lambda: (rows, "live_csv", None))
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    m.main()
            finally:
                m.datetime, m.sheet_rows = saved_dt, saved_rows
            out = {n: hashlib.sha256(Path(n).read_bytes()).hexdigest()[:16] for n in ("crossfit_insights.json", "report_history.json")}
            out["stdout"] = hashlib.sha256(buf.getvalue().encode()).hexdigest()[:16]
            data = json.loads(Path("crossfit_insights.json").read_text())
            out["strength_exercises"] = len((data.get("muscle_load") or {}).get("strength_exercises") or [])
            return out
    finally:
        os.chdir(cwd)
        sys.path.remove(str(ROOT))
        for k, v in saved_env.items():
            if v is not None:
                os.environ[k] = v


class GoldenCrossfit(unittest.TestCase):
    def test_package_module_output_is_identical(self):
        self.assertEqual(run_crossfit("garmin_recovery.crossfit"), GOLDEN)

    def test_legacy_names_are_the_same_modules(self):
        sys.path.insert(0, str(ROOT))
        try:
            import crossfit_insights
            import data_quality
            import muscle_load
            import report_audit
            import rpe_cycle_snapshot
            import training_extensions
            from garmin_recovery import crossfit, data_quality as dq, muscle_load as ml, report_audit as ra
            from garmin_recovery import rpe_cycle_snapshot as rs, training_extensions as te
        finally:
            sys.path.remove(str(ROOT))
        for old, new in ((crossfit_insights, crossfit), (data_quality, dq), (muscle_load, ml),
                         (report_audit, ra), (rpe_cycle_snapshot, rs), (training_extensions, te)):
            self.assertIs(old, new)


if __name__ == "__main__":
    unittest.main()
