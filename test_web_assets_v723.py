"""V7.23: el CSS y el JS de la web viven en garmin_recovery/web/ y se incrustan al generar la página."""
import shutil
import subprocess
import unittest
from pathlib import Path

from garmin_recovery import dashboard

WEB = Path(dashboard.__file__).with_name("web")


class WebAssets(unittest.TestCase):
    def test_template_is_composed(self):
        t = dashboard.TEMPLATE
        self.assertNotIn("{{CSS}}", t)
        self.assertNotIn("{{JS}}", t)
        self.assertIn((WEB / "dashboard.css").read_text(encoding="utf-8").rstrip("\n"), t)
        self.assertIn((WEB / "dashboard.js").read_text(encoding="utf-8").rstrip("\n"), t)
        # una sola hoja de estilos y un solo script principal, como antes
        self.assertEqual(t.count("<style>"), 1)
        self.assertEqual(t.count("{{DATA}}"), 1)

    def test_assets_do_not_use_placeholders(self):
        for name in ("dashboard.css", "dashboard.js"):
            text = (WEB / name).read_text(encoding="utf-8")
            for key in ("TITLE", "HEAD", "DATA", "HOY", "TEND", "ENT", "SIS"):
                self.assertNotIn("{{" + key + "}}", text, f"{name} no debe llevar marcadores de plantilla")

    @unittest.skipUnless(shutil.which("node"), "node no instalado")
    def test_js_syntax(self):
        r = subprocess.run(["node", "--check", str(WEB / "dashboard.js")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
