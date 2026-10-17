"""Prueba de extremo a extremo con un día real congelado (17/10/2026, ciclo de las 16:45).

Ejecuta la app completa sobre los datos guardados en ``tests_fixtures/`` y compara lo
esencial con la foto esperada. Si un cambio altera la decisión, las puntuaciones o el
informe sin querer, falla. Si el cambio es intencionado, regenerar la foto con:
``python test_e2e_frozen_v61.py --update`` y explicarlo en el PR.
"""
import json
import sys
import tarfile
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIXTURE = ROOT / "tests_fixtures" / "e2e_2026-10-17.tar.gz"
EXPECTED = ROOT / "tests_fixtures" / "e2e_2026-10-17.expected.json"
NOW = "2026-10-17T17:05:00+02:00"


def snapshot(tmp: Path) -> dict:
    from garmin_recovery.pipeline import run
    from garmin_recovery.validate import validate
    with tarfile.open(FIXTURE) as tf:
        tf.extractall(tmp, filter="data")
    r = run(tmp, now=datetime.fromisoformat(NOW))
    md = (tmp / "app" / "informe.md").read_text(encoding="utf-8")
    weekly = (tmp / "app" / "informe_semanal.md").read_text(encoding="utf-8")
    val = validate(tmp)
    dec = r["decision"]
    return {
        "date": r["date"],
        "decision_zone": dec["zone"], "rpe_max": dec["guidance"]["rpe_max"], "decided_by": dec["decided_by"],
        "registry": {m["id"]: [m.get("score"), m.get("zone")] for m in dec["registry"]},
        "v3": [r["readiness"]["score"], r["readiness"]["zone"], r["readiness"]["state"]],
        "hrv_band": r["readiness"]["components"]["hrv"].get("band"),
        "load": {k: r["load"].get(k) for k in ("week_load", "week_srpe", "monotony", "strain", "acwr", "ctl", "atl")},
        "sessions_28d": len(r["sessions_28d"]),
        "report_sections": [x for x in md.splitlines() if x.startswith("## ")],
        "summary_first_line": next(x for x in md.splitlines() if x.startswith("> **Hoy:")),
        "weekly_sections": [x for x in weekly.splitlines() if x.startswith("## ")],
        "charts": sorted(p.name for p in (tmp / "app" / "charts").iterdir()),
        "validation": [val["status"], val["errors"]],
    }


class FrozenDay(unittest.TestCase):
    def test_full_app_matches_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            got = snapshot(Path(tmp))
        want = json.loads(EXPECTED.read_text(encoding="utf-8"))
        self.assertEqual(got["validation"][0], "ok", got["validation"])
        for key in want:
            self.assertEqual(got[key], want[key], f"cambia «{key}»: si es intencionado, regenerar con --update")


if __name__ == "__main__":
    if "--update" in sys.argv:
        with tempfile.TemporaryDirectory() as tmp:
            EXPECTED.write_text(json.dumps(snapshot(Path(tmp)), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("Foto actualizada:", EXPECTED)
    else:
        unittest.main()
