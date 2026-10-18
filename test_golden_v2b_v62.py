"""Salida idéntica del ajuste de fiabilidad del v2 (``garmin_recovery/reliability.py``).

Sobre el día real congelado (17/10/2026 17:05, sin red) ejecuta primero el cálculo v2 y después
``produce``/``main`` de fiabilidad; compara el hash de cada archivo resultante y de la salida estándar.
Si un cambio es intencionado, actualizar los hashes y declararlo en el PR.
"""
import contextlib
import hashlib
import importlib
import io
import json
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
    "advanced_analytics.json": "673920b6c7b07e71",
    "daily_summary.json": "42ecb28157d68832",
    "weekly_summary.json": "ca811bfec1535de4",
    "data_quality.json": "24661dc4f9223a4b",
    "recovery_assessment.json": "bfde3e7dfd22c0d5",
}
GOLDEN_STDOUT = "517bea71307348ec"
NOW = datetime(2026, 10, 17, 17, 5, tzinfo=ZoneInfo("Europe/Madrid"))


def h(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def run_v2b(modname: str) -> tuple[dict, dict, str]:
    cwd, saved_env = os.getcwd(), {k: os.environ.pop(k, None) for k in ("INTERVALS_API_KEY", "DAY_CONTEXT_B64")}
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
            mod = importlib.import_module(modname)
            produced = mod.produce(now=NOW)
            objs = {n: h((json.dumps(o, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()) for n, o in produced.items()}
            real, buf = mod.produce, io.StringIO()
            mod.produce = lambda *a, **k: real(now=NOW)
            try:
                with contextlib.redirect_stdout(buf):
                    mod.main()
            finally:
                mod.produce = real
            files = {n: h(Path(n).read_bytes()) for n in produced}
            return objs, files, h(buf.getvalue().encode())
    finally:
        os.chdir(cwd)
        sys.path.remove(str(ROOT))
        for k, v in saved_env.items():
            if v is not None:
                os.environ[k] = v


class GoldenV2b(unittest.TestCase):
    def test_package_module_output_is_identical(self):
        objs, files, out = run_v2b("garmin_recovery.reliability")
        self.assertEqual(objs, GOLDEN)
        self.assertEqual(files, GOLDEN)
        self.assertEqual(out, GOLDEN_STDOUT)

    def test_legacy_names_are_the_same_modules(self):
        sys.path.insert(0, str(ROOT))
        try:
            from garmin_recovery import reliability as recovery_reliability
            from garmin_recovery import reliability
        finally:
            sys.path.remove(str(ROOT))
        self.assertIs(recovery_reliability, reliability)


if __name__ == "__main__":
    unittest.main()
