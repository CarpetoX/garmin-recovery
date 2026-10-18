"""Decisión del vigilante post-sueño de Apps Script (apps_script/GarminPostSueno.gs, v2.9.5).

Carga el archivo con Node (sin red ni servicios de Google) y comprueba ``_postSuenoPlan_``.
Se omite si Node no está instalado.
"""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GS = ROOT / "apps_script" / "GarminPostSueno.gs"
DRIVER = """
const fs = require('fs'), vm = require('vm');
const ctx = vm.createContext({console});
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8') + '\\n;globalThis.plan = _postSuenoPlan_;', ctx);
const cases = JSON.parse(process.argv[2]);
console.log(JSON.stringify(cases.map(c => ctx.plan(c))));
"""
DAY = "2026-10-18"


def ms(hhmm):
    h, m = hhmm.split(":")
    return __import__("datetime").datetime(2026, 10, 18, int(h), int(m)).timestamp() * 1000


def case(hhmm, sleep=None, last_min=None, status="completed", post_night=False, n=0):
    h, m = hhmm.split(":")
    latest = None
    if last_min is not None:
        latest = {"status": status, "id": 1, "created_at": __import__("datetime").datetime.fromtimestamp(
            (ms(hhmm) - last_min * 60000) / 1000, __import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    return {"localMinutes": int(h) * 60 + int(m), "nowMs": ms(hhmm), "postNight": post_night,
            "sleep": sleep or {}, "today": DAY, "latest": latest, "dispatchesToday": n}


WAIT = {"date": DAY, "state": "confirmed_wait_30m", "earliest_definitive_at": "2026-10-18T09:30:44"}


@unittest.skipUnless(shutil.which("node"), "Node no disponible")
class PostSueno(unittest.TestCase):
    def run_cases(self, *cases):
        # earliest_definitive_at sin zona se interpreta en hora local en Node, igual que ms()
        out = subprocess.run(["node", "-e", DRIVER, str(GS), json.dumps(cases)], capture_output=True,
                             text=True, check=True).stdout
        return json.loads(out)

    def test_confirmed_wake_dispatches_as_soon_as_margin_is_met(self):
        before, after = self.run_cases(case("09:25", WAIT, 6), case("09:35", WAIT, 16))
        self.assertEqual(before["state"], "esperando_30_minutos")
        self.assertEqual((after["action"], after["state"]), ("dispatch", "margen_cumplido"))

    def test_late_wake_does_not_wait_for_a_fixed_slot(self):
        # despertar 09:00, último Sync 09:19: a las 09:47 ya se pide (antes esperaba al sondeo de las 10:00)
        r, = self.run_cases(case("09:47", WAIT, 28))
        self.assertEqual(r["action"], "dispatch")

    def test_outside_window(self):
        a, b = self.run_cases(case("08:40"), case("18:45"))
        self.assertEqual((a["state"], b["state"]), ("fuera_de_sondeo", "fuera_de_sondeo"))

    def test_pending_sleep_interval(self):
        recent, due, post_wait, post_due = self.run_cases(
            case("10:00", None, 10), case("10:00", None, 35),
            case("10:00", None, 35, post_night=True), case("10:00", None, 65, post_night=True))
        self.assertEqual(recent["state"], "sync_reciente")
        self.assertEqual(due["action"], "dispatch")
        self.assertEqual(post_wait["action"], "skip")
        self.assertEqual(post_due["action"], "dispatch")

    def test_yesterdays_sleep_is_not_today(self):
        old = {"date": "2026-10-17", "state": "confirmed_ready", "is_definitive": True, "wake_confirmed": True}
        r, = self.run_cases(case("10:00", old, 40))
        self.assertEqual((r["action"], r["state"]), ("dispatch", "sueno_sin_confirmar"))

    def test_definitive_stops_polling(self):
        ready = {"date": DAY, "state": "confirmed_ready", "is_definitive": True, "wake_confirmed": True}
        r, = self.run_cases(case("11:00", ready, 90))
        self.assertEqual(r["state"], "sueno_ya_confirmado")

    def test_running_sync_and_daily_cap(self):
        run, cap = self.run_cases(case("10:00", None, 5, status="in_progress"), case("12:00", None, 60, n=10))
        self.assertEqual(run["state"], "sync_en_ejecucion")
        self.assertEqual(cap["state"], "limite_diario")

    def test_post_night_sleep_08_to_14(self):
        # TN: acuesta 08:00, despierta 14:00 -> consultas horarias y Sync al cumplirse el margen (14:30)
        wait = {"date": DAY, "state": "confirmed_wait_30m", "earliest_definitive_at": "2026-10-18T14:30:12"}
        pending = [case(h, None, 60, post_night=True, n=i) for i, h in enumerate(["10:00", "11:00", "12:00", "13:00"])]
        out = self.run_cases(*pending, case("14:20", wait, 20, post_night=True, n=4),
                             case("14:32", wait, 32, post_night=True, n=4))
        self.assertEqual([o["action"] for o in out], ["dispatch"] * 4 + ["skip", "dispatch"])
        self.assertEqual(out[-1]["state"], "margen_cumplido")

    def test_recovery_pending_retries(self):
        s = {"date": DAY, "state": "confirmed_recovery_sync_pending"}
        r, = self.run_cases(case("10:10", s, 20))
        self.assertEqual(r["state"], "recuperacion_pendiente")


if __name__ == "__main__":
    unittest.main()
