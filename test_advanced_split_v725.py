"""V7.25: las funciones de advanced.py que dependen del día viven en módulos sin reloj."""
import ast
import importlib
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent
PARTS = {"advanced_baselines": ("rolling_robust", "baselines_by_context"), "advanced_load": ("weekly_load_metrics",),
         "advanced_recovery": ("personal_recovery_index", "convergence_alert"), "advanced_quality": ("data_quality",)}


class ClockFreeParts(unittest.TestCase):
    def test_parts_do_not_read_the_clock(self):
        for part in PARTS:
            text = (ROOT / "garmin_recovery" / f"{part}.py").read_text(encoding="utf-8")
            names = {n.id for n in ast.walk(ast.parse(text)) if isinstance(n, ast.Name)}
            self.assertFalse(names & {"NOW", "TODAY"}, part)
            self.assertNotIn("datetime.now(", text, part)
            self.assertNotIn("from .advanced import", text, part)  # solo hacia abajo

    def test_facade_passes_its_own_today(self):
        adv = importlib.import_module("garmin_recovery.advanced")
        fixed = date(2026, 1, 2)
        with mock.patch.object(adv, "TODAY", fixed), mock.patch.object(adv, "NOW", datetime(2026, 1, 2, 9, 0)):
            for part, names in PARTS.items():
                mod = importlib.import_module(f"garmin_recovery.{part}")
                for name in names:
                    seen = {}

                    def spy(*a, _seen=seen, **k):
                        _seen.update(k)
                        return "ok"
                    with mock.patch.object(mod, name, spy):
                        fn = getattr(adv, name)
                        argc = fn.__code__.co_argcount
                        self.assertEqual(fn(*([{}] * argc)), "ok")
                    self.assertEqual(seen.get("today_date"), fixed, f"{part}.{name}")


if __name__ == "__main__":
    unittest.main()
