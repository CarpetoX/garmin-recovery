"""Salida idéntica del monitor (``garmin_recovery/monitor.py`` y módulos asociados).

Sobre el día real congelado (17/10/2026 17:06) ejecuta el ciclo (v2, fiabilidad, CrossFit, certificado) y
después los seis pasos del monitor (``monitor``, ``origin_integration``, ``report_monitor``, ``cycle_observer``,
``monitor_clarity``, ``reliability_history``) con la API de GitHub simulada (sin red) y compara el hash de cada
archivo que escriben. Si un cambio es intencionado, actualizar los hashes y declararlo en el PR.
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
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
FIXTURE = ROOT / "tests_fixtures" / "e2e_2026-10-17.tar.gz"
TZ = ZoneInfo("Europe/Madrid")
NOW = dtmod.datetime(2026, 10, 17, 17, 6, tzinfo=TZ)
GOLDEN = {
    "workflow_health.json": "5ff0a5c8fd6d868b",
    "monthly_report.json": "39ccafe99e89c2c6",
    "cycle_observation_v373.json": "594f257eacc379a8",
    "reliability_history_v294.json": "2cb43340b55911a8",
    "origin_monitor_v292.json": "4ec28a6bfc82d104",
    "report_ready.json": "fae201c5f0812ea3",
    "report_cycles.json": "328ad363479ad638",
}
NAMES = [("monitor_monthly", "monitor"), ("monitor_origin_integration_v292", "origin_integration"),
         ("report_monitor_v34", "report_monitor"), ("cycle_observer_v373", "cycle_observer"),
         ("monitor_clarity_v297", "monitor_clarity"), ("reliability_history_v294", "reliability_history"),
         ("monitor_v231", "monitor_v231")]


class FrozenDatetime(dtmod.datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW.astimezone(tz) if tz else NOW.replace(tzinfo=None)


class Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def silent(fn, *args):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args)


def fake_run(run_id, event, start, end, status="completed", conclusion="success"):
    def iso(hh, mm):
        return dtmod.datetime(2026, 10, 17, hh, mm, tzinfo=TZ).isoformat()
    return {"id": run_id, "event": event, "created_at": iso(*start), "updated_at": iso(*end), "status": status,
            "conclusion": conclusion, "html_url": f"https://github.com/x/y/actions/runs/{run_id}"}


def run_monitor(style: str) -> dict:
    """style: ``legacy`` (nombres antiguos, alias) o ``package`` (garmin_recovery.*)."""
    cwd = os.getcwd()
    keys = ("INTERVALS_API_KEY", "DAY_CONTEXT_B64", "RPE_CSV_URL", "GITHUB_EVENT_NAME", "GITHUB_REPOSITORY",
            "GH_TOKEN", "CROSSFIT_RUN_ID", "ADVANCED_RUN_ID")
    saved_env = {k: os.environ.pop(k, None) for k in keys}
    saved_urlopen = urllib.request.urlopen
    sys.path.insert(0, str(ROOT))
    patched = []
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
            gate = importlib.import_module("garmin_recovery.delivery_gate")
            importlib.import_module("garmin_recovery.sleep_integration")
            by_run = {"/actions/runs/104": crossfit, "/actions/runs/103": advanced}
            saved_gate = gate.datetime, gate.github_json, gate.get_runs
            gate.datetime = FrozenDatetime
            gate.github_json = lambda url, token: by_run[url.split("garmin-recovery")[-1]]
            gate.get_runs = lambda repo, token, wf: {"garmin-heart-rate.yml": [heart], "sync.yml": [sync]}.get(wf, [])
            os.environ.update(GITHUB_REPOSITORY="CarpetoX/garmin-recovery", GH_TOKEN="x",
                              CROSSFIT_RUN_ID="104", ADVANCED_RUN_ID="103")
            try:
                silent(gate.main)
            finally:
                gate.datetime, gate.github_json, gate.get_runs = saved_gate
            runs = {"sync.yml": [sync, fake_run(100, "schedule", (8, 31), (8, 35))], "garmin-heart-rate.yml": [heart],
                    "advanced-analytics-rpe.yml": [advanced],
                    "crossfit-insights.yml": [dict(crossfit, status="completed", conclusion="success")]}
            by_id = {r["id"]: r for lst in runs.values() for r in lst}

            def fake_urlopen(req, timeout=None):
                url = req.full_url if hasattr(req, "full_url") else req
                if "/workflows/" in url:
                    return Resp(json.dumps({"workflow_runs": runs[url.split("/workflows/")[1].split("/")[0]]}).encode())
                return Resp(json.dumps(by_id[int(url.rstrip("/").split("/runs/")[1].split("?")[0])]).encode())
            urllib.request.urlopen = fake_urlopen
            os.environ["GH_TOKEN"] = "x"

            def mod(legacy, pkg):
                return importlib.import_module("garmin_recovery." + pkg)
            for legacy, pkg in NAMES:
                mod(legacy, pkg)
            known = dict(NAMES)
            for name, module in list(sys.modules.items()):
                if module is not None and getattr(module, "datetime", None) is dtmod.datetime and (
                        name.startswith("garmin_recovery.monitor") or name.startswith("garmin_recovery.origin")
                        or name.startswith("garmin_recovery.report_monitor") or name.startswith("garmin_recovery.cycle_")
                        or name.startswith("garmin_recovery.reliability_history") or name.startswith("garmin_recovery.ops_metrics")
                        or name in known):
                    module.datetime = FrozenDatetime
                    patched.append(module)
            out = {}
            try:
                silent(mod("monitor_monthly", "monitor").main)
            except SystemExit as exc:
                out["monitor_exit"] = exc.code
            silent(mod("monitor_origin_integration_v292", "origin_integration").main, [])
            silent(mod("report_monitor_v34", "report_monitor").main, [])
            silent(mod("cycle_observer_v373", "cycle_observer").main)
            silent(mod("monitor_clarity_v297", "monitor_clarity").main, [])
            silent(mod("reliability_history_v294", "reliability_history").main,
                   ["--ledger", "report_cycles.json", "--out", "reliability_history_v294.json", "--now", NOW.isoformat()])
            for name in GOLDEN:
                path = Path(name)
                out[name] = hashlib.sha256(path.read_bytes()).hexdigest()[:16] if path.exists() else None
            return out
    finally:
        for module in patched:
            module.datetime = dtmod.datetime
        urllib.request.urlopen = saved_urlopen
        os.chdir(cwd)
        sys.path.remove(str(ROOT))
        for k in keys:
            os.environ.pop(k, None)
        for k, v in saved_env.items():
            if v is not None:
                os.environ[k] = v


class GoldenMonitor(unittest.TestCase):
    def test_package_modules_output_is_identical(self):
        self.assertEqual(run_monitor("package"), GOLDEN)


if __name__ == "__main__":
    unittest.main()
