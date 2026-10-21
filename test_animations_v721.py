"""V7.21: animaciones de la web (curvas que se dibujan, ♥ a la FC media) sin tocar datos."""
import json
import unittest
from pathlib import Path

from garmin_recovery.dashboard import render

ROOT = Path(__file__).resolve().parent


class Animations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        result = json.loads((ROOT / "app" / "readiness_v3.json").read_text(encoding="utf-8"))
        cls.page = render(result, {"hr_curves": {"step_s": 10, "activities": {}}})

    def test_reduced_motion_is_respected(self):
        self.assertIn("prefers-reduced-motion: reduce", self.page)  # el script no anima
        self.assertIn("@media (prefers-reduced-motion:reduce){.hrmark.beat{animation:none}", self.page)

    def test_helpers_defined_before_use(self):
        p = self.page
        self.assertLess(p.index("function animIn("), p.index("function chart(el, opt)"))
        self.assertLess(p.index("const beat = hr =>"), p.index("$('sessions').innerHTML"))

    def test_beat_follows_heart_rate(self):
        self.assertIn("(60 / hr).toFixed(3)", self.page)
        self.assertIn("@keyframes beat", self.page)


if __name__ == "__main__":
    unittest.main()
