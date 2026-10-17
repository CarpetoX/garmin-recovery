"""Salida idéntica del certificado del ciclo (``garmin_recovery/delivery_gate.py`` + ``sleep_integration.py``).

Sobre el día real congelado (17/10/2026, ciclo de las 16:45) ejecuta v2 + fiabilidad + CrossFit Insights y
después el certificado con una cadena de ejecuciones de GitHub simulada (sin red). Compara el hash de
``report_ready.json`` y ``report_cycles.json`` (con instantánea SHA-256). Si un cambio es intencionado,
actualizar los hashes y declararlo en el PR.
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
TZ = ZoneInfo("Europe/Madrid")
NOW = dtmod.datetime(2026, 10, 17, 17, 5, tzinfo=TZ)
GOLDEN = {"rc": 0, "stdout": "Report gate READY: 2026-10-17-1645 sync_run 101 crossfit_run 104\n",
          "report_ready.json": "8a8efbb4af83de5d", "report_cycles.json": "8ce2dffea73d0122"}


class FrozenDatetime(dtmod.datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW


def silent(fn):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn()


def fake_run(run_id, event, start, end, status="completed", conclusion="success"):
    def iso(hh, mm):
        return dtmod.datetime(2026, 10, 17, hh, mm, tzinfo=TZ).isoformat()
    return {"id": run_id, "event": event, "created_at": iso(*start), "updated_at": iso(*end),
            "status": status, "conclusion": conclusion}


def run_certificate(gate_name: str, entry_name: str) -> dict:
    cwd = os.getcwd()
    keys = ("INTERVALS_API_KEY", "DAY_CONTEXT_B64", "RPE_CSV_URL", "GITHUB_EVENT_NAME",
            "GITHUB_REPOSITORY", "GH_TOKEN", "CROSSFIT_RUN_ID", "ADVANCED_RUN_ID")
    saved_env = {k: os.environ.pop(k, None) for k in keys}
    sys.path.insert(0, str(ROOT))
    try:
        with tempfile.TemporaryDirectory() as tmp:
            with tarfile.open(FIXTURE) as tf:
                tf.extractall(tmp, filter="data")
            os.chdir(tmp)
            adv = importlib.import_module("garmin_recovery.advanced")
            saved_adv = adv.NOW, adv.TODAY
            adv.NOW, adv.TODAY = NOW, NOW.date()
            try:
                silent(adv.main)
            finally:
                adv.NOW, adv.TODAY = saved_adv
            rel = importlib.import_module("garmin_recovery.reliability")
            real_produce = rel.produce
            rel.produce = lambda *a, **k: real_produce(now=NOW)
            try:
                silent(rel.main)
            finally:
                rel.produce = real_produce
            cf = importlib.import_module("garmin_recovery.crossfit")
            saved_cf = cf.datetime, cf.sheet_rows
            row = {"Fecha": "2026-10-16", "ID actividad": "1", "Actividad": "x", "RPE": "6", "Sensaciones": "",
                   "Notas": "", "Registrado": "", "Detalle JSON": ""}
            cf.datetime, cf.sheet_rows = FrozenDatetime, (lambda: ([row], "live_csv", None))
            try:
                silent(cf.main)
            finally:
                cf.datetime, cf.sheet_rows = saved_cf
            generated = dtmod.datetime(2026, 10, 17, 17, 1, tzinfo=TZ).isoformat()
            for name in ("daily_summary.json", "weekly_summary.json"):
                data = json.loads(Path(name).read_text())
                data["generated_at"] = generated
                Path(name).write_text(json.dumps(data))
            Path("garmin_status.json").write_text(json.dumps({"status": "success", "generated_at": generated}))
            for name in ("report_ready.json", "report_cycles.json"):
                if Path(name).exists():
                    Path(name).unlink()
            sync = fake_run(101, "workflow_dispatch", (16, 47), (16, 50))
            heart = fake_run(102, "workflow_run", (16, 51), (16, 53))
            advanced = fake_run(103, "workflow_run", (16, 54), (16, 58))
            crossfit = fake_run(104, "workflow_run", (16, 59), (17, 5), "in_progress", None)
            gate = importlib.import_module(gate_name)
            importlib.import_module(entry_name)  # el alias de sueño parchea el certificado
            saved_gate = gate.datetime, gate.github_json, gate.get_runs
            by_run = {"/actions/runs/104": crossfit, "/actions/runs/103": advanced}
            gate.datetime = FrozenDatetime
            gate.github_json = lambda url, token: by_run[url.split("garmin-recovery")[-1]]
            gate.get_runs = lambda repo, token, wf: {"garmin-heart-rate.yml": [heart], "sync.yml": [sync]}.get(wf, [])
            os.environ.update(GITHUB_REPOSITORY="CarpetoX/garmin-recovery", GH_TOKEN="x",
                              CROSSFIT_RUN_ID="104", ADVANCED_RUN_ID="103")
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    rc = gate.main()
            finally:
                gate.datetime, gate.github_json, gate.get_runs = saved_gate
            out = {"rc": rc, "stdout": buf.getvalue()}
            for name in ("report_ready.json", "report_cycles.json"):
                if Path(name).exists():
                    out[name] = hashlib.sha256(Path(name).read_bytes()).hexdigest()[:16]
            return out
    finally:
        os.chdir(cwd)
        sys.path.remove(str(ROOT))
        for k in keys:
            os.environ.pop(k, None)
        for k, v in saved_env.items():
            if v is not None:
                os.environ[k] = v


class GoldenCertificate(unittest.TestCase):
    def test_package_module_output_is_identical(self):
        self.assertEqual(run_certificate("garmin_recovery.delivery_gate", "garmin_recovery.sleep_integration"), GOLDEN)


if __name__ == "__main__":
    unittest.main()
