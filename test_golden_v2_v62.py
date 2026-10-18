"""Prueba de salida idéntica del cálculo v2 (``garmin_recovery/advanced.py``).

Ejecuta el módulo sobre el día real congelado (17/10/2026 17:05, sin red) y compara el hash de
cada archivo que escribe. Cualquier cambio de un campo, aunque sea mínimo, la hace fallar:
si es intencionado, actualizar los hashes y declararlo en el PR.
"""
import contextlib
import hashlib
import importlib
import io
import os
import sys
import tarfile
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
FIXTURE = ROOT / "tests_fixtures" / "e2e_2026-10-17.tar.gz"
GOLDEN = {
    "advanced_analytics.json": "e27a3645376b8856",
    "data_quality.json": "1a7e109f0e4f6952",
    "daily_summary.json": "f28eb655c7b33f6a",
    "weekly_summary.json": "5c7492f24f31511d",
    "stdout": "60ff0c50f8a69e88",
}


def run_v2(modname: str) -> dict:
    cwd, saved_env = os.getcwd(), {k: os.environ.pop(k, None) for k in ("INTERVALS_API_KEY", "DAY_CONTEXT_B64")}
    sys.path.insert(0, str(ROOT))
    try:
        with tempfile.TemporaryDirectory() as tmp:
            with tarfile.open(FIXTURE) as tf:
                tf.extractall(tmp, filter="data")
            os.chdir(tmp)
            mod = importlib.import_module(modname)
            saved = mod.NOW, mod.TODAY
            now = datetime(2026, 10, 17, 17, 5, tzinfo=ZoneInfo("Europe/Madrid"))
            mod.NOW, mod.TODAY = now, now.date()
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    mod.main()
            finally:
                mod.NOW, mod.TODAY = saved
            out = {n: hashlib.sha256(Path(n).read_bytes()).hexdigest()[:16] for n in GOLDEN if n != "stdout"}
            out["stdout"] = hashlib.sha256(buf.getvalue().encode()).hexdigest()[:16]
            return out
    finally:
        os.chdir(cwd)
        sys.path.remove(str(ROOT))
        for k, v in saved_env.items():
            if v is not None:
                os.environ[k] = v


class GoldenV2(unittest.TestCase):
    def test_package_module_output_is_identical(self):
        self.assertEqual(run_v2("garmin_recovery.advanced"), GOLDEN)

    def test_legacy_name_is_the_same_module(self):
        from garmin_recovery import advanced as advanced_analytics
        from garmin_recovery import advanced
        self.assertIs(advanced_analytics, advanced)


if __name__ == "__main__":
    unittest.main()
