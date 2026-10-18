"""V7.3: curva de FC por sesión (solo visualización)."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from garmin_recovery import hr_curves, site

ROOT = Path(__file__).resolve().parent


def act(i, day, hr=True, **kw):
    return {"id": i, "start_date_local": f"{day}T10:00:00", "name": "WOD", "type": "HIIT", "has_heartrate": hr,
            "average_heartrate": 140, "max_heartrate": 175, "elapsed_time": 600, "icu_hr_zones": [120, 140, 160, 175],
            "icu_hr_zone_times": [100, 200, 300, 0], **kw}


def payload(n=120):
    return [{"type": "time", "data": list(range(n))}, {"type": "heartrate", "data": [100 + i % 50 for i in range(n)]}]


class Curves(unittest.TestCase):
    def test_downsample_means_and_ignores_bad_values(self):
        pts = hr_curves.downsample([0, 1, 2, 10, 11, 12], [100, 110, None, 0, 150, 160])
        self.assertEqual(pts, [[0, 105], [10, 155]])

    def test_entry_unavailable_without_hr(self):
        e = hr_curves.entry(act("i1", "2026-10-18"), [{"type": "time", "data": [0, 1]}])
        self.assertFalse(e["available"])
        self.assertEqual(e["points"], [])

    def test_refresh_fetches_recent_first_caps_and_caches(self):
        calls = []

        def fetch(aid, key):
            calls.append(aid)
            return payload()
        acts = [act("i1", "2026-10-10"), act("i2", "2026-10-18"), act("i3", "2026-10-17"), act("old", "2026-08-01")]
        out = hr_curves.refresh(acts, None, "k", fetch, "2026-10-18", max_new=2)
        self.assertEqual(calls, ["i2", "i3"])  # las más recientes primero y con tope
        self.assertEqual(sorted(out["activities"]), ["i2", "i3"])  # la de agosto queda fuera de la ventana
        out2 = hr_curves.refresh(acts, out, "k", fetch, "2026-10-18", max_new=2)
        self.assertEqual(calls, ["i2", "i3", "i1"])  # no repite lo ya guardado
        self.assertTrue(out2["activities"]["i1"]["available"])

    def test_refresh_errors_are_retried_and_no_hr_is_marked(self):
        def boom(aid, key):
            raise OSError("red")
        out = hr_curves.refresh([act("i1", "2026-10-18"), act("i2", "2026-10-17", hr=False)], None, "k", boom, "2026-10-18")
        self.assertNotIn("i1", out["activities"])  # fallo de red: se reintenta, no se marca
        self.assertFalse(out["activities"]["i2"]["available"])
        self.assertEqual(out["fetch_errors_this_run"], 1)

    def test_no_key_makes_no_calls(self):
        out = hr_curves.refresh([act("i1", "2026-10-18")], None, "", lambda *a: self.fail("sin clave no se descarga"), "2026-10-18")
        self.assertEqual(out["activities"], {})


class Web(unittest.TestCase):
    def test_site_embeds_curves_and_rows_are_clickable(self):
        if not (ROOT / "app" / "readiness_v3.json").exists():
            self.skipTest("sin salida publicada")
        sid = json.loads((ROOT / "app" / "readiness_v3.json").read_text(encoding="utf-8"))["recent_sessions"][0]["id"]
        with tempfile.TemporaryDirectory() as tmp:
            for d in ("app", "history"):
                shutil.copytree(ROOT / d, Path(tmp, d))
            if (ROOT / "crossfit_insights.json").exists():
                shutil.copy(ROOT / "crossfit_insights.json", tmp)
            e = hr_curves.entry(act(sid, "2026-10-18"), payload())
            Path(tmp, "activity_hr_curves.json").write_text(json.dumps({"step_s": 10, "activities": {sid: e}}), encoding="utf-8")
            info = site.build_site(tmp, Path(tmp, "_site"), history=False)
            html = (Path(info["out"]) / "index.html").read_text(encoding="utf-8")
            self.assertIn('id="hrdetail"', html)
            self.assertIn('"hr_curves"', html)
            self.assertIn("showHr", html)


if __name__ == "__main__":
    unittest.main()
