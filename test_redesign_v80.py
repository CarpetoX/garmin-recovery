"""V8.0: tema oscuro por defecto, texto explicativo plegado bajo «Ver detalle» y selector de apariencia."""
import json
import unittest
from pathlib import Path

from garmin_recovery.dashboard import render

ROOT = Path(__file__).resolve().parent


class Redesign(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = render(json.loads((ROOT / "app" / "readiness_v3.json").read_text(encoding="utf-8")), {})

    def test_dark_by_default_with_light_and_auto(self):
        p = self.page
        self.assertIn(':root:not([data-theme="light"]){\n  color-scheme: dark;', p)
        self.assertIn(':root[data-theme="auto"]', p)
        # el tema guardado se aplica antes de pintar (en <head>, antes de la hoja de estilos)
        self.assertLess(p.index('localStorage.getItem("gr-theme")'), p.index("<style>"))
        from garmin_recovery.dashboard import PWA_HEAD
        self.assertIn('<meta name="theme-color" content="#07090c">', PWA_HEAD)  # barra del móvil a juego (web publicada)

    def test_text_is_folded_not_removed(self):
        p = self.page
        self.assertIn("Ver detalle", p)
        self.assertIn("body.appendChild(el)", p)       # se mueve el nodo, no se borra
        self.assertNotIn(".remove()", p[p.index("V8.0 · Menos texto"):p.index("V8.0 · Apariencia")])
        self.assertIn("Metodología y versión", p)

    def test_theme_switcher(self):
        self.assertIn("['dark', 'Oscuro'], ['light', 'Claro'], ['auto', 'Automático']", self.page)


if __name__ == "__main__":
    unittest.main()
