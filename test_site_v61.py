"""V6.1: web publicada (PWA), calendario, RPE interactivo, puntualidad e histórico."""
import json
import shutil
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from garmin_recovery import site

ROOT = Path(__file__).resolve().parent


class Icon(unittest.TestCase):
    def test_png_is_valid(self):
        png = site.icon_png(32)
        self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))
        w, h = struct.unpack(">II", png[16:24])
        self.assertEqual((w, h), (32, 32))
        idat = png[png.index(b"IDAT") + 4:png.index(b"IEND") - 8]
        raw = zlib.decompress(idat)
        self.assertEqual(len(raw), 32 * (1 + 32 * 4))


class History(unittest.TestCase):
    def test_history_from_git_log(self):
        class R:
            def __init__(self, out):
                self.stdout = out

        def fake(cmd, **kw):
            if "log" in cmd:
                return R("abc123 2026-10-17T15:05:10+00:00\n")
            if cmd[-1].endswith("readiness_v3.json"):
                return R(json.dumps({"decision": {"zone": "red"}}))
            return R("# Informe\n\n`GR-2026-10-17-1705-8a9b0d` · cita\n")
        items = site.report_history(Path("."), run=fake)
        self.assertEqual(items, [{"label": "17/10 17:05", "zone": "red", "report_id": "GR-2026-10-17-1705-8a9b0d",
                                  "url": f"{site.REPO_URL}/blob/abc123/app/informe.md"}])

    def test_git_failure_gives_empty(self):
        def boom(cmd, **kw):
            raise OSError("sin git")
        self.assertEqual(site.report_history(Path("."), run=boom), [])


class BuildSite(unittest.TestCase):
    def test_build_complete_site(self):
        if not (ROOT / "app" / "readiness_v3.json").exists():
            self.skipTest("sin salida publicada")
        with tempfile.TemporaryDirectory() as tmp:
            for d in ("app", "history"):
                shutil.copytree(ROOT / d, Path(tmp, d))
            if (ROOT / "crossfit_insights.json").exists():
                shutil.copy(ROOT / "crossfit_insights.json", tmp)
            info = site.build_site(tmp, Path(tmp, "_site"), history=False)
            out = Path(info["out"])
            for f in ("index.html", "manifest.webmanifest", "sw.js", "icon-192.png", "icon-512.png", "icon-180.png", ".nojekyll"):
                self.assertTrue((out / f).exists(), f)
            html = (out / "index.html").read_text(encoding="utf-8")
            for txt in ('rel="manifest"', "serviceWorker", 'id="cal"', 'id="c-rpe"', 'class="tabbar"', 'id="rings"', 'id="porque"'):
                self.assertIn(txt, html)
            self.assertNotIn("{{", html)
            man = json.loads((out / "manifest.webmanifest").read_text(encoding="utf-8"))
            self.assertEqual(man["display"], "standalone")
            # el panel del repositorio no lleva las etiquetas PWA (rutas relativas a la web)
            from garmin_recovery.dashboard import render
            plain = render(json.loads((ROOT / "app" / "readiness_v3.json").read_text(encoding="utf-8")))
            self.assertNotIn('rel="manifest"', plain)
            self.assertIn('id="cal"', plain)

    def test_data_marker_in_content_is_not_reinterpreted(self):
        if not (ROOT / "app" / "readiness_v3.json").exists():
            self.skipTest("sin salida publicada")
        from garmin_recovery.dashboard import render
        result = json.loads((ROOT / "app" / "readiness_v3.json").read_text(encoding="utf-8"))
        html = render(result, {"pwa": True, "history": [], "strength_svg": "<svg>{{DATA}}</svg>"})
        self.assertEqual(html.count("{{DATA}}"), 1)  # solo el texto del extra, nunca el JSON

    def test_service_worker_only_clears_own_caches(self):
        self.assertIn("k.startsWith('garmin-recovery-')", site.SERVICE_WORKER)

    def test_pages_workflow(self):
        wf = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
        self.assertIn("types: [garmin-monitor]", wf)
        self.assertIn("python -m garmin_recovery site --out _site", wf)
        self.assertIn("actions/deploy-pages@", wf)
        self.assertIn("fetch-depth: 0", wf)


if __name__ == "__main__":
    unittest.main()
